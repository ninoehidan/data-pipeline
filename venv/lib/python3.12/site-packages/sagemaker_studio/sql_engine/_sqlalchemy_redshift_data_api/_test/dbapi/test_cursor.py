"""
Unit tests for the Cursor class and StatementExecutor.

This module tests the statement execution and polling mechanism
with mocked boto3 responses.
"""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from ...dbapi.connection import Connection
from ...dbapi.connection_params import ConnectionParams
from ...dbapi.cursor import Cursor, ResultConverter, StatementExecutor
from ...dbapi.exceptions import InterfaceError, OperationalError, ProgrammingError


@pytest.fixture
def mock_connection():
    """Create a mock connection for testing."""
    connection = Mock(spec=Connection)
    connection.client = Mock()
    connection.connection_params = ConnectionParams(
        cluster_identifier="test-cluster",
        database_name="testdb",
        db_user="test_user",
        region="us-east-1",
    )
    connection.get_transaction_id.return_value = None
    connection._closed = False
    return connection


@pytest.fixture
def statement_executor(mock_connection):
    """Create a StatementExecutor for testing."""
    return StatementExecutor(mock_connection)


@pytest.fixture
def cursor(mock_connection):
    """Create a Cursor for testing."""
    return Cursor(mock_connection)


class TestStatementExecutor:
    """Test cases for the StatementExecutor class."""

    def test_execute_statement_success(self, statement_executor):
        """Test successful statement execution."""
        # Mock execute_statement response
        statement_executor.client.execute_statement.return_value = {"Id": "test-statement-id-123"}

        # Mock describe_statement response (completed)
        statement_executor.client.describe_statement.return_value = {
            "Status": "FINISHED",
            "HasResultSet": True,
            "ResultMetadata": {"ColumnMetadata": []},
            "RecordsUpdated": 0,
        }

        result = statement_executor.execute_statement("SELECT 1")

        assert result["statement_id"] == "test-statement-id-123"
        assert result["status"] == "FINISHED"
        assert result["has_result_set"] is True

        # Verify execute_statement was called with correct parameters
        statement_executor.client.execute_statement.assert_called_once()
        call_args = statement_executor.client.execute_statement.call_args[1]
        assert call_args["Database"] == "testdb"
        assert call_args["Sql"] == "SELECT 1"
        assert call_args["ClusterIdentifier"] == "test-cluster"
        assert call_args["DbUser"] == "test_user"
        assert "StatementName" in call_args

    def test_execute_statement_with_workgroup(self, mock_connection):
        """Test statement execution with workgroup instead of cluster."""
        mock_connection.connection_params.cluster_identifier = None
        mock_connection.connection_params.workgroup_name = "test-workgroup"

        executor = StatementExecutor(mock_connection)

        # Mock responses
        executor.client.execute_statement.return_value = {"Id": "test-id"}
        executor.client.describe_statement.return_value = {"Status": "FINISHED"}

        executor.execute_statement("SELECT 1")

        call_args = executor.client.execute_statement.call_args[1]
        assert "WorkgroupName" in call_args
        assert call_args["WorkgroupName"] == "test-workgroup"
        assert "ClusterIdentifier" not in call_args

    def test_execute_statement_with_secret_arn(self, mock_connection):
        """Test statement execution with secret ARN."""
        mock_connection.connection_params.secret_arn = (
            "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"
        )

        executor = StatementExecutor(mock_connection)

        # Mock responses
        executor.client.execute_statement.return_value = {"Id": "test-id"}
        executor.client.describe_statement.return_value = {"Status": "FINISHED"}

        executor.execute_statement("SELECT 1")

        call_args = executor.client.execute_statement.call_args[1]
        assert "SecretArn" in call_args
        assert call_args["SecretArn"] == "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"
        assert "DbUser" not in call_args

    def test_execute_statement_without_db_user(self):
        """Test statement execution when db_user is None."""
        from unittest.mock import Mock

        from ...dbapi.connection_params import ConnectionParams
        from ...dbapi.cursor import Cursor

        # Create connection params without db_user (None)
        connection_params = ConnectionParams(
            database_name="test_db",
            cluster_identifier="test-cluster",
            db_user=None,  # Explicitly set to None
            region="us-east-1",
        )

        # Mock connection and client
        mock_connection = Mock()
        mock_connection.connection_params = connection_params
        mock_connection.get_transaction_id.return_value = None
        mock_connection.client = Mock()

        # Mock responses
        mock_connection.client.execute_statement.return_value = {"Id": "test-id"}
        mock_connection.client.describe_statement.return_value = {"Status": "FINISHED"}

        cursor = Cursor(mock_connection)
        cursor.execute("SELECT 1")

        call_args = mock_connection.client.execute_statement.call_args[1]
        assert "DbUser" not in call_args
        assert call_args["Database"] == "test_db"
        assert call_args["ClusterIdentifier"] == "test-cluster"

    def test_execute_statement_with_transaction(self, statement_executor):
        """Test statement execution within a transaction."""
        statement_executor.connection.get_transaction_id.return_value = "txn-123"

        # Mock responses
        statement_executor.client.execute_statement.return_value = {"Id": "test-id"}
        statement_executor.client.describe_statement.return_value = {"Status": "FINISHED"}

        statement_executor.execute_statement("INSERT INTO test VALUES (1)")

        call_args = statement_executor.client.execute_statement.call_args[1]
        assert call_args["TransactionId"] == "txn-123"

    def test_execute_statement_with_parameters(self, statement_executor):
        """Test statement execution with parameters."""
        # Mock responses
        statement_executor.client.execute_statement.return_value = {"Id": "test-id"}
        statement_executor.client.describe_statement.return_value = {"Status": "FINISHED"}

        parameters = ["test_string", 42, 3.14, True, None]
        statement_executor.execute_statement(
            "SELECT * FROM test WHERE col1 = ? AND col2 = ?", parameters
        )

        call_args = statement_executor.client.execute_statement.call_args[1]
        assert "Parameters" in call_args

        params = call_args["Parameters"]
        assert len(params) == 5

        # Check string parameter
        assert params[0]["name"] == "param_0"
        assert params[0]["value"] == "test_string"

        # Check integer parameter
        assert params[1]["name"] == "param_1"
        assert params[1]["value"] == "42"

        # Check float parameter
        assert params[2]["name"] == "param_2"
        assert params[2]["value"] == "3.14"

        # Check boolean parameter
        assert params[3]["name"] == "param_3"
        assert params[3]["value"] == "true"

        # Check null parameter
        assert params[4]["name"] == "param_4"
        assert params[4]["value"] == ""

    def test_execute_statement_no_cluster_or_workgroup(self, mock_connection):
        """Test error when neither cluster nor workgroup is specified."""
        mock_connection.connection_params.cluster_identifier = None
        mock_connection.connection_params.workgroup_name = None

        executor = StatementExecutor(mock_connection)

        with pytest.raises(
            ProgrammingError, match="Either cluster_identifier or workgroup_name must be specified"
        ):
            executor.execute_statement("SELECT 1")

    def test_polling_with_multiple_statuses(self, statement_executor):
        """Test polling mechanism with multiple status changes."""
        # Mock execute_statement response
        statement_executor.client.execute_statement.return_value = {"Id": "test-id"}

        # Mock describe_statement responses - simulate progression
        status_responses = [
            {"Status": "SUBMITTED"},
            {"Status": "PICKED"},
            {"Status": "STARTED"},
            {"Status": "FINISHED", "HasResultSet": False, "RecordsUpdated": 1},
        ]

        statement_executor.client.describe_statement.side_effect = status_responses

        with patch("time.sleep") as mock_sleep:
            result = statement_executor.execute_statement("UPDATE test SET col1 = 'value'")

        assert result["status"] == "FINISHED"
        assert result["records_updated"] == 1
        assert mock_sleep.call_count == 3  # Called for first 3 statuses

    def test_polling_exponential_backoff(self, statement_executor):
        """Test that polling uses exponential backoff."""
        # Mock execute_statement response
        statement_executor.client.execute_statement.return_value = {"Id": "test-id"}

        # Mock describe_statement responses - multiple running statuses
        status_responses = [
            {"Status": "SUBMITTED"},
            {"Status": "STARTED"},
            {"Status": "STARTED"},
            {"Status": "FINISHED", "HasResultSet": False},
        ]

        statement_executor.client.describe_statement.side_effect = status_responses

        with patch("time.sleep") as mock_sleep:
            statement_executor.execute_statement("SELECT 1")

        # Check that sleep intervals increase (exponential backoff)
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert len(sleep_calls) == 3
        assert sleep_calls[0] == 0.1  # Initial interval
        assert abs(sleep_calls[1] - 0.15) < 1e-10  # 0.1 * 1.5 (handle floating point precision)
        assert abs(sleep_calls[2] - 0.225) < 1e-10  # 0.15 * 1.5 (handle floating point precision)

    def test_statement_failed(self, statement_executor):
        """Test handling of failed statement."""
        # Mock execute_statement response
        statement_executor.client.execute_statement.return_value = {"Id": "test-failed-id"}

        # Mock describe_statement response - failed status
        statement_executor.client.describe_statement.return_value = {
            "Status": "FAILED",
            "Error": "Syntax error in SQL statement",
        }

        with pytest.raises(
            OperationalError, match="Statement execution failed: Syntax error in SQL statement"
        ):
            statement_executor.execute_statement("SELECT * FROM nonexistent_table")

    def test_statement_aborted(self, statement_executor):
        """Test handling of aborted statement."""
        # Mock execute_statement response
        statement_executor.client.execute_statement.return_value = {"Id": "test-aborted-id"}

        # Mock describe_statement response - aborted status
        statement_executor.client.describe_statement.return_value = {"Status": "ABORTED"}

        with pytest.raises(OperationalError, match="Statement was cancelled: test-aborted-id"):
            statement_executor.execute_statement("SELECT 1")

    def test_unknown_status(self, statement_executor):
        """Test handling of unknown statement status."""
        # Mock execute_statement response
        statement_executor.client.execute_statement.return_value = {"Id": "test-unknown-id"}

        # Mock describe_statement response - unknown status
        statement_executor.client.describe_statement.return_value = {"Status": "UNKNOWN_STATUS"}

        with pytest.raises(OperationalError, match="Unknown statement status: UNKNOWN_STATUS"):
            statement_executor.execute_statement("SELECT 1")

    def test_get_statement_result(self, statement_executor):
        """Test getting statement results."""
        mock_result = {
            "Records": [
                [{"stringValue": "value1"}, {"longValue": 123}],
                [{"stringValue": "value2"}, {"longValue": 456}],
            ],
            "ColumnMetadata": [
                {"name": "col1", "typeName": "varchar"},
                {"name": "col2", "typeName": "int8"},
            ],
        }

        statement_executor.client.get_statement_result.return_value = mock_result

        result = statement_executor.get_statement_result("test-statement-id")

        assert result == mock_result
        statement_executor.client.get_statement_result.assert_called_once_with(
            Id="test-statement-id"
        )

    def test_get_statement_result_with_pagination(self, statement_executor):
        """Test getting statement results with pagination token."""
        mock_result = {"Records": [], "ColumnMetadata": []}
        statement_executor.client.get_statement_result.return_value = mock_result

        statement_executor.get_statement_result("test-statement-id", next_token="next-page-token")

        statement_executor.client.get_statement_result.assert_called_once_with(
            Id="test-statement-id", NextToken="next-page-token"
        )


