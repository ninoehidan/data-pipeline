"""Tests for AthenaSparkSessionManager."""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock Project class before any imports to prevent Domain ID error
with patch("sagemaker_studio.Project"):

    # Mock pyspark before importing  # noqa: E402
    sys.modules["pyspark"] = Mock()
    sys.modules["pyspark.sql"] = Mock()
    sys.modules["pyspark.sql.connect"] = Mock()
    sys.modules["pyspark.sql.connect.session"] = Mock()
    sys.modules["pyspark.sql.connect.client"] = Mock()
    sys.modules["aws_embedded_metrics"] = Mock()
    sys.modules["aws_embedded_metrics.sinks"] = Mock()
    sys.modules["aws_embedded_metrics.sinks.stdout_sink"] = Mock()
    sys.modules["aws_embedded_metrics.logger"] = Mock()
    sys.modules["aws_embedded_metrics.logger.metrics_logger"] = Mock()
    sys.modules["aws_embedded_metrics.logger.metrics_context"] = Mock()
    sys.modules["aws_embedded_metrics.environment"] = Mock()
    sys.modules["aws_embedded_metrics.environment.local_environment"] = Mock()

    pyspark_modules = [
        "pyspark",
        "pyspark.sql",
        "pyspark.sql.session",
        "pyspark.sql.connect",
        "pyspark.sql.connect.session",
        "pyspark.sql.connect.client",
        "grpc",
        "pyspark.errors",
        "pyspark.errors.exceptions",
        "pyspark.errors.exceptions.connect",
    ]

    for module_name in pyspark_modules:
        if module_name not in sys.modules:
            mock_module = Mock()
            if module_name == "grpc":
                # Mock gRPC specific classes and functions
                mock_module.insecure_channel = Mock()
                mock_module.secure_channel = Mock()
                mock_module.intercept_channel = Mock()
                mock_module.UnaryUnaryClientInterceptor = Mock()
                mock_module.UnaryStreamClientInterceptor = Mock()
                mock_module.StreamUnaryClientInterceptor = Mock()
                mock_module.StreamStreamClientInterceptor = Mock()
                mock_module.ClientCallDetails = Mock()
            elif module_name == "pyspark.sql.connect.client":
                mock_module.ChannelBuilder = Mock()
            sys.modules[module_name] = mock_module

    # Mock the interceptors module to avoid importing the actual interceptors
    mock_interceptors = Mock()
    mock_interceptors.CustomChannelBuilder = Mock()
    sys.modules["sagemaker_studio.utils.spark.session.athena.interceptors"] = mock_interceptors

    from sagemaker_studio.utils.spark.session.athena.athena_spark_session_manager import (
        AthenaSparkSessionManager,
    )


@pytest.fixture
def mock_boto3_clients():
    """Mocks boto3 athena and sts clients."""
    athena_client = MagicMock()
    sts_client = MagicMock()
    sts_client.get_caller_identity.return_value = {
        "UserId": "abc:random-user-id",
        "Account": "1234567890",
    }

    with patch("boto3.client") as mock_boto_client:
        mock_boto_client.side_effect = lambda service_name, **kwargs: (
            athena_client if service_name == "athena" else sts_client
        )
        yield athena_client, sts_client


@pytest.fixture
def mock_internal_utils():
    """Mocks InternalUtils and Project setup."""
    with patch(
        "sagemaker_studio.utils.spark.session.athena.athena_spark_session_manager.InternalUtils"
    ) as mock_utils, patch(
        "sagemaker_studio.utils.spark.session.athena.athena_spark_session_manager.Project"
    ) as mock_project:
        mock_utils.return_value._get_domain_region.return_value = "us-west-2"
        mock_project.return_value.connection.return_value.data.workgroup_name = "test_workgroup"
        yield mock_utils, mock_project


@pytest.fixture
def manager(mock_boto3_clients, mock_internal_utils):
    """Create a testable AthenaSparkSessionManager with mocks injected."""
    mgr = AthenaSparkSessionManager(connection_name="test_connection")
    return mgr


def test_lazy_init_creates_clients(manager, mock_boto3_clients, mock_internal_utils):
    """Ensure _lazy_init sets up athena and sts clients and workgroup."""
    athena_client, sts_client = mock_boto3_clients
    manager._lazy_init()

    assert manager.athena_client is athena_client
    assert manager.sts_client is sts_client
    assert manager.workgroup_name == "test_workgroup"


