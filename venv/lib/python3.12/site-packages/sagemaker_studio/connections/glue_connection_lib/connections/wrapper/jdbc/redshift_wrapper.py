"""
Redshift JDBC Connection Wrapper Implementation.
"""

from typing import Any, Dict

from ...constants import ConnectionObjectKey, RedshiftOptionValues, SparkOptionsKey
from .jdbc_wrapper import JDBCConnectionWrapper


class RedshiftJDBCConnectionWrapper(JDBCConnectionWrapper):
    """
    Redshift-specific JDBC connection wrapper.
    """

    def get_resolved_connection(self) -> Dict[str, Any]:
        """Get connection with resolved JDBC spark properties for Redshift."""
        # Get the base resolved connection from parent
        resolved_connection = super().get_resolved_connection()

        # Apply Redshift-specific options
        spark_properties = resolved_connection.get(ConnectionObjectKey.SPARK_PROPERTIES, {})
        combined_options = self._combine_options(spark_properties)
        resolved_connection[ConnectionObjectKey.SPARK_PROPERTIES] = combined_options

        return resolved_connection

    def _combine_options(self, options_map: Dict[str, str]) -> Dict[str, str]:
        """Combine options with Redshift-specific defaults."""
        combined_options = options_map.copy()

        # If aws_iam_role or temporary aws credentials are not passed in the options,
        # set forward_spark_s3_credentials to true
        has_iam_role = SparkOptionsKey.AWS_IAM_ROLE in combined_options
        has_temp_credentials = (
            SparkOptionsKey.TEMPORARY_AWS_ACCESS_KEY_ID in combined_options
            and SparkOptionsKey.TEMPORARY_AWS_SECRET_ACCESS_KEY in combined_options
            and SparkOptionsKey.TEMPORARY_AWS_SESSION_TOKEN in combined_options
        )

        if not (has_iam_role or has_temp_credentials):
            combined_options[SparkOptionsKey.FORWARD_SPARK_S3_CREDENTIALS] = (
                RedshiftOptionValues.TRUE
            )

        # Set default tempformat if not present
        if SparkOptionsKey.TEMPFORMAT not in combined_options:
            combined_options[SparkOptionsKey.TEMPFORMAT] = RedshiftOptionValues.AVRO_FORMAT

        return combined_options
