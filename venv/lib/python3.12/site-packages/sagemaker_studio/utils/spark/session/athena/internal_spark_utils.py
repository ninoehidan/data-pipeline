import logging

from sagemaker_studio import Project
from sagemaker_studio.utils._internal import InternalUtils

CATALOG_LIMIT = 7

_utils = InternalUtils()
region = _utils._get_domain_region()
stage = _utils._get_datazone_stage()

logger = logging.getLogger("SparkConnect")
proj = Project()

DEFAULT_SPARK_PROPS = {
    "hive.metastore.client.factory.class": "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory",
    "spark.hadoop.fs.s3.credentialsResolverClass": "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver",
    "spark.hadoop.fs.s3.useDirectoryHeaderAsFolderObject": "true",
    "spark.hadoop.fs.s3.folderObject.autoAction.disabled": "true",
    "spark.sql.catalogImplementation": "hive",
    "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    "spark.sql.catalog.createDirectoryAfterTable.enabled": "true",
    "spark.sql.catalog.dropDirectoryBeforeTable.enabled": "true",
    "spark.sql.catalog.skipLocationValidationOnCreateTable.enabled": "true",
}


def _get_account_id_from_arn(arn):
    return arn.split(":")[4]


def _generate_spark_catalog_spark_configs(account_id):
    return {
        "spark.sql.catalog.spark_catalog": "org.apache.iceberg.spark.SparkSessionCatalog",
        "spark.sql.catalog.spark_catalog.catalog-impl": "org.apache.iceberg.aws.glue.GlueCatalog",
        "spark.sql.catalog.spark_catalog.client.region": region,
        "spark.sql.catalog.spark_catalog.glue.account-id": account_id,
        "spark.sql.catalog.spark_catalog.glue.id": account_id,
        "spark.sql.catalog.spark_catalog.glue.lakeformation-enabled": "true",
    }


def _generate_s3tables_spark_configs():
    catalogs = proj.connection().catalogs
    conf = {}
    catalog_count = 0
    for catalog in catalogs:
        if catalog_count < CATALOG_LIMIT:
            if (
                catalog.type == "FEDERATED"
                and catalog.federated_catalog.get("ConnectionName") == "aws:s3tables"
            ):

                # If a catalog hierarchy looks like level_1 -> level_2 -> level_3 -> dev
                # The ParentCatalogNames list of catalog dev would be
                # index 0: level_1
                # index 1: level_2
                # index 2: level_3
                catalog_name = catalog.name
                conf[f"spark.sql.catalog.{catalog_name}"] = "org.apache.iceberg.spark.SparkCatalog"
                conf[f"spark.sql.catalog.{catalog_name}.catalog-impl"] = (
                    "org.apache.iceberg.aws.glue.GlueCatalog"
                )
                conf[f"spark.sql.catalog.{catalog_name}.warehouse"] = catalog.federated_catalog.get(
                    "Identifier"
                )
                conf[f"spark.sql.catalog.{catalog_name}.glue.id"] = catalog.id
                conf[f"spark.sql.catalog.{catalog_name}.glue.account-id"] = (
                    f"{_get_account_id_from_arn(catalog.resource_arn)}"
                )
                conf[f"spark.sql.catalog.{catalog_name}.glue.catalog-arn"] = catalog.resource_arn
                conf[f"spark.sql.catalog.{catalog_name}.client.region"] = region
                if stage == "prod":
                    conf[f"spark.sql.catalog.{catalog_name}.glue.lakeformation-enabled"] = "true"

                catalog_count += 1

    return conf


def generate_spark_configs(account_id):
    spark_props = DEFAULT_SPARK_PROPS.copy()
    spark_props.update(_generate_spark_catalog_spark_configs(account_id))
    spark_props.update(_generate_s3tables_spark_configs())
    return spark_props
