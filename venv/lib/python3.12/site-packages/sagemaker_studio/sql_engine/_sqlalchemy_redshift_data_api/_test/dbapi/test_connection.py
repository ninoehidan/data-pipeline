"""
Unit tests for the Connection class.

Tests connection lifecycle, transaction management, and error handling.
"""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from ...dbapi.connection import Connection
from ...dbapi.exceptions import DatabaseError, InterfaceError


class TestConnection:
    """Test cases for the Connection class."""

    @pytest.fixture
    def mock_client_manager(self):
        """Create a mock RedshiftDataAPIClient."""
        mock_manager = Mock()
        mock_client = Mock()
        mock_manager.client = mock_client
        return mock_manager, mock_client

    @pytest.fixture
    def provisioned_connection_params(self):
        """Standard provisioned connection parameters for testing."""
        return {
            "database_name": "test-db",
            "cluster_identifier": "test-cluster",
            "db_user": "test-user",
            "region": "us-east-1",
        }

    @pytest.fixture
    def serverless_connection_params(self):
        """Standard serverless connection parameters for testing."""
        return {
            "database_name": "test-db",
            "workgroup_name": "test-workgroup",
            "db_user": "test-user",
            "region": "us-east-1",
        }

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_connection_initialization(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test connection initialization with proper parameters."""
        # Setup mocks
        mock_params = Mock()
        mock_create_params.return_value = mock_params
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Create connection
        conn = Connection(**provisioned_connection_params)

        # Verify initialization
        mock_create_params.assert_called_once_with(**provisioned_connection_params)
        mock_client_class.assert_called_once_with(mock_params)
        assert conn.connection_params == mock_params
        assert conn.client_manager == mock_client_instance
        assert not conn._closed
        assert conn.transaction_id is None
        assert conn.autocommit is True

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_cursor_creation(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test cursor creation from connection."""
        # Setup mocks
        mock_create_params.return_value = Mock()
        mock_client_class.return_value = Mock()

        # Create connection and cursor
        conn = Connection(**provisioned_connection_params)
        cursor = conn.cursor()

        # Verify cursor creation
        assert cursor is not None
        assert cursor.connection == conn

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_cursor_creation_closed_connection(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test cursor creation fails on closed connection."""
        # Setup mocks
        mock_create_params.return_value = Mock()
        mock_client_class.return_value = Mock()

        # Create and close connection
        conn = Connection(**provisioned_connection_params)
        conn.close()

        # Verify cursor creation fails
        with pytest.raises(InterfaceError, match="Connection is closed"):
            conn.cursor()

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_begin_transaction(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test beginning a new transaction."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = None
        mock_params.is_serverless = False  # Provisioned cluster
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-123"}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection and begin transaction
        conn = Connection(**provisioned_connection_params)
        txn_id = conn.begin_transaction()

        # Verify transaction creation
        assert txn_id == "txn-123"
        assert conn.transaction_id == "txn-123"
        mock_client.begin_transaction.assert_called_once_with(
            Database="test-db", DbUser="test-user", ClusterIdentifier="test-cluster"
        )

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_begin_transaction_with_workgroup(
        self, mock_create_params, mock_client_class, serverless_connection_params
    ):
        """Test beginning transaction with workgroup instead of cluster."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = None
        mock_params.workgroup_name = "test-workgroup"
        mock_params.secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-456"}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection and begin transaction
        conn = Connection(**serverless_connection_params)
        txn_id = conn.begin_transaction()

        # Verify transaction creation with workgroup (no DbUser for serverless)
        assert txn_id == "txn-456"
        mock_client.begin_transaction.assert_called_once_with(
            Database="test-db",
            WorkgroupName="test-workgroup",
            SecretArn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
        )

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_begin_transaction_already_active(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test beginning transaction when one is already active."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = None
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-123"}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection and begin transaction twice
        conn = Connection(**provisioned_connection_params)
        txn_id1 = conn.begin_transaction()
        txn_id2 = conn.begin_transaction()

        # Verify only one transaction is created
        assert txn_id1 == txn_id2 == "txn-123"
        mock_client.begin_transaction.assert_called_once()

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_begin_transaction_error(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test error handling during transaction creation."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = None
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid request"}},
            "BeginTransaction",
        )
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection and attempt to begin transaction
        conn = Connection(**provisioned_connection_params)

        with pytest.raises(DatabaseError, match="Failed to begin transaction"):
            conn.begin_transaction()

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_begin_transaction_without_db_user(self, mock_create_params, mock_client_class):
        """Test beginning transaction when db_user is None."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = None  # Explicitly set to None
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = None
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-123"}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection and begin transaction
        connection_params = {
            "database_name": "test-db",
            "cluster_identifier": "test-cluster",
            "db_user": None,
            "region": "us-east-1",
        }
        conn = Connection(**connection_params)
        txn_id = conn.begin_transaction()

        # Verify transaction creation without DbUser parameter
        assert txn_id == "txn-123"
        mock_client.begin_transaction.assert_called_once_with(
            Database="test-db", ClusterIdentifier="test-cluster"
        )

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_commit_transaction(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test committing a transaction."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = None
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-123"}
        mock_client.commit_transaction.return_value = {}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection, begin and commit transaction
        conn = Connection(**provisioned_connection_params)
        conn.begin_transaction()
        conn.commit()

        # Verify commit
        mock_client.commit_transaction.assert_called_once_with(TransactionId="txn-123")
        assert conn.transaction_id is None

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_commit_no_transaction(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test committing when no transaction is active."""
        # Setup mocks
        mock_create_params.return_value = Mock()
        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection and commit (no transaction)
        conn = Connection(**provisioned_connection_params)
        conn.commit()

        # Verify no commit call is made
        mock_client.commit_transaction.assert_not_called()

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_rollback_transaction(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test rolling back a transaction."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = None
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-123"}
        mock_client.rollback_transaction.return_value = {}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection, begin and rollback transaction
        conn = Connection(**provisioned_connection_params)
        conn.begin_transaction()
        conn.rollback()

        # Verify rollback
        mock_client.rollback_transaction.assert_called_once_with(TransactionId="txn-123")
        assert conn.transaction_id is None

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_rollback_no_transaction(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test rolling back when no transaction is active."""
        # Setup mocks
        mock_create_params.return_value = Mock()
        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection and rollback (no transaction)
        conn = Connection(**provisioned_connection_params)
        conn.rollback()

        # Verify no rollback call is made
        mock_client.rollback_transaction.assert_not_called()

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_autocommit_mode(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test autocommit mode setting."""
        # Setup mocks
        mock_create_params.return_value = Mock()
        mock_client_class.return_value = Mock()

        # Create connection and test autocommit
        conn = Connection(**provisioned_connection_params)
        assert conn.autocommit is True

        conn.set_autocommit(False)
        assert conn.autocommit is False

        conn.set_autocommit(True)
        assert conn.autocommit is True

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_connection_close_with_transaction(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test closing connection with active transaction."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = None
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-123"}
        mock_client.rollback_transaction.return_value = {}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection, begin transaction, and close
        conn = Connection(**provisioned_connection_params)
        conn.begin_transaction()
        conn.close()

        # Verify transaction is rolled back and connection is closed
        mock_client.rollback_transaction.assert_called_once_with(TransactionId="txn-123")
        mock_client_instance.close.assert_called_once()
        assert conn.is_closed()

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_connection_close_rollback_error(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test closing connection when rollback fails."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = None
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-123"}
        mock_client.rollback_transaction.side_effect = Exception("Rollback failed")
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection, begin transaction, and close
        conn = Connection(**provisioned_connection_params)
        conn.begin_transaction()
        conn.close()  # Should not raise exception even if rollback fails

        # Verify connection is still closed despite rollback error
        assert conn.is_closed()
        mock_client_instance.close.assert_called_once()

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_operations_on_closed_connection(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test that operations fail on closed connection."""
        # Setup mocks
        mock_create_params.return_value = Mock()
        mock_client_class.return_value = Mock()

        # Create and close connection
        conn = Connection(**provisioned_connection_params)
        conn.close()

        # Verify operations fail
        with pytest.raises(InterfaceError, match="Connection is closed"):
            conn.cursor()

        with pytest.raises(InterfaceError, match="Connection is closed"):
            conn.commit()

        with pytest.raises(InterfaceError, match="Connection is closed"):
            conn.rollback()

        with pytest.raises(InterfaceError, match="Connection is closed"):
            conn.begin_transaction()

        with pytest.raises(InterfaceError, match="Connection is closed"):
            conn.set_autocommit(False)

        with pytest.raises(InterfaceError, match="Connection is closed"):
            conn.get_client_info()

        with pytest.raises(InterfaceError, match="Connection is closed"):
            conn.test_permissions()

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_transaction_id_management(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test transaction ID getter and management."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = None
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-123"}
        mock_client.commit_transaction.return_value = {}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection and test transaction ID management
        conn = Connection(**provisioned_connection_params)

        # Initially no transaction
        assert conn.get_transaction_id() is None

        # Begin transaction
        conn.begin_transaction()
        assert conn.get_transaction_id() == "txn-123"

        # Commit transaction
        conn.commit()
        assert conn.get_transaction_id() is None

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_client_property_access(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test client property access and error handling."""
        # Setup mocks
        mock_create_params.return_value = Mock()
        mock_client_instance = Mock()
        mock_boto3_client = Mock()
        mock_client_instance.client = mock_boto3_client
        mock_client_class.return_value = mock_client_instance

        # Create connection and test client access
        conn = Connection(**provisioned_connection_params)
        assert conn.client == mock_boto3_client

        # Close connection and test client access fails
        conn.close()
        with pytest.raises(InterfaceError, match="Connection is closed"):
            _ = conn.client

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_serverless_connection_initialization(
        self, mock_create_params, mock_client_class, serverless_connection_params
    ):
        """Test serverless connection initialization with proper parameters."""
        # Setup mocks
        mock_params = Mock()
        mock_params.is_serverless = True
        mock_create_params.return_value = mock_params
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Create serverless connection
        conn = Connection(**serverless_connection_params)

        # Verify initialization (cluster_identifier=None is passed explicitly)
        expected_params = dict(serverless_connection_params)
        expected_params["cluster_identifier"] = None
        mock_create_params.assert_called_once_with(**expected_params)
        mock_client_class.assert_called_once_with(mock_params)
        assert conn.connection_params == mock_params
        assert conn.client_manager == mock_client_instance
        assert not conn._closed
        assert conn.transaction_id is None
        assert conn.autocommit is True

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_serverless_transaction_operations(
        self, mock_create_params, mock_client_class, serverless_connection_params
    ):
        """Test transaction operations with serverless configuration."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = None
        mock_params.workgroup_name = "test-workgroup"
        mock_params.secret_arn = None
        mock_params.is_serverless = True
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-serverless-123"}
        mock_client.commit_transaction.return_value = {}
        mock_client.rollback_transaction.return_value = {}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create serverless connection and test transaction lifecycle
        conn = Connection(**serverless_connection_params)

        # Begin transaction
        txn_id = conn.begin_transaction()
        assert txn_id == "txn-serverless-123"
        mock_client.begin_transaction.assert_called_once_with(
            Database="test-db", DbUser="test-user", WorkgroupName="test-workgroup"
        )

        # Commit transaction
        conn.commit()
        mock_client.commit_transaction.assert_called_once_with(TransactionId="txn-serverless-123")
        assert conn.transaction_id is None

        # Begin another transaction and rollback
        conn.begin_transaction()
        conn.rollback()
        mock_client.rollback_transaction.assert_called_once_with(TransactionId="txn-serverless-123")
        assert conn.transaction_id is None

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_connection_with_minimal_parameters(self, mock_create_params, mock_client_class):
        """Test connection creation with minimal required parameters."""
        # Setup mocks
        mock_params = Mock()
        mock_create_params.return_value = mock_params
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Create connection with minimal parameters (database only)
        conn = Connection(database_name="test-db")

        # Verify initialization with defaults
        mock_create_params.assert_called_once_with(
            database_name="test-db", cluster_identifier=None, db_user=None, region="us-east-1"
        )
        assert conn.connection_params == mock_params
        assert not conn._closed
        assert conn.autocommit is True

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_connection_with_secret_arn(self, mock_create_params, mock_client_class):
        """Test connection creation with secret ARN for authentication."""
        # Setup mocks
        mock_params = Mock()
        mock_params.database_name = "test-db"
        mock_params.db_user = "test-user"
        mock_params.cluster_identifier = "test-cluster"
        mock_params.workgroup_name = None
        mock_params.secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"
        mock_params.is_serverless = False  # Provisioned cluster
        mock_create_params.return_value = mock_params

        mock_client_instance = Mock()
        mock_client = Mock()
        mock_client.begin_transaction.return_value = {"TransactionId": "txn-secret-123"}
        mock_client_instance.client = mock_client
        mock_client_class.return_value = mock_client_instance

        # Create connection with secret ARN
        conn = Connection(
            database_name="test-db",
            cluster_identifier="test-cluster",
            db_user="test-user",
            secret_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
        )

        # Test transaction with secret ARN
        conn.begin_transaction()
        mock_client.begin_transaction.assert_called_once_with(
            Database="test-db",
            ClusterIdentifier="test-cluster",
            SecretArn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
        )

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_connection_state_tracking(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test connection state tracking and resource cleanup."""
        # Setup mocks
        mock_params = Mock()
        mock_create_params.return_value = mock_params
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Create connection and test state tracking
        conn = Connection(**provisioned_connection_params)

        # Initially open
        assert not conn.is_closed()
        assert conn._closed is False

        # Close connection
        conn.close()
        assert conn.is_closed()
        assert conn._closed is True

        # Verify client manager cleanup was called
        mock_client_instance.close.assert_called_once()

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    def test_autocommit_mode_operations(
        self, mock_create_params, mock_client_class, provisioned_connection_params
    ):
        """Test autocommit mode behavior."""
        # Setup mocks
        mock_create_params.return_value = Mock()
        mock_client_class.return_value = Mock()

        # Create connection and test autocommit mode
        conn = Connection(**provisioned_connection_params)

        # Test default autocommit mode
        assert conn.autocommit is True

        # Test setting autocommit to False
        conn.set_autocommit(False)
        assert conn.autocommit is False

        # Test setting autocommit back to True
        conn.set_autocommit(True)
        assert conn.autocommit is True

        # Test that autocommit setting fails on closed connection
        conn.close()
        with pytest.raises(InterfaceError, match="Connection is closed"):
            conn.set_autocommit(False)
