import logging
from typing import Any, Dict, List, Optional, Union

from sagemaker_studio.connections.helper_factory import HelperFactory
from sagemaker_studio.project import Project

logger = logging.getLogger()
logger.info("Importing sqlutils")

_project = None
_duckdb = None
_sql_executor = None


def sql(
    query: str,
    parameters: Optional[Union[Dict[str, Any], List[str]]] = None,
    connection_id: Optional[str] = None,
    connection_name: Optional[str] = None,
    **kwargs,
):
    """
    Executes a SQL query on the specified connection and returns the result as a DataFrame.

    Args:
        query (str): The SQL query to execute.
        parameters (Optional[Union[Dict[str, Any], List[str]]]): Optional parameters for the query.
        connection_id (Optional[str]): The ID of the DataZone connection to use for the query.
        connection_name (Optional[str]): The name of the DataZone connection to use for the query.

    Returns:
        DataFrame: The result of the SQL query as a DataFrame.

    Raises:
        RuntimeError: If Project is not initialized when using connection_name or if there's an error executing the SQL query.
    """

    engine = get_engine(connection_id, connection_name, **kwargs)
    if engine:
        return _ensure_sql_executor().execute(engine, query, parameters)
    else:
        # Execute query locally using DuckDB if no connection specified
        return (lambda x: x.df() if x else None)(_ensure_duckdb().sql(query))


def get_engine(
    connection_id: Optional[str] = None, connection_name: Optional[str] = None, **kwargs
):
    """
    Returns the SQL engine for the specified connection.

    Args:
        connection_id (Optional[str]): The ID of the DataZone connection to get the SQL engine for.
        connection_name (Optional[str]): The name of the DataZone connection to get the SQL engine for.

    Returns:
        The SQL engine instance for executing queries.

    Raises:
        ValueError: If multiple connection parameters are provided
        RuntimeError: If project initialization fails or if SQL is not supported for this connection type.
    """

    provided_params = sum(x is not None for x in [connection_id, connection_name])
    if provided_params == 0:
        # No connection provided, use local DuckDB engine
        return None
    if provided_params > 1:
        raise ValueError("Only one of connection_id or connection_name should be provided")

    project = _ensure_project()
    if not project:
        raise RuntimeError("Project is not initialized.")

    # Need to handle connection_id case
    if connection_name:
        connection = project.connection(connection_name)
    elif connection_id:
        connection = project.connection(id=connection_id)

    sql_executor = _ensure_sql_executor()

    if connection.type not in sql_executor.get_supported_connection_types():
        raise RuntimeError(
            f"SQL is not supported for connection type {connection.type}. Supported types are { ', '.join(sql_executor.get_supported_connection_types())}."
        )

    sql_helper = HelperFactory.get_sql_helper(connection.type)
    connection_config = sql_helper.to_sql_config(connection, **kwargs)

    return sql_executor.create_engine(connection.type, connection_config)


def _ensure_project():
    """Initialize Project on demand"""
    global _project
    if _project is None:
        try:
            _project = Project()
        except Exception:
            _project = False
    return _project


def _ensure_duckdb():
    """Initialize Project on demand"""
    global _duckdb
    if _duckdb is None:
        import duckdb as _duckdb

        # Refer to https://duckdb.org/duckdb-docs.pdf
        _duckdb.sql("SET python_scan_all_frames = true;")
        # Refer to https://duckdb.org/docs/stable/core_extensions/httpfs/s3api#credential_chain-provider
        _duckdb.sql("CREATE SECRET (TYPE s3, PROVIDER credential_chain);")
    return _duckdb


def _ensure_sql_executor():
    """Initialize Project on demand"""
    global _sql_executor
    if _sql_executor is None:
        from sagemaker_studio.sql_engine.sql_executor import SqlExecutor

        _sql_executor = SqlExecutor()
    return _sql_executor


logger.info("Finished importing sqlutils")
