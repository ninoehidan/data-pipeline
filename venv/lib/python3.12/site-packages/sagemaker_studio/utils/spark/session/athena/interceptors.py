"""
Custom Spark Connect Authentication Interceptor

Purpose:
--------
Spark Connect does not provide a native way to plug in custom authenticators.
Athena issues short-lived authentication tokens (via Athena:GetSessionEndpointUrl API)
that are valid for only ~30 minutes. To maintain uninterrupted connectivity for interactive
Spark workloads in Spiral Notebooks, this interceptor automatically refreshes the token
when it expires and injects it into each gRPC request.

Outcomes:
---------
- Ensures seamless execution of Spark queries in Spiral Notebooks without manual token refresh.
- Supports long-running interactive sessions where the token may expire mid-session.
- Integrates with existing Spark Connect client code without modifying client internals.

How It Works:
-------------
1. ChannelBuilder:
   - The Spark Connect client internally uses a gRPC Channel/ChannelBuilder to manage
     network connections to the Spark server.
   - By configuring the ChannelBuilder with a custom interceptor, we can intercept every
     outgoing RPC call and inject updated authentication metadata dynamically.

2. Interceptor:
   - The interceptor is implemented by subclassing `grpc.UnaryUnaryClientInterceptor`
     (or the appropriate gRPC interceptor type for the call type).
   - Before forwarding each RPC request, it checks if the current token has expired.
   - If expired, it fetches a new token and adds it to the request metadata.

3. Overloading _ClientCallDetails:
   - gRPC represents RPC metadata and call details in an internal `_ClientCallDetails` object.
   - Since gRPC does not provide a public API to modify request metadata directly in the interceptor,
     we subclass or wrap `_ClientCallDetails` to inject our refreshed authentication token.
   - This ensures that each RPC carries the correct, up-to-date token, while remaining compatible
     with the gRPC client call interface.

"""

import datetime
import logging as _logging
from collections import namedtuple as _namedtuple

import grpc as _grpc
from pyspark.sql.connect.client import ChannelBuilder as _ChannelBuilder

# Boilerplate for altering call details
_ClientCallDetails = _namedtuple(
    "_ClientCallDetails",
    ("method", "timeout", "metadata", "credentials", "wait_for_ready", "compression"),
)


class _ClientCallDetails(_ClientCallDetails, _grpc.ClientCallDetails):
    pass


class SparkConnectGRPCInterceptor(
    _grpc.UnaryUnaryClientInterceptor,
    _grpc.UnaryStreamClientInterceptor,
    _grpc.StreamUnaryClientInterceptor,
    _grpc.StreamStreamClientInterceptor,
):
    def __init__(self, athena_session_id: str, athena_client):
        self.logger = _logging.getLogger("SparkConnect")
        self.athena = athena_client
        self.athena_session_id = athena_session_id
        self.cache_auth_token = None
        # Offset window for refreshing the cache before it expires.
        # Current value refreshes the cache 5 minutes prior to expiration.
        self.cache_early_refresh_margin = 5 * 60
        self.cache_expiration_time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    def _refresh_token(self):
        if self.athena_session_id is not None:

            self.logger.debug(f"Refreshing token for session {self.athena_session_id}")
            try:
                get_session_endpoint_response = self.athena.get_session_endpoint(
                    SessionId=self.athena_session_id
                )
                self.cache_auth_token = get_session_endpoint_response["AuthToken"]
                self.cache_expiration_time = get_session_endpoint_response[
                    "AuthTokenExpirationTime"
                ] - datetime.timedelta(seconds=self.cache_early_refresh_margin)
                self.logger.info(f"Next token refresh at {self.cache_expiration_time}")

            except Exception as e:
                self.logger.error(
                    f"Error while refreshing the Spark connect auth tokens for session {self.athena_session_id}: {e}"
                )
                raise

    def _with_metadata(self, client_call_details):

        now = datetime.datetime.now(datetime.timezone.utc)

        # Refresh the auth token if it is expired.
        if self.cache_expiration_time < now:
            self._refresh_token()
            self.cache_last_update = now

        dict_metadata = dict(client_call_details.metadata)
        dict_metadata["x-aws-proxy-auth"] = self.cache_auth_token
        metadata = list(dict_metadata.items())

        return _ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
            compression=client_call_details.compression,
        )

    def intercept_unary_unary(self, continuation, client_call_details, request):
        return continuation(self._with_metadata(client_call_details), request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        return continuation(self._with_metadata(client_call_details), request)

    def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        return continuation(self._with_metadata(client_call_details), request_iterator)

    def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        return continuation(self._with_metadata(client_call_details), request_iterator)


class CustomChannelBuilder(_ChannelBuilder):
    def __init__(self, athena_session_id: str, url: str, athena_client):
        super().__init__(url)
        self.athena_session_id = athena_session_id
        self.athena_client = athena_client

    """
     `to_channel` code is mostly lifted from pyspark implementation https://github.com/apache/spark/blob/69355a817fab9a2898188487f5302efd4dda1f49/python/pyspark/sql/connect/client/core.py#L375
     This implementation adds the custom interceptor to the channel.
    """

    def toChannel(self) -> _grpc.Channel:  # noqa: N802
        """
        Applies the parameters of the connection string and creates a new
        GRPC channel according to the configuration. Passes optional channel options to
        construct the channel.

        Returns
        -------
        GRPC Channel instance.
        """
        channel = super().toChannel()
        interceptor = SparkConnectGRPCInterceptor(self.athena_session_id, self.athena_client)
        channel = _grpc.intercept_channel(channel, interceptor)
        return channel
