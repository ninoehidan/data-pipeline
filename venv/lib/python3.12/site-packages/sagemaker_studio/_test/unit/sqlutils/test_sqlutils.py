import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from dateutil.tz import tzlocal
from pandas import DataFrame

from sagemaker_studio import Connection, sqlutils
from sagemaker_studio.project import Project
from sagemaker_studio.sql_engine.sql_executor import SqlExecutor


class TestSqlutils(unittest.TestCase):

    def setUp(self):
        """Setup test fixtures"""
        self.mock_executor = Mock(spec=SqlExecutor)
        self.mock_project = Mock(spec=Project)

        # Reset global variables
        sqlutils._project = None
        sqlutils._sql_executor = SqlExecutor()

        # Create mock connection data that will be used across tests
        self.connection_dict = {
            "connectionId": "connectionid12",
            "description": "This is a default ATHENA connection.",
            "domainId": "dzd_domainid124567",
            "domainUnitId": "domainunitid12",
            "environmentId": "environmentid1",
            "environmentUserRole": "arn:aws:iam::123456789012:role/datazone_usr_role_projectid12345_environmentid1",
            "name": "project.athena",
            "physicalEndpoints": [
                {"awsLocation": {"awsAccountId": "123456789012", "awsRegion": "us-east-1"}}
            ],
            "projectId": "projectid12345",
            "workgroupName": "workgroup-projectid12345-environmentid1",
            "type": "ATHENA",
            "connectionCredentials": {
                "accessKeyId": "mock_access_key",
                "secretAccessKey": "mock_secret_key",
                "sessionToken": "mock_session_token",
                "expiration": datetime(2025, 1, 1, 12, 00, 00, tzinfo=tzlocal()).isoformat(),
            },
        }

        # Create a temporary Connection instance just to use _create_connection_data
        self.mock_connection = Connection(
            connection_data=self.connection_dict,
            glue_api=Mock(),
            datazone_api=Mock(),
            secrets_manager_api=Mock(),
            kms_api=Mock(),
            project_config=Mock(),
        )

    @patch("sagemaker_studio.sqlutils._ensure_duckdb")
    def test_sql_without_connection(self, mock_ensure_duckdb):
        """Test SQL execution without any connection specified"""
        mock_result = Mock()
        mock_result.df.return_value = DataFrame({"col1": [1, 2, 3]})

        mock_duckdb = Mock()
        mock_duckdb.sql.return_value = mock_result

        mock_ensure_duckdb.return_value = mock_duckdb

        query = "SELECT * FROM test_table"
        result = sqlutils.sql(query)

        mock_duckdb.sql.assert_called_once_with(query)
        self.assertIsInstance(result, DataFrame)
        self.assertEqual(list(result["col1"]), [1, 2, 3])

    @patch("sagemaker_studio.sqlutils.HelperFactory")
    @patch("sagemaker_studio.sqlutils._ensure_project")
    @patch("sagemaker_studio.sqlutils._sql_executor")
    def test_sql_with_athena_connection(
        self, mock_sql_executor, mock_ensure_project, mock_helper_factory
    ):
        """Test SQL execution with Athena connection"""
        # Setup mock project to return our Connection instance
        mock_project = Mock()
        mock_project.connection.return_value = self.mock_connection
        mock_ensure_project.return_value = mock_project

        # Setup mock SQL helper
        mock_sql_helper = Mock()
        mock_sql_helper.to_sql_config.return_value = {
            "region_name": "us-east-1",
            "aws_access_key_id": "mock_access_key",
            "aws_secret_access_key": "mock_secret_key",
            "aws_session_token": "mock_session_token",
            "workgroup": "workgroup-projectid12345-environmentid1",
            "database": "default",
            "catalog": "AwsDataCatalog",
        }
        mock_helper_factory.get_sql_helper.return_value = mock_sql_helper

        mock_engine = Mock()
        mock_sql_executor.create_engine.return_value = mock_engine
        mock_sql_executor.get_supported_connection_types.return_value = ["ATHENA"]
        mock_sql_executor.execute.return_value = DataFrame({"col1": [1, 2, 3]})

        query = "SELECT * FROM test_table"
        result = sqlutils.sql(query, connection_name="project.athena")

        # Verify the interaction with helper factory
        mock_project.connection.assert_called_once_with("project.athena")
        mock_helper_factory.get_sql_helper.assert_called_once_with("ATHENA")

        # Verify sql helper was called
        mock_sql_helper.to_sql_config.assert_called_once_with(self.mock_connection)

        # Verify engine creation with correct config
        mock_sql_executor.create_engine.assert_called_once()

        # Verify query execution
        mock_sql_executor.execute.assert_called_once_with(mock_engine, query, None)

        # Verify result
        self.assertIsInstance(result, DataFrame)
        self.assertEqual(list(result["col1"]), [1, 2, 3])

    @patch("sagemaker_studio.sqlutils.HelperFactory")
    @patch("sagemaker_studio.sqlutils._ensure_project")
    @patch("sagemaker_studio.sqlutils._sql_executor")
    @patch(
        "sagemaker_studio.connections.connection.Connection._get_aws_client_with_connection_credentials"
    )
    def test_sql_with_redshift_connection(
        self, mock_get_aws_client, mock_sql_executor, mock_ensure_project, mock_helper_factory
    ):
        """Test SQL execution with Redshift connection"""
        # Mock the glue API client since REDSHIFT is now in SUPPORTED_GLUE_CONNECTION_TYPES
        mock_glue_api = Mock()
        mock_get_aws_client.return_value = mock_glue_api

        # Create Redshift connection
        redshift_connection_dict = self.connection_dict.copy()
        redshift_connection_dict.update(
            {
                "type": "REDSHIFT",
                "name": "project.redshift",
                "physicalEndpoints": [
                    {
                        "awsLocation": {"awsAccountId": "123456789012", "awsRegion": "us-east-1"},
                        "host": "redshift-cluster.123456789012.us-east-1.redshift.amazonaws.com",
                        "port": "5439",
                    }
                ],
            }
        )

        redshift_connection = Connection(
            connection_data=redshift_connection_dict,
            glue_api=Mock(),
            datazone_api=Mock(),
            secrets_manager_api=Mock(),
            kms_api=Mock(),
            project_config=Mock(),
        )

        mock_project = Mock()
        mock_project.connection.return_value = redshift_connection
        mock_ensure_project.return_value = mock_project

        # Setup mock SQL helper
        mock_sql_helper = Mock()
        mock_sql_helper.to_sql_config.return_value = {
            "region_name": "us-east-1",
            "aws_access_key_id": "mock_access_key",
            "aws_secret_access_key": "mock_secret_key",
            "aws_session_token": "mock_session_token",
            "host": "redshift-cluster.123456789012.us-east-1.redshift.amazonaws.com",
            "port": "5439",
            "database": "dev",
            "schema": "public",
        }
        mock_helper_factory.get_sql_helper.return_value = mock_sql_helper

        mock_engine = Mock()
        mock_sql_executor.create_engine.return_value = mock_engine
        mock_sql_executor.get_supported_connection_types.return_value = ["REDSHIFT"]
        mock_sql_executor.execute.return_value = DataFrame({"col1": [1, 2, 3]})

        query = "SELECT * FROM test_table"
        sqlutils.sql(query, connection_name="project.redshift")

        # Verify interactions
        mock_helper_factory.get_sql_helper.assert_called_once_with("REDSHIFT")

        # Verify sql helper was called
        mock_sql_helper.to_sql_config.assert_called_once_with(redshift_connection)

        mock_sql_executor.create_engine.assert_called_once_with(
            "REDSHIFT", mock_sql_helper.to_sql_config.return_value
        )
        mock_sql_executor.execute.assert_called_once_with(mock_engine, query, None)
