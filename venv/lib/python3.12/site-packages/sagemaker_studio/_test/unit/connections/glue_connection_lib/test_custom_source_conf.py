"""
Unit tests for CustomSourceConf.
"""

import unittest

from sagemaker_studio.connections.glue_connection_lib.connections.config.custom_source_conf import (
    CustomSourceConf,
)


class TestCustomSourceConf(unittest.TestCase):
    """Test cases for CustomSourceConf."""

    def test_as_map_with_credentials(self):
        """Test as_map with normal username and password."""
        custom_conf = CustomSourceConf(
            connection_type="CUSTOM",
            class_name="com.example.CustomConnector",
            url="jdbc:custom://test:1234/db",
            user="testuser",
            password="testpass",
            secret_id="test-secret",
        )

        result = custom_conf.as_map()

        self.assertEqual(result["user"], "testuser")
        self.assertEqual(result["password"], "testpass")
        self.assertEqual(result["connectionType"], "CUSTOM")
        self.assertEqual(result["className"], "com.example.CustomConnector")
        self.assertEqual(result["url"], "jdbc:custom://test:1234/db")
        self.assertEqual(result["secretId"], "test-secret")

    def test_as_map_with_null_credentials_for_iam(self):
        """Test as_map with null credentials for IAM authentication."""
        custom_conf = CustomSourceConf(
            connection_type="CUSTOM",
            class_name="com.example.CustomConnector",
            url="jdbc:custom://test:1234/db",
            user=None,
            password=None,
            secret_id="test-secret",
        )

        result = custom_conf.as_map()

        # Should not contain user or password keys
        self.assertNotIn("user", result)
        self.assertNotIn("password", result)
        self.assertEqual(result["connectionType"], "CUSTOM")
        self.assertEqual(result["className"], "com.example.CustomConnector")
        self.assertEqual(result["url"], "jdbc:custom://test:1234/db")
        self.assertEqual(result["secretId"], "test-secret")


if __name__ == "__main__":
    unittest.main()
