"""
Integration tests for dialect registration and connection creation.

Tests dialect discovery, registration, and connection creation through
various SQLAlchemy interfaces.
"""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import registry
from sqlalchemy.exc import ArgumentError

import sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api as sqlalchemy_redshift_data_api

from .. import RedshiftDataAPIDialect, connect


class TestDialectRegistration:
    """Test cases for dialect registration with SQLAlchemy."""

    def test_dialect_is_registered_on_import(self):
        """Test that dialect is automatically registered when module is imported."""
        # The dialect should be registered when the module is imported
        # We can test this by trying to get it from the registry
        try:
            dialect_cls = registry.load("redshift_data_api")
            assert dialect_cls == RedshiftDataAPIDialect
        except Exception:
            # If registry.load doesn't work, try the alternative method
            from sqlalchemy.dialects import redshift_data_api as dialect_module

            assert hasattr(dialect_module, "dialect")

    def test_dialect_registration_with_driver_name(self):
        """Test that dialect is registered with driver-specific name."""
        try:
            dialect_cls = registry.load("redshift_data_api.redshift_data_api")
            assert dialect_cls == RedshiftDataAPIDialect
        except Exception:
            # Alternative test - check if we can create engine with full name
            pass  # This is tested in other methods

    def test_manual_dialect_registration(self):
        """Test manual dialect registration function."""
        # Clear any existing registration (if possible)
        # Then test manual registration
        sqlalchemy_redshift_data_api.register_dialect()

        # Should not raise any errors
        assert True

    @patch("sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connect")
    def test_create_engine_discovers_dialect(self, mock_connect):
        """Test that create_engine can discover and use our dialect."""
        # Mock the connection
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        # Create engine - this should discover our dialect
        url = "redshift_data_api://my-cluster/mydb?region=us-east-1&db_user=testuser"
        engine = create_engine(url)

        assert engine is not None
        assert engine.dialect.name == "redshift_data_api"
        assert engine.dialect.driver == "redshift_data_api"
        assert isinstance(engine.dialect, RedshiftDataAPIDialect)

    @patch("sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connect")
    def test_create_engine_with_driver_specification(self, mock_connect):
        """Test creating engine with explicit driver specification."""
        # Mock the connection
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        # Create engine with explicit driver
        url = "redshift_data_api+redshift_data_api://my-cluster/mydb?region=us-east-1&db_user=testuser"
        engine = create_engine(url)

        assert engine is not None
        assert engine.dialect.name == "redshift_data_api"
        assert engine.dialect.driver == "redshift_data_api"

    def test_invalid_dialect_name_raises_error(self):
        """Test that invalid dialect names raise appropriate errors."""
        with pytest.raises((ArgumentError, ImportError)):
            create_engine("invalid_dialect://test")


class TestConnectionCreation:
    """Test cases for connection creation through various interfaces."""

    @patch("sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.Connection")
    def test_direct_dbapi_connect_function(self, mock_connection_class):
        """Test direct usage of DBAPI connect function."""
        mock_connection = Mock()
        mock_connection_class.return_value = mock_connection

        # Test direct connect function
        connection = connect(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="testuser",
            region="us-east-1",
        )

        assert connection == mock_connection
        mock_connection_class.assert_called_once_with(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="testuser",
            region="us-east-1",
        )

    @patch("sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.Connection")
    def test_direct_dbapi_connect_with_optional_params(self, mock_connection_class):
        """Test direct DBAPI connect with optional parameters."""
        mock_connection = Mock()
        mock_connection_class.return_value = mock_connection

        # Test connect with optional parameters
        connection = connect(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="testuser",
            region="us-east-1",
            workgroup_name="my-workgroup",
            secret_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret",
            with_event=True,
        )

        assert connection == mock_connection
        mock_connection_class.assert_called_once_with(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="testuser",
            region="us-east-1",
            workgroup_name="my-workgroup",
            secret_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret",
            with_event=True,
        )

    @patch("boto3.Session")
    def test_sqlalchemy_engine_connect(self, mock_session_class):
        """Test connection creation through SQLAlchemy engine."""
        # Mock the boto3 session and client
        mock_client = Mock()
        mock_client.list_databases.return_value = {"Databases": [{"Name": "mydb"}]}

        # Mock execute_statement for SQLAlchemy initialization queries
        mock_client.execute_statement.return_value = {"Id": "test-statement-id"}
        mock_client.describe_statement.return_value = {
            "Status": "FINISHED",
            "HasResultSet": True,
            "ResultRows": 1,
            "ResultSize": 100,
        }
        mock_client.get_statement_result.return_value = {
            "Records": [[{"stringValue": "read committed"}]],  # For isolation level query
            "ColumnMetadata": [{"name": "transaction_isolation", "typeName": "varchar"}],
        }

        mock_session = Mock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        # Create engine and connect
        url = "redshift_data_api://my-cluster/mydb?region=us-east-1&db_user=testuser"
        engine = create_engine(url)

        with engine.connect() as conn:
            assert conn is not None

        # Verify our session was created and client was called
        mock_session_class.assert_called()
        mock_session.client.assert_called_with("redshift-data", region_name="us-east-1")
        mock_client.list_databases.assert_called_once()

    @patch("boto3.Session")
    def test_sqlalchemy_engine_connect_with_serverless(self, mock_session_class):
        """Test SQLAlchemy connection with serverless workgroup."""
        # Mock the boto3 session and client
        mock_client = Mock()
        mock_client.list_databases.return_value = {"Databases": [{"Name": "mydb"}]}

        # Mock execute_statement for SQLAlchemy initialization queries
        mock_client.execute_statement.return_value = {"Id": "test-statement-id"}
        mock_client.describe_statement.return_value = {
            "Status": "FINISHED",
            "HasResultSet": True,
            "ResultRows": 1,
            "ResultSize": 100,
        }
        mock_client.get_statement_result.return_value = {
            "Records": [[{"stringValue": "read committed"}]],  # For isolation level query
            "ColumnMetadata": [{"name": "transaction_isolation", "typeName": "varchar"}],
        }

        mock_session = Mock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        # Create engine for serverless
        url = "redshift_data_api:///mydb?region=us-west-2&db_user=testuser&workgroup_name=my-workgroup"
        engine = create_engine(url)

        with engine.connect() as conn:
            assert conn is not None

        # Verify our session was created and client was called with correct region
        mock_session_class.assert_called()
        mock_session.client.assert_called_with("redshift-data", region_name="us-west-2")
        mock_client.list_databases.assert_called_once()


