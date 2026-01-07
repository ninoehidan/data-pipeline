"""
Unit tests for JDBCConf.
"""

import unittest

from sagemaker_studio.connections.glue_connection_lib.connections.config.jdbc_conf import JDBCConf


class TestJDBCConf(unittest.TestCase):
    """Test cases for JDBCConf."""

    def test_as_map_with_credentials(self):
        """Test as_map with normal username and password."""
        jdbc_conf = JDBCConf(
            user="testuser",
            password="testpass",
            vendor="redshift",
            url="jdbc:redshift://test:5439/db",
            enforce_ssl="false",
            custom_jdbc_cert="",
            skip_custom_jdbc_cert_validation="false",
            custom_jdbc_cert_string="",
            full_url="jdbc:redshift://test:5439/db",
        )

        result = jdbc_conf.as_map()

        self.assertEqual(result["user"], "testuser")
        self.assertEqual(result["password"], "testpass")
        self.assertEqual(result["vendor"], "redshift")

    def test_as_map_with_null_credentials_for_iam(self):
        """Test as_map with null credentials for IAM authentication."""
        jdbc_conf = JDBCConf(
            user=None,
            password=None,
            vendor="redshift",
            url="jdbc:redshift:iam://test:5439/db",
            enforce_ssl="false",
            custom_jdbc_cert="",
            skip_custom_jdbc_cert_validation="false",
            custom_jdbc_cert_string="",
            full_url="jdbc:redshift:iam://test:5439/db",
        )

        result = jdbc_conf.as_map()

        # Should not contain user or password keys
        self.assertNotIn("user", result)
        self.assertNotIn("password", result)
        self.assertEqual(result["vendor"], "redshift")
        self.assertEqual(result["url"], "jdbc:redshift:iam://test:5439/db")

    def test_as_map_native_jdbc_with_credentials(self):
        """Test as_map for native JDBC with credentials."""
        jdbc_conf = JDBCConf(
            user="testuser",
            password="testpass",
            vendor="saphana",
            url="jdbc:sap://test:30015",
            enforce_ssl="false",
            custom_jdbc_cert="",
            skip_custom_jdbc_cert_validation="false",
            custom_jdbc_cert_string="",
            full_url="jdbc:sap://test:30015",
        )

        result = jdbc_conf.as_map()

        self.assertEqual(result["username"], "testuser")
        self.assertEqual(result["password"], "testpass")
        self.assertEqual(result["url"], "jdbc:sap://test:30015")

    def test_as_map_native_jdbc_with_null_credentials(self):
        """Test as_map for native JDBC with null credentials."""
        jdbc_conf = JDBCConf(
            user=None,
            password=None,
            vendor="saphana",
            url="jdbc:sap://test:30015",
            enforce_ssl="false",
            custom_jdbc_cert="",
            skip_custom_jdbc_cert_validation="false",
            custom_jdbc_cert_string="",
            full_url="jdbc:sap://test:30015",
        )

        result = jdbc_conf.as_map()

        # Should not contain username or password keys
        self.assertNotIn("username", result)
        self.assertNotIn("password", result)
        self.assertEqual(result["url"], "jdbc:sap://test:30015")


if __name__ == "__main__":
    unittest.main()