class TestCursor:
    """Test cases for the Cursor class."""

    def test_cursor_initialization(self, cursor):
        """Test cursor initialization."""
        assert cursor.connection is not None
        assert cursor.description is None
        assert cursor._result_data == []
        assert cursor._current_row == 0
        assert cursor._statement_id is None
        assert cursor._closed is False
        assert cursor.rowcount == -1

    def test_execute_simple_statement(self, cursor):
        """Test executing a simple SQL statement."""
        # Mock the executor's execute_statement method
        cursor._executor.execute_statement = Mock(
            return_value={
                "statement_id": "test-stmt-123",
                "status": "FINISHED",
                "has_result_set": False,
                "records_updated": 1,
            }
        )

        cursor.execute("INSERT INTO test VALUES (1, 'test')")

        assert cursor._statement_id == "test-stmt-123"
        cursor._executor.execute_statement.assert_called_once_with(
            "INSERT INTO test VALUES (1, 'test')", None
        )

    def test_execute_with_list_parameters(self, cursor):
        """Test executing statement with list parameters."""
        cursor._executor.execute_statement = Mock(
            return_value={
                "statement_id": "test-stmt-456",
                "status": "FINISHED",
                "has_result_set": True,
            }
        )

        parameters = ["test_value", 42]
        cursor.execute("SELECT * FROM test WHERE col1 = ? AND col2 = ?", parameters)

        cursor._executor.execute_statement.assert_called_once_with(
            "SELECT * FROM test WHERE col1 = ? AND col2 = ?", parameters
        )

    def test_execute_with_dict_parameters(self, cursor):
        """Test executing statement with dict parameters."""
        cursor._executor.execute_statement = Mock(
            return_value={
                "statement_id": "test-stmt-789",
                "status": "FINISHED",
                "has_result_set": True,
            }
        )

        parameters = {"param1": "test_value", "param2": 42}
        cursor.execute("SELECT * FROM test WHERE col1 = :param1 AND col2 = :param2", parameters)

        # Dict parameters should be preserved as dict for named parameter support
        cursor._executor.execute_statement.assert_called_once_with(
            "SELECT * FROM test WHERE col1 = :param1 AND col2 = :param2", parameters
        )

    def test_execute_closed_cursor(self, cursor):
        """Test executing on a closed cursor raises error."""
        cursor.close()

        with pytest.raises(InterfaceError, match="Cursor is closed"):
            cursor.execute("SELECT 1")

    def test_execute_resets_cursor_state(self, cursor):
        """Test that execute resets cursor state."""
        # Set some initial state
        cursor.description = [("col1", "varchar")]
        cursor._result_data = [["old_data"]]
        cursor._current_row = 5
        cursor._statement_id = "old-statement-id"

        cursor._executor.execute_statement = Mock(
            return_value={
                "statement_id": "new-stmt-id",
                "status": "FINISHED",
                "has_result_set": False,
            }
        )

        cursor.execute("SELECT 2")

        # State should be reset
        assert cursor.description is None
        assert cursor._result_data == []
        assert cursor._current_row == 0
        assert cursor._statement_id == "new-stmt-id"

    def test_fetch_methods_no_result_set(self, cursor):
        """Test fetch methods when there's no result set."""
        # Execute a statement without results
        cursor._executor.execute_statement = Mock(
            return_value={
                "statement_id": "test-stmt-123",
                "status": "FINISHED",
                "has_result_set": False,
                "records_updated": 1,
            }
        )

        cursor.execute("INSERT INTO test VALUES (1)")

        # Fetch methods should return None/empty list for non-result statements
        assert cursor.fetchone() is None
        assert cursor.fetchall() == []
        assert cursor.fetchmany(5) == []

    def test_cursor_close(self, cursor):
        """Test cursor close method."""
        # Set some state
        cursor.description = [("col1", "varchar")]
        cursor._result_data = [["data"]]
        cursor._current_row = 1
        cursor._statement_id = "stmt-id"

        cursor.close()

        assert cursor._closed is True
        assert cursor.description is None
        assert cursor._result_data == []
        assert cursor._current_row == 0
        assert cursor._statement_id is None

    def test_cursor_context_manager(self, cursor):
        """Test cursor as context manager."""
        with cursor as c:
            assert c is cursor
            assert not cursor._closed

        # Should be closed after exiting context
        assert cursor._closed

    def test_cursor_rowcount_property(self, cursor):
        """Test cursor rowcount property."""
        # Should return -1 until properly implemented in task 7
        assert cursor.rowcount == -1


