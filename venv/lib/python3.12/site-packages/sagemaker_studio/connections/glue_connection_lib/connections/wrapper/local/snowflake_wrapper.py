"""
Snowflake Connection Wrapper Implementation.
"""

from typing import Any, Dict

from .native_wrapper import NativeConnectionWrapper


class SnowflakeConnectionWrapper(NativeConnectionWrapper):
    """
    Snowflake connection wrapper that extends native wrapper functionality.

    Removes conflicting database/schema/warehouse options that cause issues
    with the Snowflake Spark connector when both DATABASE and sfDatabase
    are defined simultaneously.
    """

    def get_resolved_connection(self) -> Dict[str, Any]:
        """Get connection with resolved Snowflake spark properties."""
        # Get the base resolved connection
        resolved_connection = super().get_resolved_connection()

        # Combine options by removing conflicting keys
        if "SparkProperties" in resolved_connection:
            resolved_connection["SparkProperties"] = self._combine_options(
                resolved_connection["SparkProperties"]
            )

        return resolved_connection

    def _combine_options(self, options_map: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove conflicting options for Snowflake connector.

        The Snowflake spark connector complains when DATABASE and sfDatabase
        are defined at the same time in the options.

        Args:
            options_map: Original options dictionary

        Returns:
            Updated options dictionary with conflicting keys removed
        """
        # Remove conflicting keys
        options_map.pop("DATABASE", None)
        options_map.pop("SCHEMA", None)
        options_map.pop("WAREHOUSE", None)

        return options_map
