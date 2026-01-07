"""
Tests for NativeConnectionWrapper.
"""

import json
import unittest
from unittest.mock import Mock

from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.glue_connection_wrapper_inputs import (
    GlueConnectionWrapperInputs,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.local.native_wrapper import (
    NativeConnectionWrapper,
)


class TestNativeConnectionWrapper(unittest.TestCase):
    """Test cases for NativeConnectionWrapper."""

    def test_get_secret_options_from_secret_manager_success(self):
        """Test successful secret retrieval from Secrets Manager."""
        mock_connection = {
            "Name": "test-connection",
            "ConnectionType": "NATIVE",
            "ConnectionProperties": {},
        }

        mock_secrets_manager_client = Mock()
        secret_data = {"username": "testuser", "password": "testpass"}
        mock_secrets_manager_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=mock_secrets_manager_client,
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)
        result = wrapper._get_secret_options_from_secret_manager("test-secret-id")

        self.assertEqual(result, secret_data)
        mock_secrets_manager_client.get_secret_value.assert_called_once_with(
            SecretId="test-secret-id"
        )

    def test_get_driver_options_teradata(self):
        """Test driver options for Teradata connection."""
        result = NativeConnectionWrapper.get_driver_options("teradata")
        expected = {"driver": "com.teradata.jdbc.TeraDriver"}
        self.assertEqual(result, expected)

    def test_get_driver_options_teradata_case_insensitive(self):
        """Test driver options for Teradata with different case."""
        result = NativeConnectionWrapper.get_driver_options("TERADATA")
        expected = {"driver": "com.teradata.jdbc.TeraDriver"}
        self.assertEqual(result, expected)

    def test_get_driver_options_saphana(self):
        """Test driver options for SAP HANA connection."""
        result = NativeConnectionWrapper.get_driver_options("saphana")
        expected = {"driver": "com.sap.db.jdbc.Driver"}
        self.assertEqual(result, expected)

    def test_get_driver_options_unknown_type(self):
        """Test driver options for unknown connection type."""
        result = NativeConnectionWrapper.get_driver_options("unknown")
        self.assertEqual(result, {})

    def test_get_resolved_connection_legacy_with_secret(self):
        """Test get_resolved_connection for legacy connection with secret."""
        mock_connection = {
            "Name": "test-connection",
            "ConnectionType": "BIGQUERY",
            "ConnectionProperties": {
                "SparkProperties": '{"url": "test-url", "secretId": "test-secret"}'
            },
        }

        mock_secrets_manager_client = Mock()
        secret_data = {"username": "testuser", "password": "testpass"}
        mock_secrets_manager_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=mock_secrets_manager_client,
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        expected_spark_properties = {
            "url": "test-url",
            "username": "testuser",
            "password": "testpass",
            "credentials": "eyJ1c2VybmFtZSI6ICJ0ZXN0dXNlciIsICJwYXNzd29yZCI6ICJ0ZXN0cGFzcyJ9",
        }

        self.assertEqual(result["Name"], "test-connection")
        self.assertEqual(result["ConnectionType"], "BIGQUERY")
        self.assertEqual(result["SparkProperties"], expected_spark_properties)

    def test_get_resolved_connection_v2_with_secret(self):
        """Test get_resolved_connection for V2 connection with secret."""
        mock_connection = {
            "Name": "test-connection",
            "ConnectionType": "TERADATA",
            "ConnectionProperties": {"url": "test-url", "secretId": "test-secret"},
            "AuthenticationConfiguration": {"AuthenticationType": "OAUTH2"},
        }

        mock_secrets_manager_client = Mock()
        secret_data = {"username": "testuser", "password": "testpass"}
        mock_secrets_manager_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=mock_secrets_manager_client,
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        # Check that the result contains expected properties
        spark_properties = result["SparkProperties"]
        self.assertEqual(spark_properties["url"], "test-url")
        self.assertEqual(
            spark_properties["user"], "testuser"
        )  # Note: secret helper maps username to user
        self.assertEqual(spark_properties["password"], "testpass")
        self.assertEqual(spark_properties["driver"], "com.teradata.jdbc.TeraDriver")
        self.assertEqual(spark_properties["authenticationType"], "OAUTH2")
        self.assertEqual(spark_properties["connectionName"], "test-connection")

        self.assertEqual(result["Name"], "test-connection")
        self.assertEqual(result["ConnectionType"], "TERADATA")

    def test_get_resolved_connection_snowflake_oauth2(self):
        """Test get_resolved_connection for Snowflake OAuth2 connection."""
        mock_connection = {
            "Name": "snowflake-oauth2-connection",
            "ConnectionType": "SNOWFLAKE",
            "ConnectionProperties": {"url": "snowflake-url", "secretId": "oauth-secret"},
            "AuthenticationConfiguration": {"AuthenticationType": "OAUTH2"},
        }

        mock_secrets_manager_client = Mock()
        secret_data = {"ACCESS_TOKEN": "oauth_token_123", "REFRESH_TOKEN": "refresh_123"}
        mock_secrets_manager_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=mock_secrets_manager_client,
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        # Check that OAuth2 token is mapped correctly for Snowflake
        spark_properties = result["SparkProperties"]
        self.assertEqual(spark_properties["sftoken"], "oauth_token_123")
        self.assertEqual(spark_properties["authenticationType"], "OAUTH2")

    def test_get_resolved_connection_snowflake_basic_auth(self):
        """Test get_resolved_connection for Snowflake basic auth connection."""
        mock_connection = {
            "Name": "snowflake-basic-connection",
            "ConnectionType": "SNOWFLAKE",
            "ConnectionProperties": {"url": "snowflake-url", "secretId": "basic-secret"},
            "AuthenticationConfiguration": {"AuthenticationType": "BASIC"},
        }

        mock_secrets_manager_client = Mock()
        secret_data = {"USERNAME": "snowflake_user", "PASSWORD": "snowflake_pass"}
        mock_secrets_manager_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=mock_secrets_manager_client,
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        # Check that basic auth uses standard username/password mapping
        spark_properties = result["SparkProperties"]
        self.assertEqual(spark_properties["sfUser"], "snowflake_user")
        self.assertEqual(spark_properties["sfPassword"], "snowflake_pass")
        self.assertEqual(spark_properties["authenticationType"], "BASIC")

    def test_get_resolved_connection_no_secret(self):
        """Test get_resolved_connection without secret."""
        mock_connection = {
            "Name": "test-connection",
            "ConnectionType": "SAPHANA",
            "ConnectionProperties": {"url": "test-url", "username": "direct-user"},
            "AuthenticationConfiguration": {"AuthenticationType": "OAUTH2"},
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        # Check that the result contains expected properties
        spark_properties = result["SparkProperties"]
        self.assertEqual(spark_properties["url"], "test-url")
        self.assertEqual(spark_properties["username"], "direct-user")
        self.assertEqual(spark_properties["driver"], "com.sap.db.jdbc.Driver")
        self.assertEqual(spark_properties["authenticationType"], "OAUTH2")
        self.assertEqual(spark_properties["connectionName"], "test-connection")

    def test_get_resolved_connection_legacy_no_spark_properties(self):
        """Test get_resolved_connection for legacy connection without SparkProperties."""
        mock_connection = {
            "Name": "test-connection",
            "ConnectionType": "SNOWFLAKE",
            "ConnectionProperties": {"url": "test-url"},
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        # Should have empty SparkProperties since no SparkProperties key exists
        self.assertEqual(result["SparkProperties"], {})
        self.assertEqual(result["Name"], "test-connection")
        self.assertEqual(result["ConnectionType"], "SNOWFLAKE")

    def test_get_resolved_connection_legacy_jdbc_type(self):
        """Test get_resolved_connection for legacy JDBC connection type."""
        mock_connection = {
            "Name": "test-connection",
            "ConnectionType": "MYSQL",  # Use a valid JDBC type
            "ConnectionProperties": {
                "JDBCProperties": '{"url": "jdbc:mysql://host:3306/db", "username": "user"}'
            },
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        expected_spark_properties = {"url": "jdbc:mysql://host:3306/db", "username": "user"}

        self.assertEqual(result["SparkProperties"], expected_spark_properties)
        self.assertEqual(result["Name"], "test-connection")
        self.assertEqual(result["ConnectionType"], "MYSQL")

    def test_get_resolved_connection_invalid_connector_type(self):
        """Test get_resolved_connection with invalid connector type."""
        mock_connection = {
            "Name": "test-connection",
            "ConnectionType": "INVALID",
            "ConnectionProperties": {},
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)

        with self.assertRaises(ValueError) as context:
            wrapper.get_resolved_connection()

        self.assertIn("Invalid Connector Type: invalid", str(context.exception))

    def test_get_secret_options_from_secret_manager_aws_error(self):
        """Test AWS Secrets Manager error handling."""
        mock_connection = {"Name": "test-connection", "ConnectionType": "NATIVE"}
        mock_secrets_manager_client = Mock()
        mock_secrets_manager_client.get_secret_value.side_effect = Exception("AWS error")

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=mock_secrets_manager_client,
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)

        with self.assertRaises(ValueError) as context:
            wrapper._get_secret_options_from_secret_manager("test-secret-id")

        self.assertIn(
            "Failed to retrieve or parse secret 'test-secret-id': AWS error", str(context.exception)
        )

    def test_get_secret_options_from_secret_manager_json_error(self):
        """Test JSON parsing error handling."""
        mock_connection = {"Name": "test-connection", "ConnectionType": "NATIVE"}
        mock_secrets_manager_client = Mock()
        mock_secrets_manager_client.get_secret_value.return_value = {"SecretString": "invalid json"}

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=mock_secrets_manager_client,
        )

        wrapper = NativeConnectionWrapper(wrapper_inputs)

        with self.assertRaises(ValueError) as context:
            wrapper._get_secret_options_from_secret_manager("test-secret-id")

        self.assertIn("Failed to retrieve or parse secret 'test-secret-id'", str(context.exception))


if __name__ == "__main__":
    unittest.main()
