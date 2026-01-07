"""Tests for utils module."""

import json
import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from sagemaker_studio.connections.glue_connection_lib.connections.utils.utils import (
    connection_properties_exist,
    decrypt_encrypted_password,
    get_connection_properties,
    get_secret_options,
    get_vendor_from_url,
    is_jdbc_connection_needed,
    is_legacy_connection,
    resolve_connection_v2_options,
)


class TestGetSecretOptions(unittest.TestCase):
    """Test cases for get_secret_options function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_secrets_client = Mock()

    def test_get_secret_options_no_secret_id(self):
        """Test get_secret_options returns empty dict when no secretId provided."""
        option_map: dict[str, str] = {}
        result = get_secret_options(option_map, self.mock_secrets_client)

        self.assertEqual(result, {})
        self.mock_secrets_client.get_secret_value.assert_not_called()

    def test_get_secret_options_empty_secret_id(self):
        """Test get_secret_options raises ValueError for empty secretId."""
        option_map = {"secretId": ""}

        with self.assertRaises(ValueError) as context:
            get_secret_options(option_map, self.mock_secrets_client)

        self.assertEqual(str(context.exception), "If secretId is provided, it cannot be empty.")
        self.mock_secrets_client.get_secret_value.assert_not_called()

    def test_get_secret_options_success_with_json_object(self):
        """Test get_secret_options successfully returns parsed JSON object."""
        option_map = {"secretId": "my-secret"}
        secret_data = {"username": "admin", "password": "secret123"}

        self.mock_secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        result = get_secret_options(option_map, self.mock_secrets_client)

        self.assertEqual(result, secret_data)
        self.mock_secrets_client.get_secret_value.assert_called_once_with(SecretId="my-secret")

    def test_get_secret_options_success_with_mixed_types(self):
        """Test get_secret_options handles JSON with mixed value types."""
        option_map = {"secretId": "my-secret"}
        secret_data = {"host": "db.example.com", "port": 5432, "ssl": True}

        self.mock_secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        result = get_secret_options(option_map, self.mock_secrets_client)

        self.assertEqual(result, secret_data)
        self.assertEqual(result["port"], 5432)  # int
        self.assertEqual(result["ssl"], True)  # bool

    def test_get_secret_options_no_secret_string(self):
        """Test get_secret_options returns empty dict when SecretString is missing."""
        option_map = {"secretId": "my-secret"}

        self.mock_secrets_client.get_secret_value.return_value = {
            "SecretBinary": b"binary-data"  # No SecretString
        }

        result = get_secret_options(option_map, self.mock_secrets_client)

        self.assertEqual(result, {})
        self.mock_secrets_client.get_secret_value.assert_called_once_with(SecretId="my-secret")

    def test_get_secret_options_aws_error(self):
        """Test AWS Secrets Manager error handling."""
        option_map = {"secretId": "my-secret"}
        self.mock_secrets_client.get_secret_value.side_effect = Exception("AWS error")

        with self.assertRaises(ValueError) as context:
            get_secret_options(option_map, self.mock_secrets_client)

        self.assertIn(
            "Failed to retrieve or parse secret 'my-secret': AWS error", str(context.exception)
        )

    def test_get_secret_options_json_error(self):
        """Test JSON parsing error handling."""
        option_map = {"secretId": "my-secret"}
        self.mock_secrets_client.get_secret_value.return_value = {"SecretString": "invalid json"}

        with self.assertRaises(ValueError) as context:
            get_secret_options(option_map, self.mock_secrets_client)

        self.assertIn("Failed to retrieve or parse secret 'my-secret'", str(context.exception))


class TestDecryptEncryptedPassword(unittest.TestCase):
    """Test cases for decrypt_encrypted_password function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_kms_client = Mock()

    def test_decrypt_encrypted_password_empty_field(self):
        """Test decrypt_encrypted_password raises ValueError for empty field."""
        with self.assertRaises(ValueError) as context:
            decrypt_encrypted_password("", self.mock_kms_client)

        self.assertEqual(
            str(context.exception), "encrypted password field provided is null or empty"
        )
        self.mock_kms_client.decrypt.assert_not_called()

    @patch("sagemaker_studio.connections.glue_connection_lib.connections.utils.utils.base64.b64decode")
    def test_decrypt_encrypted_password_success(self, mock_b64decode):
        """Test decrypt_encrypted_password successfully decrypts password."""
        encrypted_field = "base64encodeddata"
        decoded_bytes = b"encrypted_bytes"
        decrypted_bytes = b"my-password"

        mock_b64decode.return_value = decoded_bytes
        self.mock_kms_client.decrypt.return_value = {"Plaintext": decrypted_bytes}

        result = decrypt_encrypted_password(encrypted_field, self.mock_kms_client)

        self.assertEqual(result, "my-password")
        mock_b64decode.assert_called_once_with(encrypted_field)
        self.mock_kms_client.decrypt.assert_called_once_with(CiphertextBlob=decoded_bytes)

    @patch("sagemaker_studio.connections.glue_connection_lib.connections.utils.utils.boto3.client")
    @patch("sagemaker_studio.connections.glue_connection_lib.connections.utils.utils.base64.b64decode")
    def test_decrypt_encrypted_password_fallback_to_us_east_1(
        self, mock_b64decode, mock_boto3_client
    ):
        """Test decrypt_encrypted_password falls back to us-east-1 on ClientError."""
        encrypted_field = "base64encodeddata"
        decoded_bytes = b"encrypted_bytes"
        decrypted_bytes = b"my-password"
        mock_us_east_kms = Mock()

        mock_b64decode.return_value = decoded_bytes
        mock_boto3_client.return_value = mock_us_east_kms

        # First call fails, second succeeds
        self.mock_kms_client.decrypt.side_effect = ClientError(
            {"Error": {"Code": "InvalidCiphertextException"}}, "decrypt"
        )
        mock_us_east_kms.decrypt.return_value = {"Plaintext": decrypted_bytes}

        result = decrypt_encrypted_password(encrypted_field, self.mock_kms_client)

        self.assertEqual(result, "my-password")
        mock_boto3_client.assert_called_once_with("kms", region_name="us-east-1")
        self.mock_kms_client.decrypt.assert_called_once_with(CiphertextBlob=decoded_bytes)
        mock_us_east_kms.decrypt.assert_called_once_with(CiphertextBlob=decoded_bytes)

    @patch("sagemaker_studio.connections.glue_connection_lib.connections.utils.utils.boto3.client")
    @patch("sagemaker_studio.connections.glue_connection_lib.connections.utils.utils.base64.b64decode")
    def test_decrypt_encrypted_password_both_attempts_fail(self, mock_b64decode, mock_boto3_client):
        """Test decrypt_encrypted_password propagates error when both attempts fail."""
        encrypted_field = "base64encodeddata"
        decoded_bytes = b"encrypted_bytes"
        mock_us_east_kms = Mock()

        mock_b64decode.return_value = decoded_bytes
        mock_boto3_client.return_value = mock_us_east_kms

        # Both calls fail
        first_error = ClientError({"Error": {"Code": "InvalidCiphertextException"}}, "decrypt")
        second_error = ClientError({"Error": {"Code": "DisabledException"}}, "decrypt")

        self.mock_kms_client.decrypt.side_effect = first_error
        mock_us_east_kms.decrypt.side_effect = second_error

        with self.assertRaises(ClientError) as context:
            decrypt_encrypted_password(encrypted_field, self.mock_kms_client)

        # Should raise the second error (from us-east-1 attempt)
        self.assertEqual(context.exception, second_error)