class TestStatementExecutorErrorHandling:
    """Test error handling in StatementExecutor."""

    def test_boto3_client_error_mapping(self, statement_executor):
        """Test that boto3 ClientError exceptions are properly mapped."""
        # Mock execute_statement to raise ClientError
        client_error = ClientError(
            error_response={
                "Error": {"Code": "ValidationException", "Message": "Invalid SQL syntax"}
            },
            operation_name="ExecuteStatement",
        )

        statement_executor.client.execute_statement.side_effect = client_error

        with pytest.raises(Exception):  # Should be mapped to appropriate DB-API exception
            statement_executor.execute_statement("INVALID SQL")


class TestParameterFormatting:
    """Test parameter formatting functionality."""

    def test_format_parameters_various_types(self, statement_executor):
        """Test formatting of various parameter types."""
        parameters = [
            "string_value",
            42,
            3.14159,
            True,
            False,
            None,
            b"bytes_value",  # Should be converted to string
        ]

        formatted = statement_executor._format_parameters(parameters)

        assert len(formatted) == 7

        # String parameter
        assert formatted[0] == {"name": "param_0", "value": "string_value"}

        # Integer parameter
        assert formatted[1] == {"name": "param_1", "value": "42"}

        # Float parameter
        assert formatted[2] == {"name": "param_2", "value": "3.14159"}

        # Boolean parameters
        assert formatted[3] == {"name": "param_3", "value": "true"}
        assert formatted[4] == {"name": "param_4", "value": "false"}

        # Null parameter
        assert formatted[5] == {"name": "param_5", "value": ""}

        # Bytes parameter (converted to string)
        assert formatted[6] == {"name": "param_6", "value": "b'bytes_value'"}

    def test_format_parameters_empty_list(self, statement_executor):
        """Test formatting empty parameter list."""
        formatted = statement_executor._format_parameters([])
        assert formatted == []

    def test_format_parameters_complex_types(self, statement_executor):
        """Test formatting of complex types that get converted to strings."""
        import datetime

        parameters = [datetime.date(2023, 12, 25), {"key": "value"}, [1, 2, 3]]

        formatted = statement_executor._format_parameters(parameters)

        assert len(formatted) == 3

        # All should be converted to string values
        assert all(isinstance(param["value"], str) for param in formatted)
        assert formatted[0]["value"] == "2023-12-25"
        assert formatted[1]["value"] == "{'key': 'value'}"
        assert formatted[2]["value"] == "[1, 2, 3]"

    def test_format_parameters_named_dict(self, statement_executor):
        """Test formatting of named parameters (dict)."""
        parameters = {
            "name": "John Doe",
            "age": 30,
            "active": True,
            "salary": 75000.50,
            "notes": None,
        }

        formatted = statement_executor._format_parameters(parameters)

        assert len(formatted) == 5

        # Check that parameter names are preserved
        param_names = {param["name"] for param in formatted}
        expected_names = {"name", "age", "active", "salary", "notes"}
        assert param_names == expected_names

        # Check specific parameter values (all should be strings for Data API)
        param_dict = {param["name"]: param["value"] for param in formatted}

        assert param_dict["name"] == "John Doe"
        assert param_dict["age"] == "30"
        assert param_dict["active"] == "true"
        assert param_dict["salary"] == "75000.5"
        assert param_dict["notes"] == ""  # Empty string for NULL


