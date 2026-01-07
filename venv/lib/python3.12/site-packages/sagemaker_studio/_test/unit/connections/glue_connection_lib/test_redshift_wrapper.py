"""
Unit tests for RedshiftJDBCConnectionWrapper.
"""

import unittest
from unittest.mock import Mock, patch

from sagemaker_studio.connections.glue_connection_lib.connections.constants import (
    ConnectionObjectKey,
    RedshiftOptionValues,
    SparkOptionsKey,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.glue_connection_wrapper_inputs import (
    GlueConnectionWrapperInputs,
)
from sagemaker_studio.connections.glue_connection_lib.connections.wrapper.jdbc.redshift_wrapper import (
    RedshiftJDBCConnectionWrapper,
)


class TestRedshiftJDBCConnectionWrapper(unittest.TestCase):
    """Test cases for RedshiftJDBCConnectionWrapper."""

    @patch(
        "sagemaker_studio.connections.glue_connection_lib.connections.wrapper.jdbc.redshift_wrapper.JDBCConnectionWrapper.get_resolved_connection"
    )
    def test_get_resolved_connection_with_iam_role(self, mock_super_get_resolved):
        """Test get_resolved_connection when aws_iam_role is present."""
        # Mock parent method return
        mock_super_get_resolved.return_value = {
            ConnectionObjectKey.CONNECTION_TYPE: "redshift",
            ConnectionObjectKey.SPARK_PROPERTIES: {
                SparkOptionsKey.URL: "jdbc:redshift://cluster.region.redshift.amazonaws.com:5439/db",
                SparkOptionsKey.USER: "testuser",
                SparkOptionsKey.PASSWORD: "testpass",
                SparkOptionsKey.AWS_IAM_ROLE: "arn:aws:iam::123456789012:role/RedshiftRole",
            },
        }

        mock_input = Mock()
        mock_input.additional_options.items.return_value = []
        wrapper = RedshiftJDBCConnectionWrapper(mock_input)
        result = wrapper.get_resolved_connection()

        # Should not add forward_spark_s3_credentials since aws_iam_role is present
        spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
        self.assertNotIn(SparkOptionsKey.FORWARD_SPARK_S3_CREDENTIALS, spark_props)
        self.assertEqual(spark_props[SparkOptionsKey.TEMPFORMAT], RedshiftOptionValues.AVRO_FORMAT)

    @patch(
        "sagemaker_studio.connections.glue_connection_lib.connections.wrapper.jdbc.redshift_wrapper.JDBCConnectionWrapper.get_resolved_connection"
    )
    def test_get_resolved_connection_with_temp_credentials(self, mock_super_get_resolved):
        """Test get_resolved_connection when temporary AWS credentials are present."""
        # Mock parent method return
        mock_super_get_resolved.return_value = {
            ConnectionObjectKey.CONNECTION_TYPE: "redshift",
            ConnectionObjectKey.SPARK_PROPERTIES: {
                SparkOptionsKey.URL: "jdbc:redshift://cluster.region.redshift.amazonaws.com:5439/db",
                SparkOptionsKey.USER: "testuser",
                SparkOptionsKey.PASSWORD: "testpass",
                SparkOptionsKey.TEMPORARY_AWS_ACCESS_KEY_ID: "AKIAIOSFODNN7EXAMPLE",
                SparkOptionsKey.TEMPORARY_AWS_SECRET_ACCESS_KEY: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                SparkOptionsKey.TEMPORARY_AWS_SESSION_TOKEN: "session_token_example",
            },
        }

        mock_input = Mock()
        mock_input.additional_options.items.return_value = []
        wrapper = RedshiftJDBCConnectionWrapper(mock_input)
        result = wrapper.get_resolved_connection()

        # Should not add forward_spark_s3_credentials since temp credentials are present
        spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
        self.assertNotIn(SparkOptionsKey.FORWARD_SPARK_S3_CREDENTIALS, spark_props)
        self.assertEqual(spark_props[SparkOptionsKey.TEMPFORMAT], RedshiftOptionValues.AVRO_FORMAT)

    @patch(
        "sagemaker_studio.connections.glue_connection_lib.connections.wrapper.jdbc.redshift_wrapper.JDBCConnectionWrapper.get_resolved_connection"
    )
    def test_get_resolved_connection_without_credentials(self, mock_super_get_resolved):
        """Test get_resolved_connection when no IAM role or temp credentials are present."""
        # Mock parent method return
        mock_super_get_resolved.return_value = {
            ConnectionObjectKey.CONNECTION_TYPE: "redshift",
            ConnectionObjectKey.SPARK_PROPERTIES: {
                SparkOptionsKey.URL: "jdbc:redshift://cluster.region.redshift.amazonaws.com:5439/db",
                SparkOptionsKey.USER: "testuser",
                SparkOptionsKey.PASSWORD: "testpass",
            },
        }

        mock_input = Mock()
        mock_input.additional_options.items.return_value = []
        wrapper = RedshiftJDBCConnectionWrapper(mock_input)
        result = wrapper.get_resolved_connection()

        # Should add forward_spark_s3_credentials since no IAM role or temp credentials
        spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
        self.assertEqual(
            spark_props[SparkOptionsKey.FORWARD_SPARK_S3_CREDENTIALS],
            RedshiftOptionValues.TRUE,
        )
        self.assertEqual(spark_props[SparkOptionsKey.TEMPFORMAT], RedshiftOptionValues.AVRO_FORMAT)

    @patch(
        "sagemaker_studio.connections.glue_connection_lib.connections.wrapper.jdbc.redshift_wrapper.JDBCConnectionWrapper.get_resolved_connection"
    )
    def test_get_resolved_connection_with_existing_tempformat(self, mock_super_get_resolved):
        """Test get_resolved_connection when tempformat is already set."""
        # Mock parent method return
        mock_super_get_resolved.return_value = {
            ConnectionObjectKey.CONNECTION_TYPE: "redshift",
            ConnectionObjectKey.SPARK_PROPERTIES: {
                SparkOptionsKey.URL: "jdbc:redshift://cluster.region.redshift.amazonaws.com:5439/db",
                SparkOptionsKey.USER: "testuser",
                SparkOptionsKey.PASSWORD: "testpass",
                SparkOptionsKey.TEMPFORMAT: RedshiftOptionValues.PARQUET_FORMAT,
            },
        }

        mock_input = Mock()
        mock_input.additional_options.items.return_value = []
        wrapper = RedshiftJDBCConnectionWrapper(mock_input)
        result = wrapper.get_resolved_connection()

        # Should not override existing tempformat
        spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
        self.assertEqual(
            spark_props[SparkOptionsKey.TEMPFORMAT], RedshiftOptionValues.PARQUET_FORMAT
        )
        self.assertEqual(
            spark_props[SparkOptionsKey.FORWARD_SPARK_S3_CREDENTIALS],
            RedshiftOptionValues.TRUE,
        )

    @patch(
        "sagemaker_studio.connections.glue_connection_lib.connections.wrapper.jdbc.redshift_wrapper.JDBCConnectionWrapper.get_resolved_connection"
    )
    def test_get_resolved_connection_incomplete_temp_credentials(self, mock_super_get_resolved):
        """Test get_resolved_connection when temp credentials are incomplete."""
        # Mock parent method return with only partial temp credentials
        mock_super_get_resolved.return_value = {
            ConnectionObjectKey.CONNECTION_TYPE: "redshift",
            ConnectionObjectKey.SPARK_PROPERTIES: {
                SparkOptionsKey.URL: "jdbc:redshift://cluster.region.redshift.amazonaws.com:5439/db",
                SparkOptionsKey.USER: "testuser",
                SparkOptionsKey.PASSWORD: "testpass",
                SparkOptionsKey.TEMPORARY_AWS_ACCESS_KEY_ID: "AKIAIOSFODNN7EXAMPLE",
                # Missing secret key and session token
            },
        }

        mock_input = Mock()
        mock_input.additional_options.items.return_value = []
        wrapper = RedshiftJDBCConnectionWrapper(mock_input)
        result = wrapper.get_resolved_connection()

        # Should add forward_spark_s3_credentials since temp credentials are incomplete
        spark_props = result[ConnectionObjectKey.SPARK_PROPERTIES]
        self.assertEqual(
            spark_props[SparkOptionsKey.FORWARD_SPARK_S3_CREDENTIALS],
            RedshiftOptionValues.TRUE,
        )
        self.assertEqual(spark_props[SparkOptionsKey.TEMPFORMAT], RedshiftOptionValues.AVRO_FORMAT)


class TestRedshiftAdditionalOptionsValidation(unittest.TestCase):
    """Test cases for Redshift additional options validation."""

    def test_redshift_wrapper_creation_with_valid_dbuser(self):
        """Test Redshift wrapper creation with valid DbUser additional option."""
        connection = {
            "Name": "redshift-connection",
            "ConnectionType": "redshift",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:redshift://cluster:5439/db",
                "USERNAME": "testuser",
                "PASSWORD": "testpass",
            },
        }

        valid_options = {"DbUser": "validuser123"}

        # Should create successfully
        inputs = GlueConnectionWrapperInputs(
            connection=connection,
            additional_options=valid_options,
            kms_client=Mock(),
            secrets_manager_client=Mock(),
        )

        wrapper = RedshiftJDBCConnectionWrapper(inputs)
        self.assertIsInstance(wrapper, RedshiftJDBCConnectionWrapper)

    def test_redshift_wrapper_creation_with_malicious_dbuser_fails(self):
        """Test Redshift wrapper creation fails with malicious DbUser additional option."""
        connection = {
            "Name": "redshift-connection",
            "ConnectionType": "redshift",
            "ConnectionProperties": {
                "JDBC_CONNECTION_URL": "jdbc:redshift://cluster:5439/db",
            },
        }

        malicious_options = {"DbUser": "user&malicious=param"}

        # Should raise ValueError during inputs creation due to validation
        with self.assertRaises(ValueError) as context:
            GlueConnectionWrapperInputs(
                connection=connection,
                additional_options=malicious_options,
                kms_client=Mock(),
                secrets_manager_client=Mock(),
            )

        self.assertIn("Invalid value", str(context.exception))


if __name__ == "__main__":
    unittest.main()
