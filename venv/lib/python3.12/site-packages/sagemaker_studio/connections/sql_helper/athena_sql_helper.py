import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from sagemaker_studio.connections.connection import Connection
from sagemaker_studio.connections.sql_helper.sql_helper import SqlHelper
from sagemaker_studio.exceptions import AWSClientException


class AthenaSqlHelper(SqlHelper):
    """
    SQL helper for Amazon Athena connections.

    This class transforms DataZone Athena connection data into a standardized format
    for SQL interface consumption. It handles Athena-specific configuration
    including workgroup settings, S3 staging directories, and AWS credentials.
    """

    @staticmethod
    def to_sql_config(connection: Connection, **kwargs) -> Dict[str, Any]:
        """
        Transform DataZone Athena connection data into SQL interface configuration.

        Extracts Athena-specific parameters including region, workgroup, S3 staging directory,
        and AWS credentials from the DataZone connection data and formats them for SQL interface use.

        Returns:
            Dict[str, Any]: Configuration dictionary containing:
                - region: AWS region for Athena service
                - work_group: Athena workgroup name
                - s3_staging_dir: S3 location for query results
                - aws_access_key_id: AWS access key
                - aws_secret_access_key: AWS secret key
                - aws_session_token: AWS session token (if present)

        Raises:
            RuntimeError: If S3 staging directory cannot be retrieved or is not configured.
        """
        connection_data = SqlHelper.get_connection_data(connection)
        physical_endpoints = connection_data["physical_endpoints"]
        aws_location = physical_endpoints[0].get("awsLocation", {})
        region = aws_location.get("awsRegion")
        work_group = connection_data["workgroup_name"]
        s3_staging_dir = AthenaSqlHelper._get_s3_staging_dir(work_group, region)
        connection_creds = connection_data["connection_creds"]
        catalog_name = kwargs.get("catalog_name")
        schema_name = kwargs.get("schema_name")

        config = {
            "region": region,
            "work_group": work_group,
            "s3_staging_dir": s3_staging_dir,
            "aws_access_key_id": connection_creds.get("access_key_id"),
            "aws_secret_access_key": connection_creds.get("secret_access_key"),
        }

        if connection_creds.get("session_token"):
            config["aws_session_token"] = connection_creds.get("session_token")
        if catalog_name:
            config["catalog_name"] = catalog_name
        if schema_name:
            config["schema_name"] = schema_name

        return config

    @staticmethod
    def _get_s3_staging_dir(work_group: str, region: str) -> str:
        """
        Retrieve the S3 staging directory for the specified Athena workgroup.

        Args:
            work_group (str): Name of the Athena workgroup.
            region (str): AWS region where the workgroup is located.

        Returns:
            str: S3 URI of the workgroup's result output location.

        Raises:
            RuntimeError: If the workgroup cannot be accessed or S3 staging directory
                is not configured for the workgroup.
        """
        try:
            client = boto3.client("athena", region_name=region)
            response = client.get_work_group(WorkGroup=work_group)
            return response["WorkGroup"]["Configuration"]["ResultConfiguration"]["OutputLocation"]
        except ClientError as e:
            logging.warning(
                f"Failed to get S3 staging directory for workgroup {work_group}: {AWSClientException(e)}"
            )
            raise RuntimeError(
                f"Failed to get S3 staging directory for workgroup {work_group}: {e}"
            )
        except KeyError as e:
            logging.warning(
                f"S3 staging directory not configured for workgroup {work_group}: {AWSClientException(e)}"
            )
            raise RuntimeError(
                f"S3 staging directory not configured for workgroup {work_group}: {e}"
            )
