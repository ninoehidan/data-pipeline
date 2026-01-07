"""Tests for GlueConnectionWrapper factory method and abstract base class."""

import unittest
from typing import Any, Dict
from unittest.mock import Mock, patch

from sagemaker_studio.connections.glue_connection_lib import (
    GlueConnectionWrapper,
    GlueConnectionWrapperInputs,
)
from sagemaker_studio.connections.glue_connection_lib.connections.config.jdbc_conf import JDBCConf
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.jdbc.jdbc_wrapper import (
    JDBCConnectionWrapper,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.jdbc.redshift_wrapper import (
    RedshiftJDBCConnectionWrapper,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.local.mongodb_wrapper import (
    MongoDBConnectionWrapper,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.local.native_wrapper import (
    NativeConnectionWrapper,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.local.snowflake_wrapper import (
    SnowflakeConnectionWrapper,
)


class TestGlueConnectionWrapperInputs(unittest.TestCase):
    """Test cases for GlueConnectionWrapperInputs dataclass."""

    def test_initialization(self):
        """Test that GlueConnectionWrapperInputs can be initialized with required fields."""
        # Mock AWS clients
        mock_kms_client = Mock()
        mock_secrets_client = Mock()

        # Sample connection object
        connection = {
            "Name": "test-connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {"USERNAME": "testuser"},
        }

        # Additional options
        additional_options = {"option1": "value1"}

        # Create inputs
        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=mock_kms_client,
            secrets_manager_client=mock_secrets_client,
            additional_options=additional_options,
        )

        # Verify initialization
        self.assertEqual(inputs.connection, connection)
        self.assertEqual(inputs.additional_options, additional_options)
        self.assertEqual(inputs.kms_client, mock_kms_client)
        self.assertEqual(inputs.secrets_manager_client, mock_secrets_client)


class TestGlueConnectionWrapper(unittest.TestCase):
    """Test cases for GlueConnectionWrapper abstract base class and factory method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_kms_client = Mock()
        self.mock_secrets_client = Mock()

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that GlueConnectionWrapper cannot be instantiated directly."""
        connection = {"Name": "test", "ConnectionType": "JDBC"}
        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        with self.assertRaises(TypeError):
            GlueConnectionWrapper(inputs)  # type: ignore[abstract]

    def test_factory_method_routes_to_jdbc_wrapper(self):
        """Test that factory method routes JDBC connections to JDBCConnectionWrapper."""
        # Test with JDBC connection type
        jdbc_connection = {
            "Name": "jdbc-connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {"JDBC_CONNECTION_URL": "jdbc:postgresql://localhost:5432/db"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=jdbc_connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        self.assertIsInstance(wrapper, JDBCConnectionWrapper)

    def test_factory_method_routes_to_redshift_wrapper_for_redshift(self):
        """Test that factory method routes Redshift connections to RedshiftJDBCConnectionWrapper."""
        redshift_connection = {
            "Name": "redshift-connection",
            "ConnectionType": "redshift",
            "ConnectionProperties": {"JDBC_CONNECTION_URL": "jdbc:redshift://cluster:5439/db"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=redshift_connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        self.assertIsInstance(wrapper, RedshiftJDBCConnectionWrapper)

    def test_factory_method_routes_to_mongodb_wrapper_for_mongodb(self):
        """Test that factory method routes MongoDB connections to MongoDBConnectionWrapper."""
        mongodb_connection = {
            "Name": "mongodb-connection",
            "ConnectionType": "mongodb",
            "ConnectionProperties": {"CONNECTION_URL": "mongodb://localhost:27017/db"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=mongodb_connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        self.assertIsInstance(wrapper, MongoDBConnectionWrapper)

    def test_factory_method_routes_to_snowflake_wrapper(self):
        """Test that factory method routes Snowflake connections to SnowflakeConnectionWrapper."""
        snowflake_connection = {
            "Name": "snowflake-connection",
            "ConnectionType": "snowflake",
            "ConnectionProperties": {"sfUrl": "https://myaccount.snowflakecomputing.com"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=snowflake_connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        self.assertIsInstance(wrapper, SnowflakeConnectionWrapper)

    def test_factory_method_routes_to_mongodb_wrapper_for_documentdb(self):
        """Test that factory method routes DocumentDB connections to MongoDBConnectionWrapper."""
        documentdb_connection = {
            "Name": "documentdb-connection",
            "ConnectionType": "documentdb",
            "ConnectionProperties": {"CONNECTION_URL": "mongodb://docdb-cluster:27017/db"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=documentdb_connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        self.assertIsInstance(wrapper, MongoDBConnectionWrapper)

    def test_factory_method_routes_to_native_wrapper_for_other_types(self):
        """Test that factory method routes other connection types to NativeConnectionWrapper."""
        other_connection = {
            "Name": "other-connection",
            "ConnectionType": "bigquery",
            "ConnectionProperties": {"project": "my-project"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=other_connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        self.assertIsInstance(wrapper, NativeConnectionWrapper)

    def test_factory_method_routes_to_redshift_wrapper_when_connection_type_is_redshift(self):
        """Test that factory method routes to RedshiftJDBCConnectionWrapper when connection type is 'redshift'."""
        redshift_connection = {
            "ConnectionType": "redshift",
            "ConnectionProperties": {"JDBC_CONNECTION_URL": "jdbc:redshift://cluster:5439/db"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=redshift_connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        self.assertIsInstance(wrapper, RedshiftJDBCConnectionWrapper)

    def test_factory_method_routes_to_redshift_wrapper_when_jdbc_vendor_is_redshift(self):
        """Test that factory method routes to RedshiftJDBCConnectionWrapper when connection type is 'jdbc' and vendor is 'redshift'."""
        jdbc_redshift_connection = {
            "ConnectionType": "jdbc",
            "ConnectionProperties": {"JDBC_CONNECTION_URL": "jdbc:redshift://cluster:5439/db"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=jdbc_redshift_connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        self.assertIsInstance(wrapper, RedshiftJDBCConnectionWrapper)

    def test_factory_method_routes_to_jdbc_wrapper_when_jdbc_vendor_is_not_redshift(self):
        """Test that factory method routes to JDBCConnectionWrapper when connection type is 'jdbc' and vendor is not 'redshift'."""
        jdbc_mysql_connection = {
            "ConnectionType": "jdbc",
            "ConnectionProperties": {"JDBC_CONNECTION_URL": "jdbc:mysql://host:3306/db"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=jdbc_mysql_connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        self.assertIsInstance(wrapper, JDBCConnectionWrapper)

    def test_is_redshift_jdbc_connection_returns_false_when_no_jdbc_url(self):
        """Test _is_redshift_jdbc_connection returns False when no JDBC_CONNECTION_URL is present."""
        connection_no_url: Dict[str, Any] = {"ConnectionProperties": {}}
        inputs = GlueConnectionWrapperInputs(
            connection=connection_no_url,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        result = GlueConnectionWrapper._is_redshift_jdbc_connection(inputs)
        self.assertFalse(result)


class TestGlueConnectionWrapperJDBCConf(unittest.TestCase):
    """Test cases for get_jdbc_conf method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_kms_client = Mock()
        self.mock_secrets_client = Mock()

    @patch(
        "sagemaker_studio.connections.glue_connection_lib.connections.wrapper.glue_connection_wrapper.decrypt_encrypted_password"
    )
    def test_get_jdbc_conf_with_username_password(self, mock_decrypt):
        """Test get_jdbc_conf with username and password."""
        connection = {
            "Name": "test-connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:postgresql://localhost:5432/testdb",
                "USERNAME": "testuser",
                "PASSWORD": "testpass",
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        jdbc_conf = wrapper.get_jdbc_conf()

        self.assertIsInstance(jdbc_conf, JDBCConf)
        self.assertEqual(jdbc_conf.user, "testuser")
        self.assertEqual(jdbc_conf.password, "testpass")
        self.assertEqual(jdbc_conf.vendor, "postgresql")
        self.assertEqual(jdbc_conf.url, "jdbc:postgresql://localhost:5432")

    @patch("sagemaker_studio.connections.glue_connection_lib.connections.wrapper.glue_connection_wrapper.get_secret_options")
    def test_get_jdbc_conf_with_secret_id(self, mock_get_secret):
        """Test get_jdbc_conf with secret ID."""
        mock_get_secret.return_value = {"username": "secretuser", "password": "secretpass"}

        connection = {
            "Name": "test-connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:mysql://localhost:3306/testdb",
                "SECRET_ID": "test-secret",
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        jdbc_conf = wrapper.get_jdbc_conf()

        self.assertEqual(jdbc_conf.user, "secretuser")
        self.assertEqual(jdbc_conf.password, "secretpass")
        self.assertEqual(jdbc_conf.vendor, "mysql")

    def test_get_jdbc_conf_mongodb_connection(self):
        """Test get_jdbc_conf with MongoDB connection."""
        connection = {
            "Name": "mongo-connection",
            "ConnectionType": "mongodb",
            "ConnectionProperties": {
                "CONNECTION_URL": "mongodb://localhost:27017/testdb",
                "USERNAME": "mongouser",
                "PASSWORD": "mongopass",
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        jdbc_conf = wrapper.get_jdbc_conf()

        self.assertEqual(jdbc_conf.vendor, "mongodb")
        self.assertEqual(jdbc_conf.url, "jdbc:mongodb://localhost:27017")

    def test_get_jdbc_conf_non_jdbc_connection_raises_exception(self):
        """Test get_jdbc_conf raises exception for non-JDBC connection types."""
        connection = {"Name": "s3-connection", "ConnectionType": "s3", "ConnectionProperties": {}}

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)

        with self.assertRaises(Exception) as context:
            wrapper.get_jdbc_conf()

        self.assertIn("Connection type is not JDBC", str(context.exception))

    @patch(
        "sagemaker_studio.connections.glue_connection_lib.connections.wrapper.glue_connection_wrapper.decrypt_encrypted_password"
    )
    def test_get_jdbc_conf_encrypted_password_decryption_failure(self, mock_decrypt):
        """Test get_jdbc_conf when encrypted password decryption fails and exception is re-raised."""
        original_exception = Exception("Decryption failed")
        mock_decrypt.side_effect = original_exception

        connection = {
            "Name": "test-connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:mysql://localhost:3306/testdb",
                "USERNAME": "testuser",
                "ENCRYPTED_PASSWORD": "encrypted_value",
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)

        with self.assertRaises(Exception) as context:
            wrapper.get_jdbc_conf()

        # Verify the original exception is re-raised (tests the outer exception handler)
        self.assertIs(context.exception, original_exception)

    def test_get_jdbc_conf_missing_password_raises_exception(self):
        """Test get_jdbc_conf raises exception when both encrypted and plain passwords are missing."""
        connection = {
            "Name": "test-connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:mysql://localhost:3306/testdb",
                "USERNAME": "testuser",
                # No PASSWORD or ENCRYPTED_PASSWORD
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)

        with self.assertRaises(Exception) as context:
            wrapper.get_jdbc_conf()

        self.assertEqual(
            str(context.exception),
            "Encrypted Catalog password is empty and couldn't get plain text password from the connection properties map",
        )

    @patch("sagemaker_studio.connections.glue_connection_lib.connections.wrapper.glue_connection_wrapper.get_secret_options")
    def test_get_jdbc_conf_secret_missing_credentials(self, mock_get_secret):
        """Test get_jdbc_conf raises exception when secret doesn't contain required credentials."""
        mock_get_secret.return_value = {"other_field": "value"}  # Missing username/password

        connection = {
            "Name": "test-connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:mysql://localhost:3306/testdb",
                "SECRET_ID": "test-secret",
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)

        with self.assertRaises(ValueError) as context:
            wrapper.get_jdbc_conf()

        self.assertIn("Username and password for the secretId are required", str(context.exception))

    def test_get_jdbc_conf_with_ssl_certificate_options(self):
        """Test get_jdbc_conf with SSL and certificate options to cover lines 158-162."""
        connection = {
            "Name": "test-connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:postgresql://localhost:5432/testdb",
                "USERNAME": "testuser",
                "PASSWORD": "testpass",
                # SSL and certificate options
                "JDBC_ENFORCE_SSL": "true",
                "CUSTOM_JDBC_CERT": "/path/to/cert.pem",
                "SKIP_CUSTOM_JDBC_CERT_VALIDATION": "true",
                "CUSTOM_JDBC_CERT_STRING": "-----BEGIN CERTIFICATE-----\nMIIC...",
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        jdbc_conf = wrapper.get_jdbc_conf()

        # Verify SSL and certificate options are properly extracted
        self.assertEqual(jdbc_conf.enforce_ssl, "true")
        self.assertEqual(jdbc_conf.custom_jdbc_cert, "/path/to/cert.pem")
        self.assertEqual(jdbc_conf.skip_custom_jdbc_cert_validation, "true")
        self.assertEqual(jdbc_conf.custom_jdbc_cert_string, "-----BEGIN CERTIFICATE-----\nMIIC...")

    def test_get_jdbc_conf_missing_username_and_secret_id(self):
        """Test get_jdbc_conf raises exception when both username and secretId are missing."""
        connection = {
            "Name": "test-connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:mysql://localhost:3306/testdb"
                # No USERNAME or SECRET_ID
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)

        with self.assertRaises(ValueError) as context:
            wrapper.get_jdbc_conf()

        self.assertIn(
            "Must specify username or secretId for JDBC connection (unless using IAM authentication)",
            str(context.exception),
        )

    def test_get_jdbc_conf_native_jdbc_connection_saphana(self):
        """Test get_jdbc_conf with native JDBC connection (Saphana) to cover the else branch."""
        connection = {
            "Name": "saphana-connection",
            "ConnectionType": "saphana",
            "ConnectionProperties": {
                "url": "jdbc:sap://localhost:30015",  # lowercase to match SparkOptionsKey.URL
                "USERNAME": "sapuser",
                "PASSWORD": "sappass",
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        jdbc_conf = wrapper.get_jdbc_conf()

        # Verify the else branch logic: URL comes from SparkOptionsKey.URL
        self.assertEqual(jdbc_conf.url, "jdbc:sap://localhost:30015")
        self.assertEqual(jdbc_conf.full_url, "jdbc:sap://localhost:30015")
        self.assertEqual(jdbc_conf.vendor, "saphana")  # vendor = connection_type_lower
        self.assertEqual(jdbc_conf.user, "sapuser")
        self.assertEqual(jdbc_conf.password, "sappass")

    def test_get_jdbc_conf_native_jdbc_connection_teradata(self):
        """Test get_jdbc_conf with native JDBC connection (Teradata) to cover the else branch."""
        connection = {
            "Name": "teradata-connection",
            "ConnectionType": "teradata",
            "ConnectionProperties": {
                "url": "jdbc:teradata://localhost/DATABASE=test",  # lowercase to match SparkOptionsKey.URL
                "USERNAME": "terauser",
                "PASSWORD": "terapass",
            },
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        jdbc_conf = wrapper.get_jdbc_conf()

        # Verify the else branch logic: URL comes from SparkOptionsKey.URL
        self.assertEqual(jdbc_conf.url, "jdbc:teradata://localhost/DATABASE=test")
        self.assertEqual(jdbc_conf.full_url, "jdbc:teradata://localhost/DATABASE=test")
        self.assertEqual(jdbc_conf.vendor, "teradata")  # vendor = connection_type_lower
        self.assertEqual(jdbc_conf.user, "terauser")
        self.assertEqual(jdbc_conf.password, "terapass")

    def test_get_jdbc_conf_iam_authentication_without_username_or_secret_id(self):
        """Test get_jdbc_conf with IAM authentication without username or secretId."""
        connection = {
            "Name": "test-iam-jdbc-conn",
            "ConnectionType": "REDSHIFT",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:redshift://test-cluster:5439/test"
            },
            "AuthenticationConfiguration": {"AuthenticationType": "IAM"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)
        jdbc_conf = wrapper.get_jdbc_conf()

        # Verify that null credentials are used for IAM authentication
        self.assertIsNone(jdbc_conf.user)
        self.assertIsNone(jdbc_conf.password)
        self.assertEqual(jdbc_conf.vendor, "redshift")

    def test_get_jdbc_conf_non_iam_authentication_without_username_or_secret_id_throws_exception(
        self,
    ):
        """Test that non-IAM authentication without username or secretId throws exception."""
        connection = {
            "Name": "test-password-conn",
            "ConnectionType": "REDSHIFT",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:redshift://test-cluster:5439/test"
            },
            "AuthenticationConfiguration": {"AuthenticationType": "PASSWORD"},
        }

        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            kms_client=self.mock_kms_client,
            secrets_manager_client=self.mock_secrets_client,
            additional_options={},
        )

        wrapper = GlueConnectionWrapper.create(inputs)

        with self.assertRaises(ValueError) as context:
            wrapper.get_jdbc_conf()

        self.assertIn(
            "Must specify username or secretId for JDBC connection (unless using IAM authentication)",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
