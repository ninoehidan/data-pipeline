"""
Test cases for JDBC Connection Wrapper.
"""

import unittest
from unittest.mock import Mock, patch

from sagemaker_studio.connections.glue_connection_lib.connections.constants import (
    ConnectionObjectKey,
    ConnectionPropertyKey,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.glue_connection_wrapper_inputs import (
    GlueConnectionWrapperInputs,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.jdbc.jdbc_wrapper import (
    JDBCConnectionWrapper,
)


class TestJDBCConnectionWrapper(unittest.TestCase):
    """Test cases for JDBCConnectionWrapper."""

    def test_get_driver_options_postgresql(self):
        """Test driver options for PostgreSQL."""
        # Create minimal connection for testing
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "postgresql",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {},
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = JDBCConnectionWrapper(wrapper_input)
        result = wrapper._get_driver_options("postgresql")

        self.assertEqual(result, {"driver": "org.postgresql.Driver"})

    def test_get_driver_options_other_types(self):
        """Test driver options for non-PostgreSQL types."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "mysql",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {},
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = JDBCConnectionWrapper(wrapper_input)

        # Test various connection types
        self.assertEqual(wrapper._get_driver_options("mysql"), {})
        self.assertEqual(wrapper._get_driver_options("oracle"), {})
        self.assertEqual(wrapper._get_driver_options("redshift"), {})

    def test_get_vendor_string_success(self):
        """Test successful vendor string extraction."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "JDBC",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {
                ConnectionPropertyKey.JDBC_CONNECTION_URL: "jdbc:postgresql://localhost:5432/testdb"
            },
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = JDBCConnectionWrapper(wrapper_input)
        result = wrapper._get_vendor_string()

        self.assertEqual(result, "postgresql")

    def test_get_vendor_string_missing_url(self):
        """Test vendor string extraction with missing JDBC URL."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "JDBC",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {},
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = JDBCConnectionWrapper(wrapper_input)

        with self.assertRaises(ValueError) as context:
            wrapper._get_vendor_string()

        self.assertIn("JDBC_CONNECTION_URL should not be empty or null", str(context.exception))

    def test_get_vendor_string_different_vendors(self):
        """Test vendor string extraction for different database vendors."""
        test_cases = [
            ("jdbc:mysql://localhost:3306/testdb", "mysql"),
            ("jdbc:oracle:thin:@//localhost:1521/xe", "oracle"),
            ("jdbc:redshift://cluster.region.redshift.amazonaws.com:5439/dev", "redshift"),
        ]

        for jdbc_url, expected_vendor in test_cases:
            connection = {
                ConnectionObjectKey.CONNECTION_TYPE: "JDBC",
                ConnectionObjectKey.CONNECTION_PROPERTIES: {
                    ConnectionPropertyKey.JDBC_CONNECTION_URL: jdbc_url
                },
            }

            wrapper_input = GlueConnectionWrapperInputs(
                connection=connection,
                additional_options={},
                kms_client=Mock(),
                secrets_manager_client=Mock(),
            )

            wrapper = JDBCConnectionWrapper(wrapper_input)
            result = wrapper._get_vendor_string()

            self.assertEqual(result, expected_vendor)

    def test_get_resolved_connection_basic(self):
        """Test basic get_resolved_connection functionality."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "postgresql",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {
                ConnectionPropertyKey.JDBC_CONNECTION_URL: "jdbc:postgresql://localhost:5432/testdb",
                ConnectionPropertyKey.USERNAME: "testuser",
                ConnectionPropertyKey.PASSWORD: "testpass",
            },
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        with patch(
            "sagemaker_studio.connections.glue_connection_lib.connections.utils.jdbc_url_update_helper.JDBCUrlUpdateHelper.update_url_in_props"
        ) as mock_url_update:
            mock_url_update.return_value = {
                "url": "jdbc:postgresql://localhost:5432/testdb",
                "fullUrl": "jdbc:postgresql://localhost:5432/testdb",
                "user": "testuser",
                "password": "testpass",
            }

            wrapper = JDBCConnectionWrapper(wrapper_input)
            result = wrapper.get_resolved_connection()

            # Verify structure
            self.assertIn(ConnectionObjectKey.SPARK_PROPERTIES, result)
            spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
            self.assertIn("driver", spark_props)
            self.assertEqual(spark_props["driver"], "org.postgresql.Driver")
            self.assertIn("url", spark_props)
            self.assertIn("fullUrl", spark_props)

    def test_get_resolved_connection_custom_cert_error(self):
        """Test that custom JDBC cert raises error."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "postgresql",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {
                ConnectionPropertyKey.JDBC_CONNECTION_URL: "jdbc:postgresql://localhost:5432/testdb",
                ConnectionPropertyKey.USERNAME: "testuser",
                ConnectionPropertyKey.PASSWORD: "testpass",
                ConnectionPropertyKey.CUSTOM_JDBC_CERT: "/path/to/cert",
            },
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = JDBCConnectionWrapper(wrapper_input)

        with self.assertRaises(ValueError) as context:
            wrapper.get_resolved_connection()

        self.assertIn(
            "Custom JDBC cert is not supported for spark dataframe", str(context.exception)
        )

    def test_get_resolved_connection_with_ssl_legacy(self):
        """Test get_resolved_connection with SSL enabled and legacy connection."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "postgresql",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {
                ConnectionPropertyKey.JDBC_CONNECTION_URL: "jdbc:postgresql://localhost:5432/testdb",
                ConnectionPropertyKey.USERNAME: "testuser",
                ConnectionPropertyKey.PASSWORD: "testpass",
                ConnectionPropertyKey.JDBC_ENFORCE_SSL: "true",
            },
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        with patch(
            "sagemaker_studio.connections.glue_connection_lib.connections.utils.utils.is_legacy_connection"
        ) as mock_is_legacy, patch(
            "sagemaker_studio.connections.glue_connection_lib.connections.utils.jdbc_url_update_helper.JDBCUrlUpdateHelper.update_url_in_props"
        ) as mock_url_update:

            mock_is_legacy.return_value = True
            mock_url_update.return_value = {
                "url": "jdbc:postgresql://localhost:5432/testdb",
                "fullUrl": "jdbc:postgresql://localhost:5432/testdb",
                "user": "testuser",
                "password": "testpass",
            }

            wrapper = JDBCConnectionWrapper(wrapper_input)
            result = wrapper.get_resolved_connection()

            # Verify SSL properties were applied
            spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
            self.assertIn("driver", spark_props)
            mock_is_legacy.assert_called_once()

    def test_get_resolved_connection_with_ssl_non_legacy(self):
        """Test get_resolved_connection with SSL enabled and non-legacy connection."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "postgresql",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {
                ConnectionPropertyKey.JDBC_CONNECTION_URL: "jdbc:postgresql://localhost:5432/testdb",
                ConnectionPropertyKey.USERNAME: "testuser",
                ConnectionPropertyKey.PASSWORD: "testpass",
                ConnectionPropertyKey.JDBC_ENFORCE_SSL: "true",
            },
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        with patch(
            "sagemaker_studio.connections.glue_connection_lib.connections.utils.utils.is_legacy_connection"
        ) as mock_is_legacy, patch(
            "sagemaker_studio.connections.glue_connection_lib.connections.utils.jdbc_url_update_helper.JDBCUrlUpdateHelper.update_url_in_props"
        ) as mock_url_update:

            mock_is_legacy.return_value = False
            mock_url_update.return_value = {
                "url": "jdbc:postgresql://localhost:5432/testdb",
                "fullUrl": "jdbc:postgresql://localhost:5432/testdb",
                "user": "testuser",
                "password": "testpass",
            }

            wrapper = JDBCConnectionWrapper(wrapper_input)
            result = wrapper.get_resolved_connection()

            # Verify SSL properties were applied
            spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
            self.assertIn("driver", spark_props)
            mock_is_legacy.assert_called_once()

    def test_get_resolved_connection_custom_cert_string_error(self):
        """Test that custom JDBC cert string raises error."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "postgresql",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {
                ConnectionPropertyKey.JDBC_CONNECTION_URL: "jdbc:postgresql://localhost:5432/testdb",
                ConnectionPropertyKey.USERNAME: "testuser",
                ConnectionPropertyKey.PASSWORD: "testpass",
                ConnectionPropertyKey.CUSTOM_JDBC_CERT_STRING: "cert-content",
            },
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = JDBCConnectionWrapper(wrapper_input)

        with self.assertRaises(ValueError) as context:
            wrapper.get_resolved_connection()

        self.assertIn(
            "Custom JDBC cert is not supported for spark dataframe", str(context.exception)
        )

    def test_get_resolved_connection_no_full_url(self):
        """Test get_resolved_connection when fullUrl is missing from options."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "postgresql",
            ConnectionObjectKey.CONNECTION_PROPERTIES: {
                ConnectionPropertyKey.JDBC_CONNECTION_URL: "jdbc:postgresql://localhost:5432/testdb",
                ConnectionPropertyKey.USERNAME: "testuser",
                ConnectionPropertyKey.PASSWORD: "testpass",
            },
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        with patch(
            "sagemaker_studio.connections.glue_connection_lib.connections.utils.jdbc_url_update_helper.JDBCUrlUpdateHelper.update_url_in_props"
        ) as mock_url_update:
            # Return options without fullUrl to test the missing branch
            mock_url_update.return_value = {
                "url": "jdbc:postgresql://localhost:5432/testdb",
                "user": "testuser",
                "password": "testpass",
                # Note: no "fullUrl" key
            }

            wrapper = JDBCConnectionWrapper(wrapper_input)
            result = wrapper.get_resolved_connection()

            # Verify structure - url should remain as is when fullUrl is missing
            spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
            self.assertEqual(spark_props["url"], "jdbc:postgresql://localhost:5432/testdb")
            self.assertNotIn("fullUrl", spark_props)

    def test_get_resolved_connection_ssl_non_legacy_case_insensitive(self):
        """Test SSL with non-legacy connection uses connection type directly."""
        connection = {
            ConnectionObjectKey.CONNECTION_TYPE: "POSTGRESQL",  # Uppercase to test .lower()
            ConnectionObjectKey.CONNECTION_PROPERTIES: {
                ConnectionPropertyKey.JDBC_CONNECTION_URL: "jdbc:postgresql://localhost:5432/testdb",
                ConnectionPropertyKey.USERNAME: "testuser",
                ConnectionPropertyKey.PASSWORD: "testpass",
                ConnectionPropertyKey.JDBC_ENFORCE_SSL: "true",
            },
        }

        wrapper_input = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        with patch(
            "sagemaker_studio.connections.glue_connection_lib.connections.utils.utils.is_legacy_connection"
        ) as mock_is_legacy, patch(
            "sagemaker_studio.connections.glue_connection_lib.connections.utils.jdbc_url_update_helper.JDBCUrlUpdateHelper.update_url_in_props"
        ) as mock_url_update:

            mock_is_legacy.return_value = False  # Force non-legacy path
            mock_url_update.return_value = {
                "url": "jdbc:postgresql://localhost:5432/testdb",
                "fullUrl": "jdbc:postgresql://localhost:5432/testdb",
                "user": "testuser",
                "password": "testpass",
            }

            wrapper = JDBCConnectionWrapper(wrapper_input)
            result = wrapper.get_resolved_connection()

            # Verify the non-legacy path was taken
            mock_is_legacy.assert_called_once()
            spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
            self.assertIn("url", spark_props)
