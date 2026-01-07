import logging

from sagemaker_studio.project import ClientConfig, Project

logger = logging.getLogger()
logger.info("Importing sparkutils")

# Check if PySpark is available
try:
    from sagemaker_studio.utils.spark.session.athena.athena_spark_session_manager import (
        AthenaSparkSessionManager,
    )
    from sagemaker_studio.utils.spark.session.lazy_spark_session import LazySparkSession

    _SPARK_AVAILABLE = True
except ImportError:
    _SPARK_AVAILABLE = False

_project = None
_DEFAULT_SPARK_CONNECT_CONNECTION_NAME = "serverless.spark"


def init(connection_name: str = None, config: ClientConfig = ClientConfig()):
    if not _SPARK_AVAILABLE:
        raise RuntimeError("PySpark is not available.")

    _session_manager = AthenaSparkSessionManager(connection_name, config)
    return LazySparkSession(_session_manager)


def get_spark_options(connection_name: str):
    """Get Spark options for a connection."""
    project = _ensure_project()

    if not project:
        raise RuntimeError("Project is not initialized.")

    connection = project.connection(connection_name)
    return connection._spark_options()


def _ensure_project():
    """Initialize Project on demand"""
    global _project
    if _project is None:
        _project = Project()
    return _project


logger.info("Finished importing sparkutils")
