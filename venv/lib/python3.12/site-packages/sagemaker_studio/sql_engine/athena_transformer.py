from typing import Any, Dict, List, Optional

from .database_transformer import DatabaseTransformer
from .resource_fetching_definition import ResourceFetchingDefinition, SQLAlchemyMetadataAction


class AthenaTransformer(DatabaseTransformer):
    """
    Database transformer for Amazon Athena connections.

    This transformer converts Athena connection configuration into SQLAlchemy-compatible
    format using the PyAthena driver. It handles Athena-specific requirements including
    workgroup configuration and S3 staging directories.
    """

    @staticmethod
    def get_required_fields() -> List[str]:
        """
        Get required fields for Athena connections.

        Returns:
            List[str]: List containing "work_group" and "s3_staging_dir"
                as mandatory fields for Athena connections.
        """
        return ["work_group", "s3_staging_dir"]

    @staticmethod
    def to_sqlalchemy_config(connection_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Athena connection data into SQLAlchemy configuration.

        Creates a SQLAlchemy connection string using the awsathena+rest driver
        and passes all connection data as connect_args for PyAthena.

        Args:
            connection_data (Dict[str, Any]): Athena connection configuration containing
                work_group, s3_staging_dir, region, and AWS credentials.

        Returns:
            Dict[str, Any]: SQLAlchemy configuration with:
                - connection_string: awsathena+rest:// URL for the specified region
                - connect_args: Original connection_data passed to PyAthena driver

        Raises:
            ValueError: If required fields (work_group, s3_staging_dir) are missing.
        """
        AthenaTransformer.validate_required_fields(
            AthenaTransformer.get_required_fields(), connection_data
        )

        region = connection_data.get("region")

        connection_string = f"awsathena+rest://@athena.{region}.amazonaws.com"

        return {"connection_string": connection_string, "connect_args": connection_data}

    @staticmethod
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
