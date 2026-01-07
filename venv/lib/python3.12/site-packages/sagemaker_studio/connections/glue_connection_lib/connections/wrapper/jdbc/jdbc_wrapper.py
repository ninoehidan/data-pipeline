"""
JDBC Connection Wrapper Implementation.
"""

import logging
from typing import Any, Dict

from ...constants import (
    POSTGRESQL,
    POSTGRESQL_DRIVER,
    ConnectionObjectKey,
    ConnectionPropertyKey,
    SparkOptionsKey,
)
from ...utils.jdbc_connection_properties import JdbcConnectionProperties
from ...utils.jdbc_url import JdbcUrl
from ...utils.jdbc_url_update_helper import JDBCUrlUpdateHelper
from ...utils.jdbc_vendor import JdbcVendor
from ...utils.utils import is_legacy_connection
from ..glue_connection_wrapper import GlueConnectionWrapper

logger = logging.getLogger(__name__)


class JDBCConnectionWrapper(GlueConnectionWrapper):
    """
    JDBC connection wrapper for database connections.
    """

    def get_resolved_connection(self) -> Dict[str, Any]:
        """Get connection with resolved JDBC spark properties."""
        # Get JDBC configuration
        jdbc_conf = self.get_jdbc_conf()
        spark_options = jdbc_conf.as_map()

        # SSL related options
        if spark_options.get(SparkOptionsKey.CUSTOM_JDBC_CERT) or spark_options.get(
            SparkOptionsKey.CUSTOM_JDBC_CERT_STRING
        ):
            raise ValueError("Custom JDBC cert is not supported for spark dataframe.")

        # Remove SSL cert options
        spark_options.pop(SparkOptionsKey.CUSTOM_JDBC_CERT, None)
        spark_options.pop(SparkOptionsKey.CUSTOM_JDBC_CERT_STRING, None)
        spark_options.pop(SparkOptionsKey.SKIP_CUSTOM_JDBC_CERT_VALIDATION, None)

        if spark_options.get(SparkOptionsKey.ENFORCE_SSL, "").lower() == "true":
            logger.debug(
                "enforceSSL = true, from connection properties, will only attempt SSL with CN matching"
            )

            # Get vendor string
            if is_legacy_connection(self._connection):
                jdbc_vendor_string = self._get_vendor_string()
            else:
                jdbc_vendor_string = self._connection.get(
                    ConnectionObjectKey.CONNECTION_TYPE, ""
                ).lower()

            # Set SSL properties
            jdbc_vendor = JdbcVendor.from_string(jdbc_vendor_string)
            jdbc_props = JdbcConnectionProperties[jdbc_vendor.name]
            ssl_properties = jdbc_props.get_ssl_with_dn_match_properties()
            spark_options.update(ssl_properties)

        logger.debug("updating jdbc urls.")

        # Update URL in properties
        spark_options_after_url_update = JDBCUrlUpdateHelper.update_url_in_props(
            self._connection.get(ConnectionObjectKey.CONNECTION_TYPE, ""),
            spark_options[SparkOptionsKey.FULL_URL],
            spark_options,
            self._additional_options,
        )

        # Remove enforceSSL from final options
        spark_options_after_url_update.pop(SparkOptionsKey.ENFORCE_SSL, None)

        # Add driver options
        driver_options = self._get_driver_options(
            self._connection.get(ConnectionObjectKey.CONNECTION_TYPE, "").lower()
        )
        final_spark_options = {**spark_options_after_url_update, **driver_options}

        # Ensure url matches fullUrl
        full_url = final_spark_options.get(SparkOptionsKey.FULL_URL)
        if full_url:
            final_spark_options[SparkOptionsKey.URL] = full_url

        # Create resolved connection by adding SparkProperties to original connection
        self._connection[ConnectionObjectKey.SPARK_PROPERTIES] = final_spark_options

        return self._connection

    def _get_vendor_string(self) -> str:
        """Get vendor string from JDBC URL."""
        connection_props = self._connection.get(ConnectionObjectKey.CONNECTION_PROPERTIES, {})
        full_url = connection_props.get(ConnectionPropertyKey.JDBC_CONNECTION_URL)

        if not full_url:
            connection_type = self._connection.get(ConnectionObjectKey.CONNECTION_TYPE, "")
            raise ValueError(
                f"JDBC_CONNECTION_URL should not be empty or null for JDBC based connection type: {connection_type}"
            )

        jdbc_url = JdbcUrl.from_url(full_url)
        return jdbc_url.get_vendor().value

    def _get_driver_options(self, connection_type: str) -> Dict[str, str]:
        """Get driver options based on connection type."""
        if connection_type == POSTGRESQL:
            return {"driver": POSTGRESQL_DRIVER}
        return {}