class TestStatementExecutorIntegration:
    """Integration tests for StatementExecutor with realistic scenarios."""

    def test_complete_select_statement_flow(self, statement_executor):
        """Test complete flow for a SELECT statement."""
        # Mock execute_statement response
        statement_executor.client.execute_statement.return_value = {"Id": "select-stmt-123"}

        # Mock describe_statement response
        statement_executor.client.describe_statement.return_value = {
            "Status": "FINISHED",
            "HasResultSet": True,
            "ResultMetadata": {
                "ColumnMetadata": [
                    {"name": "id", "typeName": "int8"},
                    {"name": "name", "typeName": "varchar"},
                ]
            },
            "RecordsUpdated": 0,
        }

        result = statement_executor.execute_statement(
            "SELECT id, name FROM users WHERE active = ?", [True]
        )

        assert result["statement_id"] == "select-stmt-123"
        assert result["status"] == "FINISHED"
        assert result["has_result_set"] is True
        assert result["records_updated"] == 0
        assert result["result_metadata"] is not None

    def test_complete_insert_statement_flow(self, statement_executor):
        """Test complete flow for an INSERT statement."""
        # Mock execute_statement response
        statement_executor.client.execute_statement.return_value = {"Id": "insert-stmt-456"}

        # Mock describe_statement response
        statement_executor.client.describe_statement.return_value = {
            "Status": "FINISHED",
            "HasResultSet": False,
            "RecordsUpdated": 1,
        }

        result = statement_executor.execute_statement(
            "INSERT INTO users (name, email, active) VALUES (?, ?, ?)",
            ["John Doe", "john@example.com", True],
        )

        assert result["statement_id"] == "insert-stmt-456"
        assert result["status"] == "FINISHED"
        assert result["has_result_set"] is False
        assert result["records_updated"] == 1

    def test_transaction_statement_flow(self, statement_executor):
        """Test statement execution within a transaction."""
        # Set up transaction
        statement_executor.connection.get_transaction_id.return_value = "txn-abc123"

        # Mock execute_statement response
        statement_executor.client.execute_statement.return_value = {"Id": "txn-stmt-789"}

        # Mock describe_statement response
        statement_executor.client.describe_statement.return_value = {
            "Status": "FINISHED",
            "HasResultSet": False,
            "RecordsUpdated": 5,
        }

        result = statement_executor.execute_statement(
            "UPDATE users SET last_login = ? WHERE active = ?", ["2023-12-25 10:30:00", True]
        )

        # Verify transaction ID was included in the request
        call_args = statement_executor.client.execute_statement.call_args[1]
        assert call_args["TransactionId"] == "txn-abc123"

        assert result["records_updated"] == 5


