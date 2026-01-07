"""
Unit tests for secure_connection module.
"""

import unittest
from typing import Any, Dict

from sagemaker_studio.connections.glue_connection_lib.connections.utils.secure_connection import (
    _is_sensitive_key,
    sanitize_connection_for_logging,
)


class TestSecureConnection(unittest.TestCase):
    """Test cases for connection sanitization."""

    def test_sanitize_spark_properties(self):
        """Test sanitization of SparkProperties with sensitive fields."""
        connection = {
            "Name": "test-connection",
            "SparkProperties": {
                "user": "testuser",
                "password": "secret123",
                "url": "jdbc:postgresql://host:5432/db",
                "vendor": "postgresql",
            },
        }

        result = sanitize_connection_for_logging(connection)

        self.assertEqual(result["Name"], "test-connection")
        self.assertEqual(result["SparkProperties"]["user"], "***MASKED***")
        self.assertEqual(result["SparkProperties"]["password"], "***MASKED***")
        self.assertEqual(result["SparkProperties"]["url"], "jdbc:postgresql://host:5432/db")
        self.assertEqual(result["SparkProperties"]["vendor"], "postgresql")

    def test_sanitize_connection_properties(self):
        """Test sanitization of ConnectionProperties."""
        connection = {
            "ConnectionProperties": {
                "USERNAME": "admin",
                "PASSWORD": "secret",
                "JDBC_CONNECTION_URL": "jdbc:mysql://host:3306/db",
            }
        }

        result = sanitize_connection_for_logging(connection)

        self.assertEqual(result["ConnectionProperties"]["USERNAME"], "***MASKED***")
        self.assertEqual(result["ConnectionProperties"]["PASSWORD"], "***MASKED***")
        self.assertEqual(
            result["ConnectionProperties"]["JDBC_CONNECTION_URL"], "jdbc:mysql://host:3306/db"
        )

    def test_sanitize_nested_sensitive_object(self):
        """Test that entire sensitive objects are masked."""
        connection = {
            "credentials": {"username": "user", "password": "pass"},
            "config": {"timeout": 30},
        }

        result = sanitize_connection_for_logging(connection)

        self.assertEqual(result["credentials"], "***MASKED***")
        self.assertEqual(result["config"]["timeout"], 30)

    def test_is_sensitive_key_exact_matches(self):
        """Test _is_sensitive_key with exact matches."""
        self.assertTrue(_is_sensitive_key("password"))
        self.assertTrue(_is_sensitive_key("user"))
        self.assertTrue(_is_sensitive_key("token"))
        self.assertTrue(_is_sensitive_key("secret"))
        self.assertTrue(_is_sensitive_key("credential"))
        self.assertTrue(_is_sensitive_key("key"))
        self.assertTrue(_is_sensitive_key("client"))
        self.assertTrue(_is_sensitive_key("auth"))
        self.assertTrue(_is_sensitive_key("principal"))
        self.assertTrue(_is_sensitive_key("role"))
        self.assertTrue(_is_sensitive_key("arn"))

    def test_is_sensitive_key_substring_matches(self):
        """Test _is_sensitive_key with substring matches."""
        self.assertTrue(_is_sensitive_key("db_password"))
        self.assertTrue(_is_sensitive_key("admin_user"))
        self.assertTrue(_is_sensitive_key("auth_token"))
        self.assertTrue(_is_sensitive_key("api_secret"))
        self.assertTrue(_is_sensitive_key("oauth_credential"))
        self.assertTrue(_is_sensitive_key("access_key"))
        self.assertTrue(_is_sensitive_key("client_id"))
        self.assertTrue(_is_sensitive_key("basic_auth"))
        self.assertTrue(_is_sensitive_key("kerberos_principal"))
        self.assertTrue(_is_sensitive_key("iam_role"))
        self.assertTrue(_is_sensitive_key("role_arn"))

    def test_is_sensitive_key_case_insensitive(self):
        """Test _is_sensitive_key is case insensitive."""
        self.assertTrue(_is_sensitive_key("PASSWORD"))
        self.assertTrue(_is_sensitive_key("User"))
        self.assertTrue(_is_sensitive_key("ACCESS_TOKEN"))
        self.assertTrue(_is_sensitive_key("Secret_Key"))
        self.assertTrue(_is_sensitive_key("CLIENT_ID"))

    def test_is_sensitive_key_non_sensitive(self):
        """Test _is_sensitive_key returns False for non-sensitive keys."""
        self.assertFalse(_is_sensitive_key("url"))
        self.assertFalse(_is_sensitive_key("vendor"))
        self.assertFalse(_is_sensitive_key("driver"))
        self.assertFalse(_is_sensitive_key("timeout"))
        self.assertFalse(_is_sensitive_key("port"))
        self.assertFalse(_is_sensitive_key("host"))

    def test_sanitize_snowflake_fields(self):
        """Test sanitization of Snowflake-specific fields."""
        connection = {
            "SparkProperties": {
                "sfUser": "snowflake_user",
                "sfPassword": "snowflake_pass",
                "sftoken": "oauth_token",
                "sfDatabase": "test_db",
                "url": "snowflake://account.snowflakecomputing.com",
            }
        }

        result = sanitize_connection_for_logging(connection)

        self.assertEqual(result["SparkProperties"]["sfUser"], "***MASKED***")
        self.assertEqual(result["SparkProperties"]["sfPassword"], "***MASKED***")
        self.assertEqual(result["SparkProperties"]["sftoken"], "***MASKED***")
        self.assertEqual(result["SparkProperties"]["sfDatabase"], "test_db")
        self.assertEqual(
            result["SparkProperties"]["url"], "snowflake://account.snowflakecomputing.com"
        )

    def test_sanitize_kafka_fields(self):
        """Test sanitization of Kafka-specific fields."""
        connection = {
            "ConnectionProperties": {
                "KAFKA_CLIENT_KEYSTORE_PASSWORD": "keystore_pass",
                "KAFKA_CLIENT_KEY_PASSWORD": "key_pass",
                "KAFKA_SASL_PLAIN_USERNAME": "kafka_user",
                "KAFKA_SASL_PLAIN_PASSWORD": "kafka_pass",
                "KAFKA_BOOTSTRAP_SERVERS": "broker1:9092,broker2:9092",
            }
        }

        result = sanitize_connection_for_logging(connection)

        self.assertEqual(
            result["ConnectionProperties"]["KAFKA_CLIENT_KEYSTORE_PASSWORD"], "***MASKED***"
        )
        self.assertEqual(
            result["ConnectionProperties"]["KAFKA_CLIENT_KEY_PASSWORD"], "***MASKED***"
        )
        self.assertEqual(
            result["ConnectionProperties"]["KAFKA_SASL_PLAIN_USERNAME"], "***MASKED***"
        )
        self.assertEqual(
            result["ConnectionProperties"]["KAFKA_SASL_PLAIN_PASSWORD"], "***MASKED***"
        )
        self.assertEqual(
            result["ConnectionProperties"]["KAFKA_BOOTSTRAP_SERVERS"], "broker1:9092,broker2:9092"
        )

    def test_sanitize_aws_fields(self):
        """Test sanitization of AWS-specific fields."""
        connection = {
            "SparkProperties": {
                "temporary_aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "temporary_aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "aws_iam_role": "arn:aws:iam::123456789012:role/MyRole",
                "region": "us-east-1",
            }
        }

        result = sanitize_connection_for_logging(connection)

        self.assertEqual(result["SparkProperties"]["temporary_aws_access_key_id"], "***MASKED***")
        self.assertEqual(
            result["SparkProperties"]["temporary_aws_secret_access_key"], "***MASKED***"
        )
        self.assertEqual(result["SparkProperties"]["aws_iam_role"], "***MASKED***")
        self.assertEqual(result["SparkProperties"]["region"], "us-east-1")

    def test_sanitize_oauth_fields(self):
        """Test sanitization of OAuth-specific fields."""
        connection = {
            "SparkProperties": {
                "ACCESS_TOKEN": "oauth_access_token",
                "REFRESH_TOKEN": "oauth_refresh_token",
                "clientId": "my_client_id",
                "authenticationType": "OAUTH2",
            }
        }

        result = sanitize_connection_for_logging(connection)

        self.assertEqual(result["SparkProperties"]["ACCESS_TOKEN"], "***MASKED***")
        self.assertEqual(result["SparkProperties"]["REFRESH_TOKEN"], "***MASKED***")
        self.assertEqual(result["SparkProperties"]["clientId"], "***MASKED***")
        self.assertEqual(result["SparkProperties"]["authenticationType"], "***MASKED***")

    def test_sanitize_empty_connection(self):
        """Test sanitization of empty connection."""
        connection: Dict[str, Any] = {}
        result = sanitize_connection_for_logging(connection)
        self.assertEqual(result, {})

    def test_sanitize_non_dict_values(self):
        """Test sanitization handles non-dict values correctly."""
        connection = {
            "Name": "test-connection",
            "Port": 5432,
            "Enabled": True,
            "Tags": ["tag1", "tag2"],
            "password": "secret",
        }

        result = sanitize_connection_for_logging(connection)

        self.assertEqual(result["Name"], "test-connection")
        self.assertEqual(result["Port"], 5432)
        self.assertEqual(result["Enabled"], True)
        self.assertEqual(result["Tags"], ["tag1", "tag2"])
        self.assertEqual(result["password"], "***MASKED***")


if __name__ == "__main__":
    unittest.main()
