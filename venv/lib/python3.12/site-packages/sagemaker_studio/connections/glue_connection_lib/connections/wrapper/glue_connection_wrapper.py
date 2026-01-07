"""
Glue Connection Wrapper Interface.
This interface allows clients to be unblocked while implementations are being developed.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from ..config import JDBCConf
from ..constants import (
    JDBC_CONNECTION_TYPES,
    ConnectionObjectKey,
    ConnectionPropertyKey,
    SparkOptionsKey,
)
from ..utils.utils import (
    decrypt_encrypted_password,
    get_connection_properties,
    get_secret_options,
    get_vendor_from_url,
    is_jdbc_connection_needed,
)
from .glue_connection_wrapper_inputs import GlueConnectionWrapperInputs


class GlueConnectionWrapper(ABC):
    """
    Abstract base class for Glue connection wrappers.

    This class provides the interface that all connection wrapper implementations must follow.
    The output is the Connection object itself with fully resolved spark options inside
    the SparkProperties field.

    The connection object should be the AWS Glue Connection as returned by:
    boto3.client('glue').get_connection(Name='connection-name', ApplyOverrideForComputeEnvironment='SPARK')['Connection']
    """

    def __init__(self, wrapper_input: GlueConnectionWrapperInputs):
        """
        Initialize the connection wrapper.

        Args:
            wrapper_input: Input parameters containing connection, clients, and options
        """
        self.log = logging.getLogger(self.__class__.__name__)

        # Protected fields
        self._wrapper_input = wrapper_input
        self._connection = wrapper_input.connection
        self._kms_client = wrapper_input.kms_client
        self._secrets_manager_client = wrapper_input.secrets_manager_client
        self._additional_options = wrapper_input.additional_options

    @classmethod
    def _is_redshift_jdbc_connection(cls, wrapper_input: GlueConnectionWrapperInputs) -> bool:
        """Check if a generic JDBC connection is actually Redshift based on URL vendor."""
        props = get_connection_properties(wrapper_input.connection)
        jdbc_url = props.get(ConnectionPropertyKey.JDBC_CONNECTION_URL, "")
        if jdbc_url:
            _, _, vendor = get_vendor_from_url(jdbc_url)
            return vendor.lower() == "redshift"
        return False

    @classmethod
    def create(cls, wrapper_input: GlueConnectionWrapperInputs) -> "GlueConnectionWrapper":
        """
        Factory method to create the appropriate connection wrapper implementation.

        Automatically selects the correct implementation based on the connection type.

        Args:
            wrapper_input: Input parameters containing connection, clients, and options

        Returns:
            Appropriate GlueConnectionWrapper implementation

        """
        from .jdbc.jdbc_wrapper import JDBCConnectionWrapper
        from .jdbc.redshift_wrapper import RedshiftJDBCConnectionWrapper
        from .local.mongodb_wrapper import MongoDBConnectionWrapper
        from .local.native_wrapper import NativeConnectionWrapper
        from .local.snowflake_wrapper import SnowflakeConnectionWrapper

        connection_type = wrapper_input.connection.get(ConnectionObjectKey.CONNECTION_TYPE, "")
        connection_type_lower = connection_type.lower()

        # Check if this is a Redshift connection (direct type or JDBC with Redshift vendor)
        if connection_type_lower == "redshift" or (
            connection_type_lower == "jdbc" and cls._is_redshift_jdbc_connection(wrapper_input)
        ):
            return RedshiftJDBCConnectionWrapper(wrapper_input)
        # Handle remaining JDBC types
        elif connection_type_lower in JDBC_CONNECTION_TYPES:
            return JDBCConnectionWrapper(wrapper_input)
        # Route specific connection types to specialized wrappers
        elif connection_type_lower in ("mongodb", "documentdb"):
            return MongoDBConnectionWrapper(wrapper_input)
        elif connection_type_lower == "snowflake":
            return SnowflakeConnectionWrapper(wrapper_input)
        else:
            return NativeConnectionWrapper(wrapper_input)

    @abstractmethod
    def get_resolved_connection(self) -> Dict[str, Any]:
        """
        Get the AWS Glue Connection object with fully resolved spark properties.

        The output should be the AWS Glue Connection object itself. It will have the fully
        resolved spark options inside the SparkProperties field.

        Returns:
            AWS Glue Connection object with resolved SparkProperties field

        Example return structure:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/glue/client/get_connection.html#
        """
        pass

    def get_jdbc_conf(self) -> JDBCConf:
        """Get JDBC configuration for the connection."""
        try:
            props = get_connection_properties(self._connection)
            connection_type_lower = self._connection.get(
                ConnectionObjectKey.CONNECTION_TYPE, ""
            ).lower()

            if not is_jdbc_connection_needed(connection_type_lower):
                raise Exception(
                    f"Connection type is not JDBC nor one of types in {JDBC_CONNECTION_TYPES}"
                )

            # Get password (encrypted or plain)
            def get_password(props: Dict[str, str]) -> str:
                encrypted_password = props.get(ConnectionPropertyKey.ENCRYPTED_PASSWORD)
                if encrypted_password:
                    self.log.debug(
                        "Encrypted Catalog password is not empty, now decrypting encrypted value"
                    )
                    return decrypt_encrypted_password(encrypted_password, self._kms_client)

                password = props.get(ConnectionPropertyKey.PASSWORD)
                if password:
                    self.log.debug(
                        "Encrypted Catalog password is empty, using value of unencrypted Catalog password"
                    )
                    return password

                raise Exception(
                    "Encrypted Catalog password is empty and couldn't get plain text password from the connection properties map"
                )

            # Get user and password
            username = props.get(ConnectionPropertyKey.USERNAME)
            if username:
                user, password = username, get_password(props)
            else:
                secret_id = props.get(ConnectionPropertyKey.SECRET_ID)
                if secret_id:
                    secrets_map = get_secret_options(
                        {"secretId": secret_id}, self._secrets_manager_client
                    )
                    if (
                        ConnectionPropertyKey.USERNAME.lower() in secrets_map
                        and ConnectionPropertyKey.PASSWORD.lower() in secrets_map
                    ):
                        user, password = (
                            secrets_map[ConnectionPropertyKey.USERNAME.lower()],
                            secrets_map[ConnectionPropertyKey.PASSWORD.lower()],
                        )
                    elif (
                        ConnectionPropertyKey.USERNAME in secrets_map
                        and ConnectionPropertyKey.PASSWORD in secrets_map
                    ):
                        user, password = (
                            secrets_map[ConnectionPropertyKey.USERNAME],
                            secrets_map[ConnectionPropertyKey.PASSWORD],
                        )
                    else:
                        raise ValueError("Username and password for the secretId are required")
                else:
                    # Check if this is IAM authentication, which doesn't require username or secretId
                    auth_config = self._connection.get(
                        ConnectionObjectKey.AUTHENTICATION_CONFIGURATION
                    )
                    if auth_config and auth_config.get("AuthenticationType") == "IAM":
                        user, password = None, None  # Null credentials for IAM authentication
                    else:
                        raise ValueError(
                            "Must specify username or secretId for JDBC connection (unless using IAM authentication)"
                        )

            # Get URL and vendor
            if connection_type_lower in ("mongodb", "documentdb"):
                url, full_url, vendor = get_vendor_from_url(
                    props[ConnectionPropertyKey.CONNECTION_URL]
                )
            elif connection_type_lower in JDBC_CONNECTION_TYPES:
                # JDBC connections such as Redshift/Oracle etc.
                url, full_url, vendor = get_vendor_from_url(
                    props[ConnectionPropertyKey.JDBC_CONNECTION_URL]
                )
            else:
                # Native JDBC connections such as Saphana/Teradata etc.
                url = props[SparkOptionsKey.URL]
                full_url = props[SparkOptionsKey.URL]
                vendor = connection_type_lower

            # Get SSL and certificate options
            enforce_ssl = props.get(ConnectionPropertyKey.JDBC_ENFORCE_SSL, "false")
            custom_jdbc_cert = props.get(ConnectionPropertyKey.CUSTOM_JDBC_CERT, "")
            skip_custom_jdbc_cert_validation = props.get(
                ConnectionPropertyKey.SKIP_CUSTOM_JDBC_CERT_VALIDATION, "false"
            )
            custom_jdbc_cert_string = props.get(ConnectionPropertyKey.CUSTOM_JDBC_CERT_STRING, "")

            return JDBCConf(
                user=user,
                password=password,
                vendor=vendor,
                url=url,
                enforce_ssl=enforce_ssl,
                custom_jdbc_cert=custom_jdbc_cert,
                skip_custom_jdbc_cert_validation=skip_custom_jdbc_cert_validation,
                custom_jdbc_cert_string=custom_jdbc_cert_string,
                full_url=full_url,
            )

        except Exception as ex:
            raise ex