class TestResultConverter:
    """Test cases for the ResultConverter class."""

    def test_convert_column_metadata_basic_types(self):
        """Test conversion of basic column metadata."""
        column_metadata = [
            {"name": "id", "typeName": "int8", "precision": None, "scale": None, "nullable": False},
            {
                "name": "name",
                "typeName": "varchar",
                "precision": 255,
                "scale": None,
                "nullable": True,
            },
            {"name": "price", "typeName": "numeric", "precision": 10, "scale": 2, "nullable": True},
        ]

        description = ResultConverter.convert_column_metadata(column_metadata)

        assert len(description) == 3

        # Check id column
        assert description[0][0] == "id"
        assert description[0][1] == "NUMBER"
        assert description[0][4] is None  # precision
        assert description[0][5] is None  # scale
        assert description[0][6] is False  # nullable

        # Check name column
        assert description[1][0] == "name"
        assert description[1][1] == "STRING"
        assert description[1][4] == 255  # precision
        assert description[1][6] is True  # nullable

        # Check price column
        assert description[2][0] == "price"
        assert description[2][1] == "NUMBER"
        assert description[2][4] == 10  # precision
        assert description[2][5] == 2  # scale

    def test_convert_column_metadata_redshift_types(self):
        """Test conversion of Redshift-specific types."""
        column_metadata = [
            {"name": "json_data", "typeName": "super"},
            {"name": "location", "typeName": "geometry"},
            {"name": "created_at", "typeName": "timestamptz"},
            {"name": "is_active", "typeName": "bool"},
        ]

        description = ResultConverter.convert_column_metadata(column_metadata)

        assert description[0][1] == "JSON"  # super -> JSON
        assert description[1][1] == "BINARY"  # geometry -> BINARY
        assert description[2][1] == "DATETIME"  # timestamptz -> DATETIME
        assert description[3][1] == "BOOLEAN"  # bool -> BOOLEAN

    def test_map_type_name_to_code(self):
        """Test type name mapping."""
        # String types
        assert ResultConverter._map_type_name_to_code("varchar") == "STRING"
        assert ResultConverter._map_type_name_to_code("char") == "STRING"
        assert ResultConverter._map_type_name_to_code("text") == "STRING"

        # Numeric types
        assert ResultConverter._map_type_name_to_code("int8") == "NUMBER"
        assert ResultConverter._map_type_name_to_code("integer") == "NUMBER"
        assert ResultConverter._map_type_name_to_code("numeric") == "NUMBER"
        assert ResultConverter._map_type_name_to_code("float8") == "NUMBER"

        # Boolean types
        assert ResultConverter._map_type_name_to_code("bool") == "BOOLEAN"
        assert ResultConverter._map_type_name_to_code("boolean") == "BOOLEAN"

        # Date/time types
        assert ResultConverter._map_type_name_to_code("date") == "DATETIME"
        assert ResultConverter._map_type_name_to_code("timestamp") == "DATETIME"

        # Redshift specific
        assert ResultConverter._map_type_name_to_code("super") == "JSON"
        assert ResultConverter._map_type_name_to_code("geometry") == "BINARY"

        # Unknown type defaults to STRING
        assert ResultConverter._map_type_name_to_code("unknown_type") == "STRING"

    def test_convert_records_various_types(self):
        """Test conversion of records with various data types."""
        records = [
            [
                {"stringValue": "John Doe"},
                {"longValue": 42},
                {"doubleValue": 3.14},
                {"booleanValue": True},
                {"isNull": True},
                {"stringValue": "2023-12-25"},
            ],
            [
                {"stringValue": "Jane Smith"},
                {"longValue": 24},
                {"doubleValue": 2.71},
                {"booleanValue": False},
                {"stringValue": "not null"},
                {"stringValue": "2023-12-26"},
            ],
        ]

        column_metadata = [
            {"typeName": "varchar"},
            {"typeName": "int8"},
            {"typeName": "float8"},
            {"typeName": "bool"},
            {"typeName": "varchar"},
            {"typeName": "date"},
        ]

        converted = ResultConverter.convert_records(records, column_metadata)

        assert len(converted) == 2

        # First row
        assert converted[0][0] == "John Doe"
        assert converted[0][1] == 42
        assert converted[0][2] == 3.14
        assert converted[0][3] is True
        assert converted[0][4] is None  # NULL value
        assert converted[0][5] == "2023-12-25"

        # Second row
        assert converted[1][0] == "Jane Smith"
        assert converted[1][1] == 24
        assert converted[1][2] == 2.71
        assert converted[1][3] is False
        assert converted[1][4] == "not null"
        assert converted[1][5] == "2023-12-26"

    def test_convert_field_value_null(self):
        """Test conversion of NULL field values."""
        field = {"isNull": True}
        result = ResultConverter._convert_field_value(field, "varchar")
        assert result is None

    def test_convert_field_value_string(self):
        """Test conversion of string field values."""
        field = {"stringValue": "test string"}
        result = ResultConverter._convert_field_value(field, "varchar")
        assert result == "test string"

    def test_convert_field_value_numbers(self):
        """Test conversion of numeric field values."""
        # Long value
        field = {"longValue": 123456}
        result = ResultConverter._convert_field_value(field, "int8")
        assert result == 123456

        # Double value
        field = {"doubleValue": 123.456}
        result = ResultConverter._convert_field_value(field, "float8")
        assert result == 123.456

    def test_convert_field_value_boolean(self):
        """Test conversion of boolean field values."""
        field = {"booleanValue": True}
        result = ResultConverter._convert_field_value(field, "bool")
        assert result is True

        field = {"booleanValue": False}
        result = ResultConverter._convert_field_value(field, "bool")
        assert result is False

    def test_convert_field_value_blob(self):
        """Test conversion of blob field values."""
        field = {"blobValue": b"binary data"}
        result = ResultConverter._convert_field_value(field, "geometry")
        assert result == b"binary data"

    def test_convert_field_value_array(self):
        """Test conversion of array field values (SUPER type)."""
        field = {"arrayValue": [{"stringValue": "item1"}, {"stringValue": "item2"}]}
        result = ResultConverter._convert_field_value(field, "super")
        assert result == [{"stringValue": "item1"}, {"stringValue": "item2"}]

    def test_convert_field_value_unknown_field_type(self):
        """Test conversion of unknown field types."""
        field = {"unknownField": "some value"}
        result = ResultConverter._convert_field_value(field, "varchar")
        assert result == field  # Should return the field as-is


