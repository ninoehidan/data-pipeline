"""Tests for Snowflake connection wrapper."""

import json
import unittest
from unittest.mock import Mock

from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.glue_connection_wrapper_inputs import (
    GlueConnectionWrapperInputs,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.local.snowflake_wrapper import (
    SnowflakeConnectionWrapper,
)


class TestSnowflakeConnectionWrapper(unittest.TestCase):
    """Test cases for SnowflakeConnectionWrapper."""

    def test_get_resolved_connection_removes_conflicting_keys(self):
        """Test that conflicting DATABASE, SCHEMA, WAREHOUSE keys are removed."""
        mock_connection = {
            "Name": "test-snowflake-connection",
            "ConnectionType": "SNOWFLAKE",
            "ConnectionProperties": {
                "SparkProperties": json.dumps(
                    {
                        "url": "test-url",
                        "DATABASE": "test_db",
                        "SCHEMA": "test_schema",
                        "WAREHOUSE": "test_warehouse",
                        "sfDatabase": "snowflake_db",
                        "sfSchema": "snowflake_schema",
                        "sfWarehouse": "snowflake_warehouse",
                        "user": "testuser",
                    }
                )
            },
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = SnowflakeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        # Verify conflicting keys are removed
        spark_properties = result["SparkProperties"]
        self.assertNotIn("DATABASE", spark_properties)
        self.assertNotIn("SCHEMA", spark_properties)
        self.assertNotIn("WAREHOUSE", spark_properties)

        # Verify Snowflake-specific keys are preserved
        self.assertIn("sfDatabase", spark_properties)
        self.assertIn("sfSchema", spark_properties)
        self.assertIn("sfWarehouse", spark_properties)
        self.assertIn("user", spark_properties)
        self.assertIn("url", spark_properties)

    def test_get_resolved_connection_no_spark_properties(self):
        """Test behavior when no SparkProperties exist."""
        mock_connection = {
            "Name": "test-snowflake-connection",
            "ConnectionType": "SNOWFLAKE",
            "ConnectionProperties": {},
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = SnowflakeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        # Should not fail and return connection with empty SparkProperties
        self.assertEqual(result["Name"], "test-snowflake-connection")
        self.assertEqual(result["SparkProperties"], {})

    def test_get_resolved_connection_with_secrets(self):
        """Test Snowflake wrapper with secret handling."""
        mock_connection = {
            "Name": "test-snowflake-connection",
            "ConnectionType": "SNOWFLAKE",
            "ConnectionProperties": {
                "SparkProperties": json.dumps(
                    {"url": "test-url", "DATABASE": "test_db", "secretId": "test-secret"}
                )
            },
        }

        mock_secrets_manager_client = Mock()
        secret_data = {"user": "testuser", "password": "testpass"}
        mock_secrets_manager_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        wrapper_inputs = GlueConnectionWrapperInputs(
            connection=mock_connection,
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=mock_secrets_manager_client,
        )

        wrapper = SnowflakeConnectionWrapper(wrapper_inputs)
        result = wrapper.get_resolved_connection()

        spark_properties = result["SparkProperties"]

        # Verify DATABASE is removed
        self.assertNotIn("DATABASE", spark_properties)

        # Verify secret credentials are added
        self.assertEqual(spark_properties["user"], "testuser")
        self.assertEqual(spark_properties["password"], "testpass")
        self.assertEqual(spark_properties["url"], "test-url")

    def test_combine_options_handles_missing_keys(self):
        """Test _combine_options when conflicting keys don't exist."""
        wrapper_inputs = GlueConnectionWrapperInputs(
            connection={"ConnectionType": "SNOWFLAKE"},
            additional_options={},
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = SnowflakeConnectionWrapper(wrapper_inputs)

        original_options = {"url": "test-url", "sfDatabase": "snowflake_db", "user": "testuser"}

        result = wrapper._combine_options(original_options)

        # Should not fail and preserve all existing keys
        self.assertEqual(result, original_options)


if __name__ == "__main__":
    unittest.main()
