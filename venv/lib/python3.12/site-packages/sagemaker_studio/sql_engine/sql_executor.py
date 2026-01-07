import logging
from typing import Any, Dict, List, Optional, Type, Union

from pandas import DataFrame
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .athena_transformer import AthenaTransformer
from .big_query_transformer import BigQueryTransformer
from .database_resource import DatabaseResource
from .database_transformer import DatabaseTransformer
from .dynamodb_transformer import DynamoDBTransformer
from .mssql_transformer import MSSQLTransformer
from .mysql_transformer import MySQLTransformer
from .postgresql_transformer import PostgreSQLTransformer
from .redshift_transformer import RedshiftTransformer
from .resource_fetching_definition import FetchMode, SQLAlchemyMetadataAction
from .snowflake_transformer import SnowflakeTransformer


class SqlExecutor:
    def __init__(self):
        self._transformer_classes: Dict[str, Type[DatabaseTransformer]] = {
            "REDSHIFT": RedshiftTransformer,
            "ATHENA": AthenaTransformer,
            "MYSQL": MySQLTransformer,
            "SNOWFLAKE": SnowflakeTransformer,
            "BIGQUERY": BigQueryTransformer,
            "DYNAMODB": DynamoDBTransformer,
            "SQLSERVER": MSSQLTransformer,
            "POSTGRESQL": PostgreSQLTransformer,
        }

    def get_supported_connection_types(self) -> list[str]:
        """
        Returns the supported connection types as a list of strings.
        """
        return [str(key) for key in self._transformer_classes.keys()]

    def create_engine(self, connection_type: str, connection_data: Dict[str, Any]) -> Engine:
        """Create SQLAlchemy engine based on connection type and data."""
        if connection_type not in self._transformer_classes:
            raise ValueError(f"Unsupported connection type: {connection_type}")

        transformer = self._transformer_classes[connection_type]
        [
            logging.getLogger(logger_name).setLevel(logging.WARNING)
            for logger_name in transformer.get_loggers()
        ]  # Set loggers to warn

        config = transformer.to_sqlalchemy_config(connection_data)

        if "connection_string" not in config:
            raise ValueError(
                f"Transformer for {connection_type} must return 'connection_string' in config"
            )

        connect_args = config.get("connect_args", {})
        return create_engine(config["connection_string"], connect_args=connect_args)

    def execute(
        self,
        engine: Engine,
        query: str,
        parameters: Optional[Union[Dict[str, Any], List[str]]] = None,
    ) -> Union[DataFrame, int]:
        """Execute SQL query with optional parameters using provided engine.

        Returns:
            Union[DataFrame, int]: DataFrame for SELECT queries, row count for non-SELECT queries.

        Raises:
            SQLAlchemyError: For database-specific errors (table exists, syntax errors, etc.)
        """
        try:
            with engine.connect() as conn:
                result = conn.execute(text(query), parameters or {})

                # Check if query returns results (SELECT, SHOW, DESCRIBE, etc.)
                if result.returns_rows:
                    return DataFrame(result.fetchall(), columns=result.keys())
                else:
                    # For INSERT, UPDATE, DELETE, etc. - return affected row count
                    return result.rowcount
        except SQLAlchemyError:
            # Re-raise SQLAlchemy errors with original database error details
            raise

    def get_resources(
        self,
        engine: Engine,
        connection_type: str,
        resource_type: Optional[str],
        parents: Dict[str, str],
    ) -> List[DatabaseResource]:
        """
        Fetch database resources (databases, schemas, tables, or columns).

        This function delegates to a driver-specific SQL helper to obtain a
        `ResourceFetchingDefinition`, then either:
          * uses SQLAlchemy's Inspector to read metadata (schemas/tables/columns), or
          * executes the provided SQL and reads the first column of the result.

        The returned `DatabaseResource` instances use `resource_type` if provided;
        otherwise the helper's `default_type`. Child resource kinds are taken from
        the helper's definition.

        Args:
          resource_type: The kind of resource to fetch. Expected values include
            `"DATABASE"`, `"SCHEMA"`, `"TABLE"`, `"COLUMN"`. If `None`, the helper’s
            `default_type` is used.
          parents: Mapping of required parent identifiers, depending on
            `resource_type`. Typical expectations:
              * `"SCHEMA"`: `{"DATABASE": "<db>"}`.
              * `"TABLE"`: `{"DATABASE": "<db>", "SCHEMA": "<schema>"}`.
              * `"COLUMN"`: `{"DATABASE": "<db>", "SCHEMA": "<schema>", "TABLE": "<table>"}`.
            Exact keys/requirements are determined by the SQL helper’s
            `get_resources_action`.
          connection_id: Optional identifier of the connection to use.
          connection_name: Optional human-friendly name of the connection to use.
          **kwargs: Extra options forwarded to `get_engine`, `_get_connection`, and
            the SQL execution helper (e.g., execution options).

        Returns:
          A list of `DatabaseResource` objects, one per discovered resource name.

        Raises:
          ValueError: If the helper returns an unsupported fetching mode or an
            unsupported SQLAlchemy metadata action.
        """
        if connection_type not in self._transformer_classes:
            raise ValueError(f"Unsupported connection type: {connection_type}")

        transformer = self._transformer_classes[connection_type]

        definition = transformer.get_resources_action(resource_type, parents)

        if definition.mode is FetchMode.SQLALCHEMY_METADATA:
            inspector = inspect(engine)
            action = definition.sqlalchemy_action

            if action is SQLAlchemyMetadataAction.GET_SCHEMA_NAMES:
                resource_names = inspector.get_schema_names()

            elif action is SQLAlchemyMetadataAction.GET_TABLE_NAMES:
                schema = DatabaseTransformer.get_required_resource_parent(parents, "DATABASE")
                resource_names = inspector.get_table_names(schema=schema)

            elif action is SQLAlchemyMetadataAction.GET_COLUMN_NAMES:
                schema = DatabaseTransformer.get_required_resource_parent(parents, "DATABASE")
                table = DatabaseTransformer.get_required_resource_parent(parents, "TABLE")
                columns = inspector.get_columns(table_name=table, schema=schema)
                resource_names = [c["name"] for c in columns]

            else:
                raise ValueError(f"Unsupported SQLAlchemy metadata action: {action}")

        elif definition.mode is FetchMode.SQL_EXECUTION:
            # definition.sql is guaranteed by __post_init__
            result_df = self.execute(engine, definition.sql, definition.sql_parameters)
            resource_names = (
                []
                if result_df is None or result_df.shape[1] < 1
                else result_df.iloc[:, 0].astype(str).tolist()
            )
        else:
            raise ValueError(f"Unsupported resource fetching mode: {definition.mode}")

        kind = resource_type if resource_type is not None else definition.default_type
        return [DatabaseResource(name, kind, list(definition.children)) for name in resource_names]