class TestCursorResultProcessing:
    """Test cases for cursor result processing functionality."""

    @pytest.fixture
    def cursor_with_results(self, mock_connection):
        """Create a cursor with mocked result data."""
        cursor = Cursor(mock_connection)

        # Mock executor to return result data
        cursor._executor.execute_statement = Mock(
            return_value={
                "statement_id": "test-stmt-123",
                "status": "FINISHED",
                "has_result_set": True,
                "result_metadata": {
                    "ColumnMetadata": [
                        {"name": "id", "typeName": "int8"},
                        {"name": "name", "typeName": "varchar"},
                    ]
                },
            }
        )

        cursor._executor.get_statement_result = Mock()
        return cursor

    def test_execute_with_result_metadata(self, cursor_with_results):
        """Test that execute properly sets up result metadata."""
        cursor_with_results.execute("SELECT id, name FROM users")

        # Check that description is set
        assert cursor_with_results.description is not None
        assert len(cursor_with_results.description) == 2
        assert cursor_with_results.description[0][0] == "id"
        assert cursor_with_results.description[1][0] == "name"

        # Check result set flags
        assert cursor_with_results._has_result_set is True
        assert cursor_with_results._statement_id == "test-stmt-123"

    def test_fetchone_single_batch(self, cursor_with_results):
        """Test fetchone with single batch of results."""
        # Set up mock result data
        cursor_with_results._executor.get_statement_result.return_value = {
            "Records": [
                [{"longValue": 1}, {"stringValue": "Alice"}],
                [{"longValue": 2}, {"stringValue": "Bob"}],
            ],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "name", "typeName": "varchar"},
            ],
        }

        cursor_with_results.execute("SELECT id, name FROM users")

        # First fetchone should load data and return first row
        row1 = cursor_with_results.fetchone()
        assert row1 == [1, "Alice"]

        # Second fetchone should return second row
        row2 = cursor_with_results.fetchone()
        assert row2 == [2, "Bob"]

        # Third fetchone should return None
        row3 = cursor_with_results.fetchone()
        assert row3 is None

    def test_fetchall_single_batch(self, cursor_with_results):
        """Test fetchall with single batch of results."""
        cursor_with_results._executor.get_statement_result.return_value = {
            "Records": [
                [{"longValue": 1}, {"stringValue": "Alice"}],
                [{"longValue": 2}, {"stringValue": "Bob"}],
                [{"longValue": 3}, {"stringValue": "Charlie"}],
            ],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "name", "typeName": "varchar"},
            ],
        }

        cursor_with_results.execute("SELECT id, name FROM users")

        rows = cursor_with_results.fetchall()
        assert len(rows) == 3
        assert rows[0] == [1, "Alice"]
        assert rows[1] == [2, "Bob"]
        assert rows[2] == [3, "Charlie"]

        # Subsequent fetchall should return empty list
        rows2 = cursor_with_results.fetchall()
        assert rows2 == []

    def test_fetchmany_default_size(self, cursor_with_results):
        """Test fetchmany with default arraysize."""
        cursor_with_results._executor.get_statement_result.return_value = {
            "Records": [
                [{"longValue": 1}, {"stringValue": "Alice"}],
                [{"longValue": 2}, {"stringValue": "Bob"}],
                [{"longValue": 3}, {"stringValue": "Charlie"}],
            ],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "name", "typeName": "varchar"},
            ],
        }

        cursor_with_results.execute("SELECT id, name FROM users")

        # Default arraysize is 1
        rows = cursor_with_results.fetchmany()
        assert len(rows) == 1
        assert rows[0] == [1, "Alice"]

    def test_fetchmany_custom_size(self, cursor_with_results):
        """Test fetchmany with custom size."""
        cursor_with_results._executor.get_statement_result.return_value = {
            "Records": [
                [{"longValue": 1}, {"stringValue": "Alice"}],
                [{"longValue": 2}, {"stringValue": "Bob"}],
                [{"longValue": 3}, {"stringValue": "Charlie"}],
            ],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "name", "typeName": "varchar"},
            ],
        }

        cursor_with_results.execute("SELECT id, name FROM users")

        # Fetch 2 rows
        rows = cursor_with_results.fetchmany(2)
        assert len(rows) == 2
        assert rows[0] == [1, "Alice"]
        assert rows[1] == [2, "Bob"]

        # Fetch remaining row
        rows2 = cursor_with_results.fetchmany(2)
        assert len(rows2) == 1
        assert rows2[0] == [3, "Charlie"]

    def test_pagination_handling(self, cursor_with_results):
        """Test pagination with multiple batches."""
        # First batch with next token
        first_batch = {
            "Records": [
                [{"longValue": 1}, {"stringValue": "Alice"}],
                [{"longValue": 2}, {"stringValue": "Bob"}],
            ],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "name", "typeName": "varchar"},
            ],
            "NextToken": "next-page-token",
        }

        # Second batch without next token (last page)
        second_batch = {
            "Records": [
                [{"longValue": 3}, {"stringValue": "Charlie"}],
                [{"longValue": 4}, {"stringValue": "David"}],
            ],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "name", "typeName": "varchar"},
            ],
        }

        # Mock get_statement_result to return different batches
        cursor_with_results._executor.get_statement_result.side_effect = [first_batch, second_batch]

        cursor_with_results.execute("SELECT id, name FROM users")

        # Fetch all rows - should trigger pagination
        rows = cursor_with_results.fetchall()

        assert len(rows) == 4
        assert rows[0] == [1, "Alice"]
        assert rows[1] == [2, "Bob"]
        assert rows[2] == [3, "Charlie"]
        assert rows[3] == [4, "David"]

        # Verify get_statement_result was called twice
        assert cursor_with_results._executor.get_statement_result.call_count == 2

        # Check the calls - first without token, second with token
        calls = cursor_with_results._executor.get_statement_result.call_args_list
        # Each call now includes execution_context as the third argument
        assert calls[0][0][:2] == ("test-stmt-123", None)  # Check first two args
        assert calls[1][0][:2] == ("test-stmt-123", "next-page-token")  # Check first two args

    def test_fetch_closed_cursor(self, cursor_with_results):
        """Test that fetch methods raise error on closed cursor."""
        cursor_with_results.close()

        with pytest.raises(InterfaceError, match="Cursor is closed"):
            cursor_with_results.fetchone()

        with pytest.raises(InterfaceError, match="Cursor is closed"):
            cursor_with_results.fetchall()

        with pytest.raises(InterfaceError, match="Cursor is closed"):
            cursor_with_results.fetchmany()

    def test_result_loading_error_handling(self, cursor_with_results):
        """Test error handling during result loading."""
        cursor_with_results._executor.get_statement_result.side_effect = Exception("API Error")

        cursor_with_results.execute("SELECT id, name FROM users")

        with pytest.raises(OperationalError, match="AWS service error: API Error"):
            cursor_with_results.fetchone()

    def test_mixed_fetch_operations(self, cursor_with_results):
        """Test mixing different fetch operations."""
        cursor_with_results._executor.get_statement_result.return_value = {
            "Records": [
                [{"longValue": 1}, {"stringValue": "Alice"}],
                [{"longValue": 2}, {"stringValue": "Bob"}],
                [{"longValue": 3}, {"stringValue": "Charlie"}],
                [{"longValue": 4}, {"stringValue": "David"}],
                [{"longValue": 5}, {"stringValue": "Eve"}],
            ],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "name", "typeName": "varchar"},
            ],
        }

        cursor_with_results.execute("SELECT id, name FROM users")

        # Fetch one row
        row1 = cursor_with_results.fetchone()
        assert row1 == [1, "Alice"]

        # Fetch two rows
        rows2 = cursor_with_results.fetchmany(2)
        assert len(rows2) == 2
        assert rows2[0] == [2, "Bob"]
        assert rows2[1] == [3, "Charlie"]

        # Fetch remaining rows
        remaining = cursor_with_results.fetchall()
        assert len(remaining) == 2
        assert remaining[0] == [4, "David"]
        assert remaining[1] == [5, "Eve"]

    def test_rowcount_for_select_statement(self, cursor_with_results):
        """Test rowcount for SELECT statements."""
        cursor_with_results.execute("SELECT id, name FROM users")

        # For SELECT statements, rowcount should be -1
        assert cursor_with_results.rowcount == -1

    def test_rowcount_for_insert_statement(self, cursor_with_results):
        """Test rowcount for INSERT statements."""
        cursor_with_results._executor.execute_statement = Mock(
            return_value={
                "statement_id": "insert-stmt-123",
                "status": "FINISHED",
                "has_result_set": False,
                "records_updated": 3,
            }
        )

        cursor_with_results.execute("INSERT INTO users VALUES (...)")

        # For INSERT statements, rowcount should reflect records updated
        assert cursor_with_results.rowcount == 3