class TestConnectionPropertiesExist(unittest.TestCase):
    """Test cases for connection_properties_exist function."""

    def test_connection_properties_exist_with_connection_properties(self):
        """Test returns True when ConnectionProperties exist."""
        connection = {"ConnectionProperties": {"url": "jdbc:mysql://host:3306/db"}}
        self.assertTrue(connection_properties_exist(connection))

    def test_connection_properties_exist_with_spark_properties(self):
        """Test returns True when SparkProperties exist."""
        connection = {"SparkProperties": {"driver": "com.mysql.cj.jdbc.Driver"}}
        self.assertTrue(connection_properties_exist(connection))

    def test_connection_properties_exist_with_both_properties(self):
        """Test returns True when both properties exist."""
        connection = {
            "ConnectionProperties": {"url": "jdbc:mysql://host:3306/db"},
            "SparkProperties": {"driver": "com.mysql.cj.jdbc.Driver"},
        }
        self.assertTrue(connection_properties_exist(connection))

    def test_connection_properties_exist_empty_connection(self):
        """Test returns False for empty connection."""
        connection: dict[str, str] = {}
        self.assertFalse(connection_properties_exist(connection))

    def test_connection_properties_exist_none_connection(self):
        """Test returns False for None connection."""
        self.assertFalse(connection_properties_exist(None))

    def test_connection_properties_exist_no_properties(self):
        """Test returns False when no relevant properties exist."""
        connection = {"Name": "test-connection", "ConnectionType": "JDBC"}
        self.assertFalse(connection_properties_exist(connection))


