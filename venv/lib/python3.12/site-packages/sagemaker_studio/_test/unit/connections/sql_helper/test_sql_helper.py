from dataclasses import make_dataclass
from unittest.mock import patch

from sagemaker_studio.connections.sql_helper.athena_sql_helper import AthenaSqlHelper
from sagemaker_studio.connections.sql_helper.big_query_sql_helper import BigQuerySqlHelper
from sagemaker_studio.connections.sql_helper.ddb_sql_helper import DDBSQLHelper
from sagemaker_studio.connections.sql_helper.mssql_sql_helper import MSSQLHelper
from sagemaker_studio.connections.sql_helper.mysql_sql_helper import MySQLHelper
from sagemaker_studio.connections.sql_helper.postgresql_helper import PostgreSQLHelper
from sagemaker_studio.connections.sql_helper.snowflake_sql_helper import SnowflakeSqlHelper

connection = make_dataclass("Connection", ["secret", "connection_creds", "data"])(
    {"username": "admin", "password": "secret"},
    make_dataclass("ConnectionCredentials", [])(),
    make_dataclass("ConnectionData", ["physical_endpoints"])(
        [
            make_dataclass("PhysicalEndpoint", ["awsLocation", "glueConnection"])(
                awsLocation={"awsRegion": "us-east-1"},
                glueConnection=make_dataclass("GlueConnection", ["connectionProperties"])(
                    connectionProperties={
                        "DATABASE": "sales",
                        "HOST": "db.example.com",
                        "PORT": "1433",
                        "WAREHOUSE": "wh1",
                    },
                ),
            )
        ]
    ),
)

snowflake_connection = make_dataclass("Connection", ["secret", "connection_creds", "data"])(
    {"username": "admin", "password": "secret"},
    make_dataclass("ConnectionCredentials", [])(),
    make_dataclass("ConnectionData", ["physical_endpoints"])(
        [
            make_dataclass("PhysicalEndpoint", ["awsLocation", "glueConnection"])(
                awsLocation={"awsRegion": "us-east-1"},
                glueConnection=make_dataclass("GlueConnection", ["connectionProperties"])(
                    connectionProperties={
                        "DATABASE": "sales",
                        "HOST": "db.example.com.snowflakecomputing.com",
                        "PORT": "1433",
                        "WAREHOUSE": "wh1",
                    },
                ),
            )
        ]
    ),
)

athena_connection = make_dataclass("Connection", ["secret", "connection_creds", "data"])(
    {},
    make_dataclass(
        "ConnectionCredentials", ["access_key_id", "secret_access_key", "session_token"]
    )(
        access_key_id="dummy_access_key_id",
        secret_access_key="dummy_secret_access_key",
        session_token="dummy_session_token",
    ),
    make_dataclass("ConnectionData", ["physical_endpoints", "workgroup_name", "connection_creds"])(
        physical_endpoints=[
            make_dataclass("PhysicalEndpoint", ["awsLocation"])(
                awsLocation={"awsRegion": "us-east-1"}
            )
        ],
        workgroup_name="test-workgroup",
        connection_creds={
            "access_key_id": "dummy_access_key_id",
            "secret_access_key": "dummy_secret_access_key",
            "session_token": "dummy_session_token",
        },
    ),
)


def test_to_big_query_helper_sql_config_returns_secret_identity():
    result = BigQuerySqlHelper.to_sql_config(connection)
    assert result == {"password": "secret", "username": "admin"}


def test_to_ddb_helper_sql_config_returns_secret_identity():
    result = DDBSQLHelper.to_sql_config(connection)
    assert result == {"region": "us-east-1"}


def test_to_mssql_helper_sql_config_returns_secret_identity():
    result = MSSQLHelper.to_sql_config(connection)
    assert result == {
        "host": "db.example.com",
        "port": 1433,
        "user": "admin",
        "database": "sales",
        "password": "secret",
    }


def test_to_mysql_helper_sql_config_returns_secret_identity():
    result = MySQLHelper.to_sql_config(connection)
    assert result == {
        "host": "db.example.com",
        "port": 1433,
        "user": "admin",
        "database": "sales",
        "password": "secret",
    }


def test_to_postgres_helper_sql_config_returns_secret_identity():
    result = PostgreSQLHelper.to_sql_config(connection)
    assert result == {
        "host": "db.example.com",
        "port": 1433,
        "user": "admin",
        "database": "sales",
        "password": "secret",
    }


def test_to_snowflake_helper_sql_config_returns_secret_identity():
    result = SnowflakeSqlHelper.to_sql_config(snowflake_connection)
    assert result == {
        "host": "db.example.com.snowflakecomputing.com",
        "port": 1433,
        "user": "admin",
        "database": "sales",
        "password": "secret",
        "account": "db.example.com.us-east-1",
        "region": "us-east-1",
        "warehouse": "wh1",
    }


@patch(
    "sagemaker_studio.connections.sql_helper.athena_sql_helper.AthenaSqlHelper._get_s3_staging_dir"
)
def test_to_athena_helper_sql_config_returns_basic_config(mock_get_s3_staging_dir):
    mock_get_s3_staging_dir.return_value = "s3://test-bucket/athena-results/"

    result = AthenaSqlHelper.to_sql_config(athena_connection)
    assert result == {
        "region": "us-east-1",
        "work_group": "test-workgroup",
        "s3_staging_dir": "s3://test-bucket/athena-results/",
        "aws_access_key_id": "dummy_access_key_id",
        "aws_secret_access_key": "dummy_secret_access_key",
        "aws_session_token": "dummy_session_token",
    }


@patch(
    "sagemaker_studio.connections.sql_helper.athena_sql_helper.AthenaSqlHelper._get_s3_staging_dir"
)
def test_to_athena_helper_sql_config_with_override(mock_get_s3_staging_dir):
    mock_get_s3_staging_dir.return_value = "s3://test-bucket/athena-results/"

    result = AthenaSqlHelper.to_sql_config(
        athena_connection, catalog_name="test_catalog", schema_name="test_schema"
    )
    assert result == {
        "region": "us-east-1",
        "work_group": "test-workgroup",
        "s3_staging_dir": "s3://test-bucket/athena-results/",
        "aws_access_key_id": "dummy_access_key_id",
        "aws_secret_access_key": "dummy_secret_access_key",
        "aws_session_token": "dummy_session_token",
        "catalog_name": "test_catalog",
        "schema_name": "test_schema",
    }
