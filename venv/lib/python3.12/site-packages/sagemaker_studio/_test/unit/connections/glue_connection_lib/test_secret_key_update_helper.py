"""
Unit tests for secret key helper functions.
"""

import unittest
from typing import Dict

from sagemaker_studio.connections.glue_connection_lib.connections.utils.secret_key_update_helper import (
    add_connection_type_secret_keys,
    add_oauth2_token_keys,
    find_key_ignore_case,
    get_connection_specific_secret_map,
)


class TestSecretKeyHelpers(unittest.TestCase):
    """Test cases for secret key helper functions."""

    def test_find_key_ignore_case_exact_match(self):
        """Test find_key_ignore_case with exact match."""
        test_map = {"USERNAME": "user1", "PASSWORD": "pass1"}
        result = find_key_ignore_case(test_map, "USERNAME")
        self.assertEqual(result, "USERNAME")

    def test_find_key_ignore_case_case_insensitive(self):
        """Test find_key_ignore_case with case insensitive match."""
        test_map = {"UserName": "user1", "PASSWORD": "pass1"}
        result = find_key_ignore_case(test_map, "username")
        self.assertEqual(result, "UserName")

    def test_find_key_ignore_case_no_match(self):
        """Test find_key_ignore_case when key not found."""
        test_map = {"USERNAME": "user1", "PASSWORD": "pass1"}
        result = find_key_ignore_case(test_map, "nonexistent")
        self.assertIsNone(result)

    def test_find_key_ignore_case_empty_map(self):
        """Test find_key_ignore_case with empty map."""
        test_map: Dict[str, str] = {}
        result = find_key_ignore_case(test_map, "USERNAME")
        self.assertIsNone(result)

    def test_add_connection_type_secret_keys_exact_match(self):
        """Test add_connection_type_secret_keys with exact key matches."""
        secret_map = {"USERNAME": "user1", "PASSWORD": "pass1"}
        add_connection_type_secret_keys("custom_user", "custom_pass", secret_map)

        expected = {
            "USERNAME": "user1",
            "PASSWORD": "pass1",
            "custom_user": "user1",
            "custom_pass": "pass1",
        }
        self.assertEqual(secret_map, expected)

    def test_add_connection_type_secret_keys_case_insensitive(self):
        """Test add_connection_type_secret_keys with case insensitive keys."""
        secret_map = {"username": "user1", "Password": "pass1"}
        add_connection_type_secret_keys("custom_user", "custom_pass", secret_map)

        expected = {
            "username": "user1",
            "Password": "pass1",
            "custom_user": "user1",
            "custom_pass": "pass1",
        }
        self.assertEqual(secret_map, expected)

    def test_add_connection_type_secret_keys_missing_username(self):
        """Test add_connection_type_secret_keys when USERNAME is missing."""
        secret_map = {"PASSWORD": "pass1", "other_key": "other_value"}
        add_connection_type_secret_keys("custom_user", "custom_pass", secret_map)

        expected = {"PASSWORD": "pass1", "other_key": "other_value", "custom_pass": "pass1"}
        self.assertEqual(secret_map, expected)

    def test_add_connection_type_secret_keys_missing_password(self):
        """Test add_connection_type_secret_keys when PASSWORD is missing."""
        secret_map = {"USERNAME": "user1", "other_key": "other_value"}
        add_connection_type_secret_keys("custom_user", "custom_pass", secret_map)

        expected = {"USERNAME": "user1", "other_key": "other_value", "custom_user": "user1"}
        self.assertEqual(secret_map, expected)

    def test_add_connection_type_secret_keys_missing_both(self):
        """Test add_connection_type_secret_keys when both USERNAME and PASSWORD are missing."""
        secret_map = {"other_key": "other_value"}
        add_connection_type_secret_keys("custom_user", "custom_pass", secret_map)

        # Should not add custom keys if USERNAME/PASSWORD not found
        expected = {"other_key": "other_value"}
        self.assertEqual(secret_map, expected)

    def test_add_connection_type_secret_keys_empty_map(self):
        """Test add_connection_type_secret_keys with empty map."""
        secret_map: Dict[str, str] = {}
        add_connection_type_secret_keys("custom_user", "custom_pass", secret_map)

        # Should remain empty
        self.assertEqual(secret_map, {})

    def test_get_connection_specific_secret_map_empty_secret_map(self):
        """Test with empty secret map returns empty dict."""
        result = get_connection_specific_secret_map({}, "mysql")
        self.assertEqual(result, {})

    def test_get_connection_specific_secret_map_none_secret_map(self):
        """Test with None secret map returns empty dict."""
        result = get_connection_specific_secret_map(None, "mysql")
        self.assertEqual(result, {})

    def test_get_connection_specific_secret_map_none_connection_type(self):
        """Test with None connection type returns copy of original map."""
        secret_map = {"USERNAME": "user1", "PASSWORD": "pass1"}
        result = get_connection_specific_secret_map(secret_map, None)
        self.assertEqual(result, secret_map)
        # Ensure it's a copy, not the same object
        self.assertIsNot(result, secret_map)

    def test_snowflake_connection_type(self):
        """Test Snowflake connection type adds sfUser and sfPassword keys."""
        secret_map = {"USERNAME": "snowflake_user", "PASSWORD": "snowflake_pass"}
        result = get_connection_specific_secret_map(secret_map, "snowflake")

        expected = {
            "USERNAME": "snowflake_user",
            "PASSWORD": "snowflake_pass",
            "sfUser": "snowflake_user",
            "sfPassword": "snowflake_pass",
        }
        self.assertEqual(result, expected)

    def test_snowflake_oauth2_connection_type(self):
        """Test Snowflake OAuth2 connection type mapping."""
        secret_map = {"ACCESS_TOKEN": "oauth_token_123"}
        result = get_connection_specific_secret_map(secret_map, "snowflake", "OAUTH2")

        expected = {"ACCESS_TOKEN": "oauth_token_123", "sftoken": "oauth_token_123"}
        self.assertEqual(result, expected)

    def test_snowflake_oauth2_case_insensitive(self):
        """Test Snowflake OAuth2 with case insensitive auth type."""
        secret_map = {"ACCESS_TOKEN": "oauth_token_123"}
        result = get_connection_specific_secret_map(secret_map, "snowflake", "oauth2")

        expected = {"ACCESS_TOKEN": "oauth_token_123", "sftoken": "oauth_token_123"}
        self.assertEqual(result, expected)

    def test_snowflake_oauth2_missing_access_token(self):
        """Test Snowflake OAuth2 without ACCESS_TOKEN."""
        secret_map = {"REFRESH_TOKEN": "refresh_token_123"}
        result = get_connection_specific_secret_map(secret_map, "snowflake", "OAUTH2")

        expected = {"REFRESH_TOKEN": "refresh_token_123"}
        self.assertEqual(result, expected)

    def test_add_oauth2_token_keys_unknown_connection(self):
        """Test add_oauth2_token_keys for unknown connection type."""
        secret_map = {"ACCESS_TOKEN": "oauth_token_123"}
        add_oauth2_token_keys("UNKNOWN", secret_map)

        # Should not modify the map for unknown connection types
        self.assertNotIn("sftoken", secret_map)
        self.assertEqual(secret_map, {"ACCESS_TOKEN": "oauth_token_123"})

    def test_jdbc_connection_types(self):
        """Test JDBC-related connection types add username and password keys."""
        secret_map = {"USERNAME": "jdbc_user", "PASSWORD": "jdbc_pass"}

        for conn_type in ["JDBC", "MYSQL", "SQLSERVER", "ORACLE", "POSTGRESQL", "REDSHIFT"]:
            with self.subTest(connection_type=conn_type):
                result = get_connection_specific_secret_map(secret_map, conn_type)

                expected = {
                    "USERNAME": "jdbc_user",
                    "PASSWORD": "jdbc_pass",
                    "username": "jdbc_user",
                    "password": "jdbc_pass",
                }
                self.assertEqual(result, expected)

    def test_document_db_mongodb_connection_types(self):
        """Test DocumentDB and MongoDB connection types add username and password keys."""
        secret_map = {"USERNAME": "mongo_user", "PASSWORD": "mongo_pass"}

        for conn_type in ["DOCUMENTDB", "MONGODB"]:
            with self.subTest(connection_type=conn_type):
                result = get_connection_specific_secret_map(secret_map, conn_type)

                expected = {
                    "USERNAME": "mongo_user",
                    "PASSWORD": "mongo_pass",
                    "username": "mongo_user",
                    "password": "mongo_pass",
                }
                self.assertEqual(result, expected)

    def test_vertica_saphana_connection_types(self):
        """Test Vertica, SAP HANA, etc. connection types add user and password keys."""
        secret_map = {"USERNAME": "db_user", "PASSWORD": "db_pass"}

        for conn_type in ["VERTICA", "SAPHANA", "TERADATA", "AZURESQL"]:
            with self.subTest(connection_type=conn_type):
                result = get_connection_specific_secret_map(secret_map, conn_type)

                expected = {
                    "USERNAME": "db_user",
                    "PASSWORD": "db_pass",
                    "user": "db_user",
                    "password": "db_pass",
                }
                self.assertEqual(result, expected)

    def test_opensearch_connection_type(self):
        """Test OpenSearch connection type adds specific auth keys."""
        secret_map = {"USERNAME": "opensearch_user", "PASSWORD": "opensearch_pass"}
        result = get_connection_specific_secret_map(secret_map, "opensearch")

        expected = {
            "USERNAME": "opensearch_user",
            "PASSWORD": "opensearch_pass",
            "opensearch.net.http.auth.user": "opensearch_user",
            "opensearch.net.http.auth.pass": "opensearch_pass",
        }
        self.assertEqual(result, expected)

    def test_bigquery_connection_type_with_existing_credentials(self):
        """Test BigQuery connection type with existing credentials key."""
        secret_map = {"credentials": "existing_creds", "USERNAME": "bq_user"}
        result = get_connection_specific_secret_map(secret_map, "bigquery")

        # Should not modify existing credentials
        expected = {"credentials": "existing_creds", "USERNAME": "bq_user"}
        self.assertEqual(result, expected)

    def test_bigquery_connection_type_without_credentials(self):
        """Test BigQuery connection type without existing credentials key."""
        import base64
        import json

        secret_map = {"USERNAME": "bq_user", "PASSWORD": "bq_pass"}
        result = get_connection_specific_secret_map(secret_map, "bigquery")

        # Should add base64 encoded JSON of the secret map
        expected_json = json.dumps(secret_map)
        expected_credentials = base64.b64encode(expected_json.encode("utf-8")).decode("utf-8")

        expected = {
            "USERNAME": "bq_user",
            "PASSWORD": "bq_pass",
            "credentials": expected_credentials,
        }
        self.assertEqual(result, expected)

    def test_dynamodb_connection_type(self):
        """Test DynamoDB connection type uses IAM, no transformation."""
        secret_map = {"USERNAME": "dynamo_user", "PASSWORD": "dynamo_pass"}
        result = get_connection_specific_secret_map(secret_map, "dynamodb")

        # Should return unchanged
        self.assertEqual(result, secret_map)

    def test_unknown_connection_type(self):
        """Test unknown connection type returns unchanged map."""
        secret_map = {"USERNAME": "unknown_user", "PASSWORD": "unknown_pass"}
        result = get_connection_specific_secret_map(secret_map, "unknown_type")

        # Should return unchanged
        self.assertEqual(result, secret_map)

    def test_case_insensitive_connection_type(self):
        """Test connection type matching is case insensitive."""
        secret_map = {"USERNAME": "user", "PASSWORD": "pass"}

        # Test lowercase
        result = get_connection_specific_secret_map(secret_map, "mysql")
        self.assertIn("username", result)

        # Test mixed case
        result = get_connection_specific_secret_map(secret_map, "MySql")
        self.assertIn("username", result)


if __name__ == "__main__":
    unittest.main()