class TestIsJdbcConnectionNeeded(unittest.TestCase):
    """Test cases for is_jdbc_connection_needed function."""

    def test_is_jdbc_connection_needed_jdbc_type(self):
        """Test returns True for JDBC connection type."""
        self.assertTrue(is_jdbc_connection_needed("JDBC"))
        self.assertTrue(is_jdbc_connection_needed("jdbc"))

    def test_is_jdbc_connection_needed_redshift_type(self):
        """Test returns True for Redshift connection type."""
        self.assertTrue(is_jdbc_connection_needed("REDSHIFT"))
        self.assertTrue(is_jdbc_connection_needed("redshift"))

    def test_is_jdbc_connection_needed_mysql_type(self):
        """Test returns True for MySQL connection type."""
        self.assertTrue(is_jdbc_connection_needed("MYSQL"))
        self.assertTrue(is_jdbc_connection_needed("mysql"))

    def test_is_jdbc_connection_needed_mongodb_type(self):
        """Test returns True for MongoDB connection type."""
        self.assertTrue(is_jdbc_connection_needed("MONGODB"))
        self.assertTrue(is_jdbc_connection_needed("mongodb"))

    def test_is_jdbc_connection_needed_documentdb_type(self):
        """Test returns True for DocumentDB connection type."""
        self.assertTrue(is_jdbc_connection_needed("DOCUMENTDB"))
        self.assertTrue(is_jdbc_connection_needed("documentdb"))

    def test_is_jdbc_connection_needed_s3_type(self):
        """Test returns False for S3 connection type."""
        self.assertFalse(is_jdbc_connection_needed("S3"))
        self.assertFalse(is_jdbc_connection_needed("s3"))

    def test_is_jdbc_connection_needed_unknown_type(self):
        """Test returns False for unknown connection type."""
        self.assertFalse(is_jdbc_connection_needed("UNKNOWN"))
        self.assertFalse(is_jdbc_connection_needed("custom"))

    def test_is_jdbc_connection_needed_connector_type_jdbc_values(self):
        """Test returns True for connection types in CONNECTOR_TYPE['jdbc']."""
        # Test all CONNECTOR_TYPE["jdbc"] values
        jdbc_types = ["sqlserver", "postgresql", "oracle", "redshift", "mysql", "saphana"]
        for jdbc_type in jdbc_types:
            with self.subTest(jdbc_type=jdbc_type):
                self.assertTrue(is_jdbc_connection_needed(jdbc_type))
                self.assertTrue(is_jdbc_connection_needed(jdbc_type.upper()))


