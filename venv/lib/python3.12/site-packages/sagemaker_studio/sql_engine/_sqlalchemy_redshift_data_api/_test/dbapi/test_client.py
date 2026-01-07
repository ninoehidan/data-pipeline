"""
Unit tests for boto3 client management and authentication.

Tests the RedshiftDataAPIClient class with mocked boto3 client for various
authentication scenarios and error conditions.
"""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

from ...dbapi.client import RedshiftDataAPIClient, create_client
from ...dbapi.connection_params import ConnectionParams
from ...dbapi.exceptions import ClusterNotFoundError, InterfaceError, OperationalError


class TestRedshiftDataAPIClient:
    """Test cases for RedshiftDataAPIClient class."""

    def test_successful_initialization_with_explicit_credentials(self):
        """Test successful client initialization with explicit AWS credentials."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock successful list_databases call for validation
            mock_client.list_databases.return_value = {"Databases": ["test_db", "other_db"]}

            client = RedshiftDataAPIClient(connection_params)

            # Verify session was created with explicit credentials
            mock_session_class.assert_called_once_with(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            )

            # Verify client creation
            mock_session.client.assert_called_once_with("redshift-data", region_name="us-east-1")

            assert client.client == mock_client
            assert client.session == mock_session

    def test_successful_initialization_with_temporary_credentials(self):
        """Test successful client initialization with temporary AWS credentials."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            aws_access_key_id="ASIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            aws_session_token="AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock successful list_databases call for validation
            mock_client.list_databases.return_value = {"Databases": ["test_db"]}

            client = RedshiftDataAPIClient(connection_params)

            # Verify session was created with temporary credentials
            mock_session_class.assert_called_once_with(
                aws_access_key_id="ASIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                aws_session_token="AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE",
            )

            assert client.client == mock_client

    def test_successful_initialization_with_named_profile(self):
        """Test successful client initialization with named AWS profile."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            profile_name="my-profile",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock successful list_databases call for validation
            mock_client.list_databases.return_value = {"Databases": ["test_db"]}

            client = RedshiftDataAPIClient(connection_params)

            # Verify session was created with named profile
            mock_session_class.assert_called_once_with(profile_name="my-profile")

            assert client.client == mock_client

    def test_successful_initialization_with_default_credentials(self):
        """Test successful client initialization with default credential chain."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock successful list_databases call for validation
            mock_client.list_databases.return_value = {"Databases": ["test_db"]}

            client = RedshiftDataAPIClient(connection_params)

            # Verify session was created with no explicit parameters (default chain)
            mock_session_class.assert_called_once_with()

            assert client.client == mock_client

    def test_explicit_credentials_session_creation_error(self):
        """Test handling of session creation error with explicit credentials."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session_class.side_effect = Exception("Invalid credentials format")

            with pytest.raises(InterfaceError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "Failed to initialize Redshift Data API client" in str(exc_info.value)
            assert "Failed to create session with explicit credentials" in str(exc_info.value)

    def test_named_profile_session_creation_error(self):
        """Test handling of session creation error with named profile."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            profile_name="nonexistent-profile",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session_class.side_effect = Exception("Profile not found")

            with pytest.raises(InterfaceError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "Failed to initialize Redshift Data API client" in str(exc_info.value)
            assert "Failed to create session with profile 'nonexistent-profile'" in str(
                exc_info.value
            )

    def test_default_credentials_session_creation_error(self):
        """Test handling of session creation error with default credentials."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session_class.side_effect = Exception("No credentials available")

            with pytest.raises(InterfaceError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "Failed to initialize Redshift Data API client" in str(exc_info.value)
            assert "Failed to create session with default credentials" in str(exc_info.value)

    def test_get_auth_method_description_explicit_credentials(self):
        """Test auth method description for explicit credentials."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client
            mock_client.list_databases.return_value = {"Databases": []}

            client = RedshiftDataAPIClient(connection_params)
            description = client._get_auth_method_description()

            assert description == "explicit AWS credentials"

    def test_get_auth_method_description_temporary_credentials(self):
        """Test auth method description for temporary credentials."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            aws_access_key_id="ASIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            aws_session_token="session_token_here",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client
            mock_client.list_databases.return_value = {"Databases": []}

            client = RedshiftDataAPIClient(connection_params)
            description = client._get_auth_method_description()

            assert description == "explicit temporary AWS credentials"

    def test_get_auth_method_description_named_profile(self):
        """Test auth method description for named profile."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            profile_name="my-profile",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client
            mock_client.list_databases.return_value = {"Databases": []}

            client = RedshiftDataAPIClient(connection_params)
            description = client._get_auth_method_description()

            assert description == "AWS profile 'my-profile'"

    def test_get_auth_method_description_default_chain(self):
        """Test auth method description for default credential chain."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client
            mock_client.list_databases.return_value = {"Databases": []}

            client = RedshiftDataAPIClient(connection_params)
            description = client._get_auth_method_description()

            assert description == "default AWS credential chain"

    def test_successful_initialization_provisioned_cluster(self):
        """Test successful client initialization for provisioned cluster."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock successful list_databases call for validation
            mock_client.list_databases.return_value = {"Databases": ["test_db", "other_db"]}

            client = RedshiftDataAPIClient(connection_params)

            # Verify session and client creation
            mock_session_class.assert_called_once()
            mock_session.client.assert_called_once_with("redshift-data", region_name="us-east-1")

            # Verify validation call
            mock_client.list_databases.assert_called_once_with(
                Database="test_db", DbUser="test_user", ClusterIdentifier="test-cluster"
            )

            # Verify client properties
            assert client.client == mock_client
            assert client.session == mock_session

    def test_successful_initialization_serverless_workgroup(self):
        """Test successful client initialization for serverless workgroup."""
        connection_params = ConnectionParams(
            database_name="test_db",
            db_user="test_user",
            region="us-west-2",
            workgroup_name="test-workgroup",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock successful list_databases call for validation
            mock_client.list_databases.return_value = {"Databases": ["test_db"]}

            RedshiftDataAPIClient(connection_params)

            # Verify validation call uses workgroup and includes DbUser when provided
            mock_client.list_databases.assert_called_once_with(
                Database="test_db", DbUser="test_user", WorkgroupName="test-workgroup"
            )

    def test_initialization_provisioned_without_db_user(self):
        """Test client initialization for provisioned cluster without db_user."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user=None,  # Explicitly set to None
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock successful list_databases call for validation
            mock_client.list_databases.return_value = {"Databases": ["test_db"]}

            RedshiftDataAPIClient(connection_params)

            # Verify validation call does not include DbUser when db_user is None
            mock_client.list_databases.assert_called_once_with(
                Database="test_db", ClusterIdentifier="test-cluster"
            )

    def test_initialization_with_secret_arn(self):
        """Test client initialization with secret ARN."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            secret_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            mock_client.list_databases.return_value = {"Databases": []}

            RedshiftDataAPIClient(connection_params)

            # Verify validation call includes secret ARN (no DbUser when using secret ARN)
            mock_client.list_databases.assert_called_once_with(
                Database="test_db",
                ClusterIdentifier="test-cluster",
                SecretArn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret",
            )

    def test_no_credentials_error(self):
        """Test handling of missing AWS credentials."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session_class.side_effect = NoCredentialsError()

            with pytest.raises(OperationalError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "AWS credentials not found" in str(exc_info.value)

    def test_partial_credentials_error(self):
        """Test handling of incomplete AWS credentials."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session_class.side_effect = PartialCredentialsError(
                provider="env", cred_var="AWS_SECRET_ACCESS_KEY"
            )

            with pytest.raises(OperationalError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "Incomplete AWS credentials" in str(exc_info.value)

    def test_client_initialization_error(self):
        """Test handling of general client initialization errors."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="invalid-region",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.side_effect = Exception("Invalid region")

            with pytest.raises(InterfaceError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "Failed to initialize Redshift Data API client" in str(exc_info.value)

    def test_cluster_not_found_error(self):
        """Test handling of cluster not found during validation."""
        connection_params = ConnectionParams(
            cluster_identifier="nonexistent-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock cluster not found error
            error_response = {
                "Error": {
                    "Code": "ClusterNotFoundFault",
                    "Message": "Cluster nonexistent-cluster not found",
                }
            }
            mock_client.list_databases.side_effect = ClientError(error_response, "ListDatabases")

            with pytest.raises(ClusterNotFoundError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "nonexistent-cluster" in str(exc_info.value)
            assert "not found" in str(exc_info.value)

    def test_workgroup_not_found_error(self):
        """Test handling of workgroup not found during validation."""
        connection_params = ConnectionParams(
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
            workgroup_name="nonexistent-workgroup",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock workgroup not found error
            error_response = {
                "Error": {
                    "Code": "WorkgroupNotFoundFault",
                    "Message": "Workgroup nonexistent-workgroup not found",
                }
            }
            mock_client.list_databases.side_effect = ClientError(error_response, "ListDatabases")

            with pytest.raises(ClusterNotFoundError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "nonexistent-workgroup" in str(exc_info.value)

    def test_access_denied_error(self):
        """Test handling of access denied during validation."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock access denied error
            error_response = {
                "Error": {
                    "Code": "AccessDeniedFault",
                    "Message": "User does not have permission to access cluster",
                }
            }
            mock_client.list_databases.side_effect = ClientError(error_response, "ListDatabases")

            with pytest.raises(OperationalError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "Access denied" in str(exc_info.value)
            assert "IAM permissions" in str(exc_info.value)

    def test_validation_exception_error(self):
        """Test handling of validation exception during validation."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock validation exception
            error_response = {
                "Error": {"Code": "ValidationException", "Message": "Invalid parameter value"}
            }
            mock_client.list_databases.side_effect = ClientError(error_response, "ListDatabases")

            with pytest.raises(InterfaceError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "Invalid parameters" in str(exc_info.value)

    def test_unexpected_validation_error(self):
        """Test handling of unexpected errors during validation."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock unexpected error
            mock_client.list_databases.side_effect = Exception("Network timeout")

            with pytest.raises(OperationalError) as exc_info:
                RedshiftDataAPIClient(connection_params)

            assert "Unexpected error during connection validation" in str(exc_info.value)

    def test_get_credentials_info(self):
        """Test getting credential information."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_credentials = Mock()

            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client
            mock_session.get_credentials.return_value = mock_credentials

            mock_credentials.access_key = "AKIAIOSFODNN7EXAMPLE"
            mock_credentials.method = "iam-role"

            mock_client.list_databases.return_value = {"Databases": []}

            client = RedshiftDataAPIClient(connection_params)
            cred_info = client.get_credentials_info()

            assert cred_info["access_key_id"] == "AKIAIOSF..."
            assert cred_info["method"] == "iam-role"
            assert cred_info["region"] == "us-east-1"

    def test_get_credentials_info_no_credentials(self):
        """Test getting credential information when no credentials available."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()

            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client
            mock_session.get_credentials.return_value = None

            mock_client.list_databases.return_value = {"Databases": []}

            client = RedshiftDataAPIClient(connection_params)
            cred_info = client.get_credentials_info()

            assert "error" in cred_info
            assert "No credentials found" in cred_info["error"]

    def test_test_permissions_success(self):
        """Test permission testing with successful results."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock successful API calls
            mock_client.list_databases.return_value = {"Databases": []}
            mock_client.execute_statement.return_value = {"Id": "statement-123"}

            client = RedshiftDataAPIClient(connection_params)
            permissions = client.test_permissions()

            assert permissions["list_databases"] is True
            assert permissions["execute_statement"] is True

            # Verify execute_statement was called with correct parameters
            mock_client.execute_statement.assert_called_once_with(
                Database="test_db",
                DbUser="test_user",
                Sql="SELECT 1",
                ClusterIdentifier="test-cluster",
            )

    def test_test_permissions_failure(self):
        """Test permission testing with failed results."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            # Mock successful validation but failed permission tests
            mock_client.list_databases.side_effect = [
                {"Databases": []},  # First call for validation
                Exception("Access denied"),  # Second call for permission test
            ]
            mock_client.execute_statement.side_effect = Exception("Permission denied")

            client = RedshiftDataAPIClient(connection_params)
            permissions = client.test_permissions()

            assert permissions["list_databases"] is False
            assert permissions["execute_statement"] is False

    def test_close(self):
        """Test client cleanup."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            mock_client.list_databases.return_value = {"Databases": []}

            client = RedshiftDataAPIClient(connection_params)

            # Verify client is available before close
            assert client.client == mock_client

            client.close()

            # Verify client is cleaned up after close
            with pytest.raises(InterfaceError):
                _ = client.client

    def test_client_property_after_close(self):
        """Test accessing client property after close raises error."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            mock_client.list_databases.return_value = {"Databases": []}

            client = RedshiftDataAPIClient(connection_params)
            client.close()

            with pytest.raises(InterfaceError) as exc_info:
                _ = client.client

            assert "Client not initialized" in str(exc_info.value)

    def test_session_property_after_close(self):
        """Test accessing session property after close raises error."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            mock_client.list_databases.return_value = {"Databases": []}

            client = RedshiftDataAPIClient(connection_params)
            client.close()

            with pytest.raises(InterfaceError) as exc_info:
                _ = client.session

            assert "Session not initialized" in str(exc_info.value)


class TestCreateClient:
    """Test cases for create_client function."""

    def test_create_client_success(self):
        """Test successful client creation using create_client function."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_session_class.return_value = mock_session
            mock_session.client.return_value = mock_client

            mock_client.list_databases.return_value = {"Databases": []}

            client = create_client(connection_params)

            assert isinstance(client, RedshiftDataAPIClient)
            assert client.connection_params == connection_params

    def test_create_client_propagates_errors(self):
        """Test that create_client propagates initialization errors."""
        connection_params = ConnectionParams(
            cluster_identifier="test-cluster",
            database_name="test_db",
            db_user="test_user",
            region="us-east-1",
        )

        with patch("boto3.Session") as mock_session_class:
            mock_session_class.side_effect = NoCredentialsError()

            with pytest.raises(OperationalError):
                create_client(connection_params)


if __name__ == "__main__":
    pytest.main([__file__])
