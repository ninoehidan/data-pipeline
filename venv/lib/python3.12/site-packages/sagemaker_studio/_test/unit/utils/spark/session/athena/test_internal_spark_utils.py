import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock Project class before any imports to prevent Domain ID error
with patch("sagemaker_studio.Project"):

    # Mock pyspark before importing  # noqa: E402
    sys.modules["pyspark"] = Mock()
    sys.modules["pyspark.sql"] = Mock()
    sys.modules["pyspark.sql.connect"] = Mock()
    sys.modules["pyspark.sql.connect.session"] = Mock()
    sys.modules["pyspark.sql.connect.client"] = Mock()

    pyspark_modules = [
        "pyspark",
        "pyspark.sql",
        "pyspark.sql.session",
        "pyspark.sql.connect",
        "pyspark.sql.connect.session",
        "pyspark.sql.connect.client",
        "grpc",
        "pyspark.errors",
        "pyspark.errors.exceptions",
        "pyspark.errors.exceptions.connect",
    ]

    for module_name in pyspark_modules:
        if module_name not in sys.modules:
            mock_module = Mock()
            if module_name == "grpc":
                # Mock gRPC specific classes and functions
                mock_module.insecure_channel = Mock()
                mock_module.secure_channel = Mock()
                mock_module.intercept_channel = Mock()
                mock_module.UnaryUnaryClientInterceptor = Mock()
                mock_module.UnaryStreamClientInterceptor = Mock()
                mock_module.StreamUnaryClientInterceptor = Mock()
                mock_module.StreamStreamClientInterceptor = Mock()
            elif module_name == "pyspark.sql.connect.client":
                mock_module.ChannelBuilder = Mock()
            sys.modules[module_name] = mock_module

    # Mock the interceptors module to avoid importing the actual interceptors
    mock_interceptors = Mock()
    mock_interceptors.CustomChannelBuilder = Mock()
    sys.modules["sagemaker_studio.utils.spark.session.athena.interceptors"] = mock_interceptors

    from sagemaker_studio.utils.spark.session.athena import internal_spark_utils


@pytest.fixture(autouse=True)
def mock_utils_and_project(monkeypatch):
    """Fixture to mock InternalUtils and Project setup."""
    mock_utils = MagicMock()
    mock_utils._get_domain_region.return_value = "us-west-2"
    mock_utils._get_datazone_stage.return_value = "prod"
    monkeypatch.setattr(internal_spark_utils, "_utils", mock_utils)
    monkeypatch.setattr(internal_spark_utils, "region", "us-west-2")
    monkeypatch.setattr(internal_spark_utils, "stage", "prod")

    mock_proj = MagicMock()
    monkeypatch.setattr(internal_spark_utils, "proj", mock_proj)
    return mock_proj


# -------------------------------------------------------------------
# Tests for _get_account_id_from_arn
# -------------------------------------------------------------------
def test_get_account_id_from_arn_valid():
    arn = "arn:aws:iam::123456789012:role/MyRole"

    assert internal_spark_utils._get_account_id_from_arn(arn) == "123456789012"


# -------------------------------------------------------------------
# Tests for _generate_spark_catalog_spark_configs
# -------------------------------------------------------------------
def test_generate_spark_catalog_spark_configs():
    configs = internal_spark_utils._generate_spark_catalog_spark_configs("999888777666")
    assert (
        configs["spark.sql.catalog.spark_catalog.catalog-impl"]
        == "org.apache.iceberg.aws.glue.GlueCatalog"
    )
    assert configs["spark.sql.catalog.spark_catalog.glue.account-id"] == "999888777666"
    assert configs["spark.sql.catalog.spark_catalog.client.region"] == "us-west-2"
    assert "spark.sql.catalog.spark_catalog" in configs


# -------------------------------------------------------------------
# Tests for _generate_s3tables_spark_configs
# -------------------------------------------------------------------
def test_generate_s3tables_spark_configs_with_federated_catalog(mock_utils_and_project):
    catalog = MagicMock()
    catalog.type = "FEDERATED"
    catalog.name = "prod_catalog"
    catalog.id = "cat-prod"
    catalog.resource_arn = "arn:aws:glue:us-west-2:123456789012:catalog/prod_catalog"
    catalog.federated_catalog = {"ConnectionName": "aws:s3tables", "Identifier": "s3://bucket/prod"}

    mock_utils_and_project.connection.return_value.catalogs = [catalog]

    conf = internal_spark_utils._generate_s3tables_spark_configs()
    assert conf["spark.sql.catalog.prod_catalog"] == "org.apache.iceberg.spark.SparkCatalog"
    assert (
        conf["spark.sql.catalog.prod_catalog.catalog-impl"]
        == "org.apache.iceberg.aws.glue.GlueCatalog"
    )
    assert conf["spark.sql.catalog.prod_catalog.glue.catalog-arn"] == catalog.resource_arn
    assert conf["spark.sql.catalog.prod_catalog.client.region"] == "us-west-2"
    assert conf["spark.sql.catalog.prod_catalog.glue.lakeformation-enabled"] == "true"
    assert conf["spark.sql.catalog.prod_catalog.glue.lakeformation-enabled"] == "true"


def test_generate_s3tables_spark_configs_ignores_non_federated(mock_utils_and_project):
    catalog = MagicMock()
    catalog.type = "OTHER"
    catalog.federated_catalog = {}
    mock_utils_and_project.connection.return_value.catalogs = [catalog]

    conf = internal_spark_utils._generate_s3tables_spark_configs()
    assert conf == {}  # no config should be generated


# -------------------------------------------------------------------
# Tests for generate_spark_configs (integration)
# -------------------------------------------------------------------
@patch(
    "sagemaker_studio.utils.spark.session.athena.internal_spark_utils._generate_spark_catalog_spark_configs",
    return_value={"a": "b"},
)
@patch(
    "sagemaker_studio.utils.spark.session.athena.internal_spark_utils._generate_s3tables_spark_configs",
    return_value={"c": "d"},
)
def test_generate_spark_configs_combines_all(mock_s3, mock_catalog):
    configs = internal_spark_utils.generate_spark_configs("999888777666")
    assert configs["a"] == "b"
    assert configs["c"] == "d"
    assert "spark.sql.catalogImplementation" in configs