@patch("sagemaker_studio.utils.spark.session.athena.athena_spark_session_manager._SparkSession")
@patch(
    "sagemaker_studio.utils.spark.session.athena.athena_spark_session_manager.CustomChannelBuilder"
)
def test_create_starts_session(
    mock_channel_builder, mock_spark_session, manager, mock_boto3_clients, mock_internal_utils
):
    """Ensure create() builds a SparkSession and calls required AWS methods."""
    athena_client, sts_client = mock_boto3_clients

    # Mock _start_athena_session to return fake session ID and endpoint URL
    manager._start_athena_session = MagicMock(return_value=("fake-session", "sc://endpoint"))

    # Mock builder chain
    builder = MagicMock()
    mock_spark_session.builder.channelBuilder.return_value = builder
    builder.appName.return_value = builder
    builder.getOrCreate.return_value = "mock_spark_session"

    session = manager.create()

    assert session == "mock_spark_session"
    assert manager.athena_session_id == "fake-session"
    mock_channel_builder.assert_called_once()
    builder.getOrCreate.assert_called_once()


def test_construct_spark_endpoint_url(manager):
    """Ensure spark endpoint URL is properly constructed."""
    response = {"EndpointUrl": "https://athena.aws.com/session", "AuthToken": "XYZ"}
    url = manager._construct_spark_endpoint_url(response)

    assert url.startswith("sc://athena.aws.com")
    assert "x-aws-proxy-auth=XYZ" in url


def test_get_user_id_parses_correctly_from_metadata(manager, mock_boto3_clients):
    """Ensure _get_user_id gets values from InternalUtils metadata when available."""
    _, sts_client = mock_boto3_clients
    manager.sts_client = sts_client

    # Mock InternalUtils to return metadata values
    with patch(
        "sagemaker_studio.utils.spark.session.athena.athena_spark_session_manager.InternalUtils"
    ) as mock_utils:
        mock_utils_instance = mock_utils.return_value
        mock_utils_instance._get_account_id.return_value = "9876543210"
        mock_utils_instance._get_user_id.return_value = "metadata-user-id"

        user_id, account_id = manager._get_user_id_account_id()

        assert user_id == "metadata-user-id"
        assert account_id == "9876543210"
        # Verify InternalUtils was called
        mock_utils_instance._get_account_id.assert_called_once()
        mock_utils_instance._get_user_id.assert_called_once()
        # Verify STS was not called since metadata was available
        sts_client.get_caller_identity.assert_not_called()


def test_get_user_id_parses_correctly_from_sts(manager, mock_boto3_clients):
    """Ensure _get_user_id falls back to STS when metadata is not available and parses UserId correctly."""
    _, sts_client = mock_boto3_clients
    manager.sts_client = sts_client

    # Mock InternalUtils to return None/empty values to trigger STS fallback
    with patch(
        "sagemaker_studio.utils.spark.session.athena.athena_spark_session_manager.InternalUtils"
    ) as mock_utils:
        mock_utils_instance = mock_utils.return_value
        mock_utils_instance._get_account_id.return_value = None
        mock_utils_instance._get_user_id.return_value = None

        user_id, account_id = manager._get_user_id_account_id()

        # Should extract "random-user-id" from "abc:random-user-id"
        assert user_id == "random-user-id"
        assert account_id == "1234567890"
        # Verify InternalUtils was called first
        mock_utils_instance._get_account_id.assert_called_once()
        mock_utils_instance._get_user_id.assert_called_once()
        # Verify STS was called as fallback
        sts_client.get_caller_identity.assert_called_once()


def test_wait_for_athena_session_ready(manager, mock_boto3_clients):
    """Ensure wait_for_athena_session returns True when session ready."""
    athena_client, _ = mock_boto3_clients
    athena_client.get_session.return_value = {
        "Status": {"State": "CREATED"},
    }
    manager.athena_client = athena_client
    assert manager._wait_for_athena_session("sess-1", timeout=5, poll_interval=0.1)


def test_wait_for_athena_session_failure(manager, mock_boto3_clients):
    """Ensure wait_for_athena_session raises when FAILED state returned."""
    athena_client, _ = mock_boto3_clients
    athena_client.get_session.return_value = {
        "Status": {"State": "FAILED", "StateChangeReason": "Error"},
    }
    manager.athena_client = athena_client

    with pytest.raises(RuntimeError):
        manager._wait_for_athena_session("sess-2", timeout=1, poll_interval=0.1)


def test_terminate_session_calls_aws(manager, mock_boto3_clients):
    """Ensure terminate_session calls Athena client."""
    athena_client, _ = mock_boto3_clients
    manager.athena_client = athena_client

    manager._terminate_athena_session("sess-3")
    athena_client.terminate_session.assert_called_once_with(SessionId="sess-3")


@patch.object(AthenaSparkSessionManager, "_terminate_athena_session")
def test_stop_cleans_up(mock_terminate, manager):
    """Ensure stop() cleans up both Spark and Athena sessions."""
    manager._spark_session = MagicMock()
    manager.athena_session_id = "sess-123"

    manager.stop()

    mock_terminate.assert_called_once_with("sess-123")
    assert manager._spark_session is None
    assert manager.athena_session_id is None