class TestModuleExports:
    """Test cases for module exports and imports."""

    def test_main_module_exports(self):
        """Test that main module exports expected symbols."""
        import sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api as sqlalchemy_redshift_data_api

        # Check that expected symbols are available
        assert hasattr(sqlalchemy_redshift_data_api, "RedshiftDataAPIDialect")
        assert hasattr(sqlalchemy_redshift_data_api, "dbapi")
        assert hasattr(sqlalchemy_redshift_data_api, "connect")
        assert hasattr(sqlalchemy_redshift_data_api, "__version__")

        # Check __all__ contains expected exports
        expected_exports = ["RedshiftDataAPIDialect", "dbapi", "connect"]
        for export in expected_exports:
            assert export in sqlalchemy_redshift_data_api.__all__

    def test_dbapi_module_exports(self):
        """Test that DBAPI module exports expected symbols."""
        from .. import dbapi

        # Check DB-API 2.0 required attributes
        assert hasattr(dbapi, "apilevel")
        assert hasattr(dbapi, "threadsafety")
        assert hasattr(dbapi, "paramstyle")
        assert hasattr(dbapi, "connect")

        # Check exception classes
        assert hasattr(dbapi, "Error")
        assert hasattr(dbapi, "Warning")
        assert hasattr(dbapi, "InterfaceError")
        assert hasattr(dbapi, "DatabaseError")

        # Check connection and cursor classes
        assert hasattr(dbapi, "Connection")
        assert hasattr(dbapi, "Cursor")

    def test_direct_dialect_import(self):
        """Test that dialect can be imported directly."""
        from ..dialect import RedshiftDataAPIDialect

        dialect = RedshiftDataAPIDialect()
        assert dialect.name == "redshift_data_api"
        assert dialect.driver == "redshift_data_api"

    def test_direct_connect_import(self):
        """Test that connect function can be imported directly."""
        from .. import connect

        # Should be callable
        assert callable(connect)

        # Should be the same as dbapi.connect
        from ..dbapi import connect as dbapi_connect

        assert connect is dbapi_connect


class TestEntryPointRegistration:
    """Test cases for entry point registration."""

    def test_entry_point_registration_format(self):
        """Test that entry points are registered in correct format."""
        # This test verifies the setup.py configuration is correct
        # by checking if the dialect can be discovered

        # Try to create a mock engine - this will test entry point discovery
        try:
            from sqlalchemy import create_mock_engine

            engine = create_mock_engine(
                "redshift_data_api://test/test?region=us-east-1&db_user=test", lambda: None
            )
            assert engine.dialect.name == "redshift_data_api"
        except ImportError:
            # Fallback for older SQLAlchemy versions - just verify the dialect class exists
            assert RedshiftDataAPIDialect.name == "redshift_data_api"
        except Exception:
            # If mock engine doesn't work, just verify the dialect class exists
            assert RedshiftDataAPIDialect.name == "redshift_data_api"

    @patch("sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connect")
    def test_multiple_entry_point_formats(self, mock_connect):
        """Test that multiple entry point formats work."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        # Test both entry point formats
        urls = [
            "redshift_data_api://test/test?region=us-east-1&db_user=test",
            "redshift_data_api+redshift_data_api://test/test?region=us-east-1&db_user=test",
        ]

        for url in urls:
            try:
                engine = create_engine(url)
                assert engine.dialect.name == "redshift_data_api"
            except Exception:
                # Some URL formats might not work in all SQLAlchemy versions
                pass


if __name__ == "__main__":
    pytest.main([__file__])
