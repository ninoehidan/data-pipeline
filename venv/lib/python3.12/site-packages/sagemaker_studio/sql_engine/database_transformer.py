from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from sagemaker_studio.sql_engine.resource_fetching_definition import (
    ResourceFetchingDefinition,
    SQLAlchemyMetadataAction,
)


class DatabaseTransformer(ABC):
    """
    Abstract base class for database connection transformers.

    This class defines the interface for transforming connection configurations
    into SQLAlchemy-compatible formats. Each concrete implementation handles
    a specific database type and its connection requirements.
    """

    @staticmethod
    @abstractmethod
    def get_required_fields() -> List[str]:
        """
        Get the list of required fields for this database connection type.

        Returns:
            List[str]: List of field names that must be present in the
                connection data for successful transformation.

        Raises:
            NotImplementedError: Must be implemented by concrete subclasses.
        """

    @staticmethod
    def get_loggers() -> List[str]:
        """
        Get the list of loggers used for this database connection type.

        Returns:
            List[str]: List of loggers that are used for this database connection type.
        """
        return []

    @staticmethod
    @abstractmethod
    def to_sqlalchemy_config(connection_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform connection data into SQLAlchemy configuration.

        Converts database-specific connection parameters into a format
        suitable for SQLAlchemy engine creation, including connection
        strings and connection arguments.

        Args:
            connection_data (Dict[str, Any]): Raw connection configuration data.

        Returns:
            Dict[str, Any]: SQLAlchemy configuration dictionary containing:
                - connection_string: SQLAlchemy-compatible connection string
                - connect_args: Additional connection arguments (optional)

        Raises:
            NotImplementedError: Must be implemented by concrete subclasses.
            ValueError: If required fields are missing from connection_data.
        """

    @staticmethod
    def validate_required_fields(
        required_fields: List[str], connection_data: Dict[str, Any]
    ) -> None:
        """
        Validate that all required fields are present in connection data.

        Args:
            required_fields (List[str]): List of field names that must be present.
            connection_data (Dict[str, Any]): Connection data to validate.

        Raises:
            ValueError: If any required field is missing or empty in connection_data.
        """
        for field in required_fields:
            if not connection_data.get(field):
                raise ValueError(f"{field} is required for connection")

    @staticmethod
    @abstractmethod
    def get_resources_action(
        resource_type: Optional[str], parents: Optional[Dict[str, str]] = None
    ) -> ResourceFetchingDefinition:
        """
        Build a definition for metadata-based resource discovery.

        Returns a `ResourceFetchingDefinition` configured to use SQLAlchemy’s
        Inspector for listing resources, based on the requested `resource_type`.
        If `resource_type` is `None`, it defaults to the database level.

        This method does **not** read `parents`; any required parent context
        (e.g., schema when listing tables) is supplied later by the consumer
        when executing the definition.

        Args:
          resource_type: Which level to discover. Supported values:
            `"DATABASE"`, `"TABLE"`, `"COLUMN"`. If `None`, treated as `"DATABASE"`.
          parents: Optional mapping of parent identifiers. Ignored here, kept
            for syntax purposes.

        Returns:
          A `ResourceFetchingDefinition` in SQLAlchemy-metadata mode with:
            - `GET_TABLE_NAMES` for `"TABLE"` (children: `("COLUMN",)`),
            - `GET_COLUMN_NAMES` for `"COLUMN"` (children: `()`),
            - `GET_SCHEMA_NAMES` for `"DATABASE"` or `None` (children: `("TABLE",)`).

        Raises:
          ValueError: If `resource_type` is not one of the supported values.
        """
        match resource_type:
            case "TABLE":
                return ResourceFetchingDefinition.from_sqlalchemy_metadata(
                    SQLAlchemyMetadataAction.GET_TABLE_NAMES,
                    default_type="TABLE",
                    children=("COLUMN",),
                )
            case "COLUMN":
                return ResourceFetchingDefinition.from_sqlalchemy_metadata(
                    SQLAlchemyMetadataAction.GET_COLUMN_NAMES,
                    default_type="COLUMN",
                    children=(),
                )
            case "DATABASE" | None:
                return ResourceFetchingDefinition.from_sqlalchemy_metadata(
                    SQLAlchemyMetadataAction.GET_SCHEMA_NAMES,
                    default_type="DATABASE",
                    children=("TABLE",),
                )
            case other:
                raise ValueError(f"Unsupported resource type: {other!r}")

    @staticmethod
    def get_required_resource_parent(parents: dict, required_type: str):
        """
        Return a required parent identifier from a mapping.

        Ensures the given parent resource (e.g., `"DATABASE"`, `"SCHEMA"`, `"TABLE"`)
        is present in the `parents` mapping used to scope resource discovery. If the
        key is missing, a clear `KeyError` is raised.

        Args:
          parents: Mapping of parent resource kinds to their identifiers
            (e.g., `{"DATABASE": "dev", "SCHEMA": "public"}`).
          required_type: The required parent key to look up (e.g., `"SCHEMA"`).

        Returns:
          The identifier associated with `parent`.

        Raises:
          KeyError: If `parent` is not found in `d`.
        """
        if parents is None:
            return None
        elif required_type in parents:
            return parents[required_type]
        else:
            raise KeyError(f"Required parent type '{required_type}' not found in provided parents.")