class TestIsLegacyConnection(unittest.TestCase):
    """Test cases for is_legacy_connection function."""

    def test_is_legacy_connection_no_auth_config(self):
        """Test returns True when AuthenticationConfiguration is missing."""
        connection = {"Name": "test-connection", "ConnectionType": "JDBC"}
        self.assertTrue(is_legacy_connection(connection))

    def test_is_legacy_connection_auth_config_none(self):
        """Test returns True when AuthenticationConfiguration is None."""
        connection = {"AuthenticationConfiguration": None}
        self.assertTrue(is_legacy_connection(connection))

    def test_is_legacy_connection_has_auth_config(self):
        """Test returns False when AuthenticationConfiguration exists."""
        connection = {
            "AuthenticationConfiguration": {
                "AuthenticationType": "BASIC",
                "SecretArn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            }
        }
        self.assertFalse(is_legacy_connection(connection))


class TestResolveConnectionV2Options(unittest.TestCase):
    """Test cases for resolve_connection_v2_options function."""

    def test_resolve_connection_v2_options_spark_properties(self):
        """Test adds spark properties to map."""
        connection = {"SparkProperties": {"driver": "com.mysql.cj.jdbc.Driver"}}
        props_map: dict[str, str] = {}

        resolve_connection_v2_options(connection, props_map)

        self.assertEqual(props_map["driver"], "com.mysql.cj.jdbc.Driver")

    def test_resolve_connection_v2_options_auth_config(self):
        """Test adds auth config properties."""
        connection = {
            "Name": "test-connection",
            "AuthenticationConfiguration": {
                "SecretArn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
                "AuthenticationType": "BASIC",
            },
        }
        props_map: dict[str, str] = {}

        resolve_connection_v2_options(connection, props_map)

        self.assertEqual(
            props_map["secretId"], "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"
        )
        self.assertEqual(props_map["authenticationType"], "BASIC")
        self.assertEqual(props_map["connectionName"], "test-connection")

    def test_resolve_connection_v2_options_jdbc_type(self):
        """Test adds JDBC properties for JDBC connection types."""
        connection = {
            "ConnectionType": "MYSQL",
            "AuthenticationConfiguration": {
                "SecretArn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"
            },
        }
        props_map: dict[str, str] = {}

        resolve_connection_v2_options(connection, props_map)

        self.assertEqual(props_map["JDBC_ENFORCE_SSL"], "false")
        self.assertEqual(
            props_map["SECRET_ID"], "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"
        )

    def test_resolve_connection_v2_options_oauth2(self):
        """Test adds OAuth2 client ID."""
        connection = {
            "AuthenticationConfiguration": {
                "AuthenticationType": "OAUTH2",
                "OAuth2Properties": {
                    "OAuth2ClientApplication": {
                        "UserManagedClientApplicationClientId": "test-client-id"
                    }
                },
            }
        }
        props_map: dict[str, str] = {}

        resolve_connection_v2_options(connection, props_map)

        self.assertEqual(props_map["clientId"], "test-client-id")


class TestGetConnectionProperties(unittest.TestCase):
    """Test cases for get_connection_properties function."""

    def test_get_connection_properties_no_properties(self):
        """Test returns empty dict when no properties exist."""
        connection = {"Name": "test-connection"}

        result = get_connection_properties(connection)

        self.assertEqual(result, {})

    def test_get_connection_properties_legacy_connection(self):
        """Test returns only connection properties for legacy connections."""
        connection = {
            "ConnectionProperties": {"url": "jdbc:mysql://host:3306/db", "user": "testuser"}
        }

        result = get_connection_properties(connection)

        self.assertEqual(result, {"url": "jdbc:mysql://host:3306/db", "user": "testuser"})

    def test_get_connection_properties_v2_connection(self):
        """Test resolves V2 options for modern connections."""
        connection = {
            "ConnectionProperties": {"url": "jdbc:mysql://host:3306/db"},
            "AuthenticationConfiguration": {
                "SecretArn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
                "AuthenticationType": "BASIC",
            },
            "SparkProperties": {"driver": "com.mysql.cj.jdbc.Driver"},
        }

        result = get_connection_properties(connection)

        # Should have original properties plus resolved V2 options
        self.assertEqual(result["url"], "jdbc:mysql://host:3306/db")
        self.assertEqual(result["driver"], "com.mysql.cj.jdbc.Driver")
        self.assertEqual(
            result["secretId"], "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"
        )


class TestGetVendorFromUrl(unittest.TestCase):
    """Test cases for get_vendor_from_url function."""

    def test_get_vendor_from_url(self):
        """Test extracting vendor from URL."""
        url = "jdbc:mysql://localhost:3306/testdb"
        result_url, result_full_url, result_vendor = get_vendor_from_url(url)

        self.assertEqual(result_url, "jdbc:mysql://localhost:3306")
        self.assertEqual(result_full_url, url)
        self.assertEqual(result_vendor, "mysql")


if __name__ == "__main__":
    unittest.main()
