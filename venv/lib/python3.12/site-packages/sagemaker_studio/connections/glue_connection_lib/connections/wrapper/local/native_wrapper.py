"""
Native Connection Wrapper Implementation.
"""

import json
from typing import Any, Dict

from ...constants import CONNECTOR_TYPE, ConnectionObjectKey
from ...utils.secret_key_update_helper import get_connection_specific_secret_map
from ...utils.utils import get_connection_properties, is_legacy_connection
from ..glue_connection_wrapper import GlueConnectionWrapper


class NativeConnectionWrapper(GlueConnectionWrapper):
    """
    Native connection wrapper for non-JDBC connections.
    """

    def get_resolved_connection(self) -> Dict[str, Any]:
        """Get connection with resolved native spark properties."""
        connection_type_lower = self._connection.get(
            ConnectionObjectKey.CONNECTION_TYPE, ""
        ).lower()

        # Get connection properties
        connection_properties = get_connection_properties(self._connection)

        if is_legacy_connection(self._connection):
            # Determine catalog property key based on connection type
            catalog_property_key = None
            for key, values in CONNECTOR_TYPE.items():
                if connection_type_lower in values:
                    if key == "spark":
                        catalog_property_key = "SparkProperties"
                    elif key == "jdbc":
                        catalog_property_key = "JDBCProperties"
                    break

            if catalog_property_key is None:
                raise ValueError(f"Invalid Connector Type: {connection_type_lower}")

            if catalog_property_key in connection_properties:
                option_map = json.loads(connection_properties[catalog_property_key])
            else:
                option_map = {}

            # Fill out credentials from secrets manager
            self._fill_credentials_from_secret_manager(option_map, connection_type_lower)
            option_map.pop("secretId", None)
        else:
            # For V2 connections, use connection properties directly
            option_map = connection_properties

            # Fill out credentials from secrets manager
            self._fill_credentials_from_secret_manager(option_map, connection_type_lower)

        # Add driver options
        driver_options = self.get_driver_options(connection_type_lower)
        final_options = {**option_map, **driver_options}

        # Add SparkProperties to the original connection
        self._connection[ConnectionObjectKey.SPARK_PROPERTIES] = final_options

        return self._connection

    def _get_secret_options_from_secret_manager(self, secret_id: str) -> Dict[str, str]:
        """
        Get secret options from AWS Secrets Manager.

        Args:
            secret_id: The secret ID to retrieve

        Returns:
            Dictionary containing secret key-value pairs
        """
        try:
            response = self._secrets_manager_client.get_secret_value(SecretId=secret_id)  # type: ignore
            secret_string = response["SecretString"]
            return json.loads(secret_string)
        except Exception as e:
            raise ValueError(f"Failed to retrieve or parse secret '{secret_id}': {str(e)}")

    def _fill_credentials_from_secret_manager(
        self, option_map: Dict[str, Any], connection_type_lower: str
    ) -> None:
        """Fill out credentials from secrets manager if secretId is present."""
        if "secretId" in option_map:
            # Extract authentication type from connection
            auth_config = self._connection.get(ConnectionObjectKey.AUTHENTICATION_CONFIGURATION, {})
            auth_type = auth_config.get("AuthenticationType")

            secret_map = get_connection_specific_secret_map(
                self._get_secret_options_from_secret_manager(option_map["secretId"]),
                connection_type_lower,
                auth_type,
            )
            option_map.update(secret_map)

    @staticmethod
    def get_driver_options(connection_type: str) -> Dict[str, str]:
        """
        Get driver options for specific connection types.

        Args:
            connection_type: The connection type

        Returns:
            Dictionary containing driver options
        """
        connection_type_lower = connection_type.lower()
        if connection_type_lower == "teradata":
            return {"driver": "com.teradata.jdbc.TeraDriver"}
        elif connection_type_lower == "saphana":
            return {"driver": "com.sap.db.jdbc.Driver"}
        else:
            return {}