class TestCursorLargeResultSets:
    """Test cases for handling large result sets and performance."""

    @pytest.fixture
    def cursor_large_results(self, mock_connection):
        """Create a cursor for testing large result sets."""
        cursor = Cursor(mock_connection)
        cursor._executor.execute_statement = Mock(
            return_value={
                "statement_id": "large-stmt-123",
                "status": "FINISHED",
                "has_result_set": True,
                "result_metadata": {
                    "ColumnMetadata": [
                        {"name": "id", "typeName": "int8"},
                        {"name": "data", "typeName": "varchar"},
                    ]
                },
            }
        )
        cursor._executor.get_statement_result = Mock()
        return cursor

    def test_large_result_set_pagination(self, cursor_large_results):
        """Test handling of large result sets with multiple pages."""
        # Simulate 3 pages of results
        pages = []
        for page in range(3):
            records = []
            for i in range(1000):  # 1000 records per page
                record_id = page * 1000 + i + 1
                records.append([{"longValue": record_id}, {"stringValue": f"data_{record_id}"}])

            page_data = {
                "Records": records,
                "ColumnMetadata": [
                    {"name": "id", "typeName": "int8"},
                    {"name": "data", "typeName": "varchar"},
                ],
            }

            # Add NextToken for all pages except the last
            if page < 2:
                page_data["NextToken"] = f"page_{page + 1}_token"

            pages.append(page_data)

        cursor_large_results._executor.get_statement_result.side_effect = pages
        cursor_large_results.execute("SELECT id, data FROM large_table")

        # Fetch all results
        all_rows = cursor_large_results.fetchall()

        # Should have 3000 total rows
        assert len(all_rows) == 3000

        # Check first and last rows
        assert all_rows[0] == [1, "data_1"]
        assert all_rows[-1] == [3000, "data_3000"]

        # Verify all pages were fetched
        assert cursor_large_results._executor.get_statement_result.call_count == 3

    def test_incremental_loading_with_fetchmany(self, cursor_large_results):
        """Test that results are loaded incrementally with fetchmany."""
        # Create two pages of results
        page1 = {
            "Records": [[{"longValue": i}, {"stringValue": f"data_{i}"}] for i in range(1, 501)],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "data", "typeName": "varchar"},
            ],
            "NextToken": "page_2_token",
        }

        page2 = {
            "Records": [[{"longValue": i}, {"stringValue": f"data_{i}"}] for i in range(501, 1001)],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "data", "typeName": "varchar"},
            ],
        }

        cursor_large_results._executor.get_statement_result.side_effect = [page1, page2]
        cursor_large_results.execute("SELECT id, data FROM large_table")

        # Fetch first 100 rows - should only load first page
        rows1 = cursor_large_results.fetchmany(100)
        assert len(rows1) == 100
        assert cursor_large_results._executor.get_statement_result.call_count == 1

        # Fetch next 600 rows - should load second page to fulfill request
        rows2 = cursor_large_results.fetchmany(600)
        assert (
            len(rows2) == 600
        )  # Should get all 600 requested rows (400 from page 1 + 200 from page 2)
        assert cursor_large_results._executor.get_statement_result.call_count == 2

        # Fetch more rows - should trigger loading of second page
        rows3 = cursor_large_results.fetchmany(100)
        assert len(rows3) == 100
        assert cursor_large_results._executor.get_statement_result.call_count == 2

    def test_various_data_types_conversion(self, cursor_large_results):
        """Test conversion of various Redshift data types."""
        cursor_large_results._executor.get_statement_result.return_value = {
            "Records": [
                [
                    {"longValue": 123},  # int8
                    {"stringValue": "test string"},  # varchar
                    {"doubleValue": 123.456},  # float8
                    {"booleanValue": True},  # bool
                    {"isNull": True},  # NULL
                    {"stringValue": "2023-12-25"},  # date
                    {"stringValue": "2023-12-25 10:30:00"},  # timestamp
                    {"arrayValue": [{"stringValue": "item1"}]},  # super (array)
                    {"blobValue": b"binary_data"},  # geometry/binary
                ]
            ],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "name", "typeName": "varchar"},
                {"name": "price", "typeName": "float8"},
                {"name": "active", "typeName": "bool"},
                {"name": "deleted_at", "typeName": "timestamp"},
                {"name": "created_date", "typeName": "date"},
                {"name": "updated_at", "typeName": "timestamp"},
                {"name": "metadata", "typeName": "super"},
                {"name": "location", "typeName": "geometry"},
            ],
        }

        cursor_large_results.execute("SELECT * FROM mixed_types_table")

        row = cursor_large_results.fetchone()

        assert row[0] == 123  # int8
        assert row[1] == "test string"  # varchar
        assert row[2] == 123.456  # float8
        assert row[3] is True  # bool
        assert row[4] is None  # NULL
        assert row[5] == "2023-12-25"  # date
        assert row[6] == "2023-12-25 10:30:00"  # timestamp
        assert row[7] == [{"stringValue": "item1"}]  # super
        assert row[8] == b"binary_data"  # geometry

    def test_empty_result_set(self, cursor_large_results):
        """Test handling of empty result sets."""
        cursor_large_results._executor.get_statement_result.return_value = {
            "Records": [],
            "ColumnMetadata": [
                {"name": "id", "typeName": "int8"},
                {"name": "name", "typeName": "varchar"},
            ],
        }

        cursor_large_results.execute("SELECT id, name FROM users WHERE 1=0")

        # All fetch methods should return empty results
        assert cursor_large_results.fetchone() is None
        assert cursor_large_results.fetchall() == []
        assert cursor_large_results.fetchmany(10) == []
