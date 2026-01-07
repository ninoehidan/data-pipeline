"""
Unit tests for comprehensive error handling and logging functionality.

This module tests the enhanced error handling, retry mechanisms, and
structured logging features added to the Redshift Data API dialect.
"""

import time
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from ...dbapi.connection import Connection
from ...dbapi.cursor import StatementExecutor
from ...dbapi.exceptions import (
    AuthenticationError,
    ClusterNotFoundError,
    DatabaseError,
    InvalidParameterError,
    StatementLimitExceededError,
    StatementTimeoutError,
    TransientError,
    _extract_cluster_id_from_message,
    _extract_statement_id_from_message,
    map_boto3_exception,
)
from ...dbapi.retry import (
    CircuitBreaker,
    RetryConfig,
    RetryContext,
    retry_on_transient_error,
    with_retry,
)


class TestEnhancedExceptions:
    """Test enhanced exception classes with execution context."""

    def test_statement_timeout_error_with_context(self):
        """Test StatementTimeoutError with execution context."""
        context = {
            "sql": "SELECT * FROM large_table",
            "database_name": "test_db",
            "cluster_identifier": "test-cluster",
        }

        error = StatementTimeoutError(
            "Statement timed out",
            statement_id="stmt-123",
            timeout_seconds=300,
            execution_context=context,
        )

        assert error.statement_id == "stmt-123"
        assert error.timeout_seconds == 300
        assert error.execution_context == context

        error_str = str(error)
        assert "Statement ID: stmt-123" in error_str
        assert "Timeout: 300s" in error_str
        assert "sql: SELECT * FROM large_table" in error_str

    def test_statement_limit_exceeded_error_with_context(self):
        """Test StatementLimitExceededError with execution context."""
        context = {"region": "us-east-1"}

        error = StatementLimitExceededError(
            "Too many active statements",
            limit_type="active_statements",
            current_count=10,
            max_count=10,
            execution_context=context,
        )

        assert error.limit_type == "active_statements"
        assert error.current_count == 10
        assert error.max_count == 10

        error_str = str(error)
        assert "Limit type: active_statements" in error_str
        assert "Usage: 10/10" in error_str
        assert "region: us-east-1" in error_str

    def test_cluster_not_found_error_with_context(self):
        """Test ClusterNotFoundError with execution context."""
        context = {"operation": "connect"}

        error = ClusterNotFoundError(
            "Cluster not found",
            cluster_identifier="test-cluster",
            workgroup_name="test-workgroup",
            execution_context=context,
        )

        assert error.cluster_identifier == "test-cluster"
        assert error.workgroup_name == "test-workgroup"

        error_str = str(error)
        assert "Cluster: test-cluster" in error_str
        assert "Workgroup: test-workgroup" in error_str
        assert "operation: connect" in error_str

    def test_authentication_error_with_context(self):
        """Test AuthenticationError with execution context."""
        context = {"credential_source": "environment"}

        error = AuthenticationError(
            "Invalid credentials",
            auth_method="iam_role",
            region="us-west-2",
            execution_context=context,
        )

        assert error.auth_method == "iam_role"
        assert error.region == "us-west-2"

        error_str = str(error)
        assert "Auth method: iam_role" in error_str
        assert "Region: us-west-2" in error_str
        assert "credential_source: environment" in error_str

    def test_transient_error_with_retry_info(self):
        """Test TransientError with retry information."""
        context = {"request_id": "req-123"}

        error = TransientError(
            "Service temporarily unavailable",
            retry_after=30,
            attempt_count=2,
            max_attempts=5,
            execution_context=context,
        )

        assert error.retry_after == 30
        assert error.attempt_count == 2
        assert error.max_attempts == 5

        error_str = str(error)
        assert "Retry after: 30s" in error_str
        assert "Attempt: 2/5" in error_str
        assert "request_id: req-123" in error_str


class TestExceptionMapping:
    """Test boto3 exception mapping with execution context."""

    def test_map_no_credentials_error(self):
        """Test mapping NoCredentialsError."""
        context = {"auth_method": "environment", "region": "us-east-1"}
        boto3_error = NoCredentialsError()

        mapped = map_boto3_exception(boto3_error, context)

        assert isinstance(mapped, AuthenticationError)
        assert mapped.auth_method == "environment"
        assert mapped.region == "us-east-1"
        assert mapped.execution_context == context

    def test_map_client_error_cluster_not_found(self):
        """Test mapping ClientError for cluster not found."""
        context = {"cluster_identifier": "test-cluster"}

        boto3_error = ClientError(
            error_response={
                "Error": {
                    "Code": "ClusterNotFoundFault",
                    "Message": "Cluster test-cluster not found",
                },
                "ResponseMetadata": {"RequestId": "req-123"},
            },
            operation_name="execute_statement",
        )

        mapped = map_boto3_exception(boto3_error, context)

        assert isinstance(mapped, ClusterNotFoundError)
        assert mapped.cluster_identifier == "test-cluster"
        assert "aws_request_id" in mapped.execution_context
        assert mapped.execution_context["aws_request_id"] == "req-123"

    def test_map_client_error_statement_timeout(self):
        """Test mapping ClientError for statement timeout."""
        context = {"statement_id": "stmt-456", "timeout_seconds": 300}

        boto3_error = ClientError(
            error_response={
                "Error": {
                    "Code": "StatementTimeoutException",
                    "Message": "Statement stmt-456 timed out",
                }
            },
            operation_name="describe_statement",
        )

        mapped = map_boto3_exception(boto3_error, context)

        assert isinstance(mapped, StatementTimeoutError)
        assert mapped.statement_id == "stmt-456"
        assert mapped.timeout_seconds == 300

    def test_map_client_error_throttling(self):
        """Test mapping ClientError for throttling (transient error)."""
        context = {"operation": "execute_statement"}

        boto3_error = ClientError(
            error_response={
                "Error": {"Code": "ThrottlingException", "Message": "Request rate exceeded"},
                "ResponseMetadata": {"HTTPHeaders": {"retry-after": "5"}},
            },
            operation_name="execute_statement",
        )

        mapped = map_boto3_exception(boto3_error, context)

        assert isinstance(mapped, TransientError)
        assert mapped.retry_after == 5

    def test_extract_cluster_id_from_message(self):
        """Test extracting cluster ID from error messages."""
        # Test "Cluster: identifier" format
        message1 = "Cluster: my-test-cluster not found"
        assert _extract_cluster_id_from_message(message1) == "my-test-cluster"

        # Test "cluster identifier" format
        message2 = "cluster my-cluster-123 is not available"
        assert _extract_cluster_id_from_message(message2) == "my-cluster-123"

        # Test no match
        message3 = "Some other error message"
        assert _extract_cluster_id_from_message(message3) is None

    def test_extract_statement_id_from_message(self):
        """Test extracting statement ID from error messages."""
        # Test "Statement: identifier" format
        message1 = "Statement: abc-123-def timed out"
        assert _extract_statement_id_from_message(message1) == "abc-123-def"

        # Test "statement identifier" format
        message2 = "statement xyz-456-ghi failed to execute"
        assert _extract_statement_id_from_message(message2) == "xyz-456-ghi"

        # Test no match
        message3 = "Some other error message"
        assert _extract_statement_id_from_message(message3) is None


class TestRetryConfig:
    """Test retry configuration and delay calculation."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True

    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=1.0, backoff_multiplier=2.0, jitter=False)

        assert config.calculate_delay(0) == 1.0  # 1.0 * 2^0
        assert config.calculate_delay(1) == 2.0  # 1.0 * 2^1
        assert config.calculate_delay(2) == 4.0  # 1.0 * 2^2

    def test_calculate_delay_with_max_delay(self):
        """Test delay calculation with maximum delay cap."""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, backoff_multiplier=2.0, jitter=False)

        assert config.calculate_delay(0) == 10.0
        assert config.calculate_delay(1) == 15.0  # Capped at max_delay
        assert config.calculate_delay(2) == 15.0  # Still capped

    def test_calculate_delay_with_retry_after(self):
        """Test delay calculation with server-suggested retry-after."""
        config = RetryConfig(base_delay=1.0, jitter=False)

        # Server suggests 5 seconds
        assert config.calculate_delay(0, retry_after=5.0) == 5.0
        assert config.calculate_delay(1, retry_after=5.0) == 5.0

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        config = RetryConfig(base_delay=10.0, jitter=True)

        # With jitter, delay should be within 10% of base delay
        delay = config.calculate_delay(0)
        assert 9.0 <= delay <= 11.0

    def test_should_retry_transient_error(self):
        """Test retry decision for transient errors."""
        config = RetryConfig(max_attempts=3)

        transient_error = TransientError("Service unavailable")

        assert config.should_retry(transient_error, 0) is True
        assert config.should_retry(transient_error, 1) is True
        assert config.should_retry(transient_error, 2) is True
        assert config.should_retry(transient_error, 3) is False  # Max attempts reached

    def test_should_retry_boto3_client_error(self):
        """Test retry decision for boto3 ClientError."""
        config = RetryConfig(max_attempts=3)

        # Throttling exception should be retried
        throttling_error = ClientError(
            error_response={"Error": {"Code": "ThrottlingException"}}, operation_name="test"
        )
        assert config.should_retry(throttling_error, 0) is True

        # Validation exception should not be retried
        validation_error = ClientError(
            error_response={"Error": {"Code": "ValidationException"}}, operation_name="test"
        )
        assert config.should_retry(validation_error, 0) is False


class TestRetryContext:
    """Test retry context for tracking attempts."""

    def test_retry_context_initialization(self):
        """Test retry context initialization."""
        context = RetryContext("test_operation", {"key": "value"})

        assert context.operation_name == "test_operation"
        assert context.execution_context == {"key": "value"}
        assert context.attempt_count == 0
        assert context.last_exception is None
        assert context.total_delay == 0.0


class TestRetryDecorator:
    """Test retry decorator functionality."""

    def test_with_retry_success_no_retries(self):
        """Test successful execution without retries."""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3))
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_function()

        assert result == "success"
        assert call_count == 1

    def test_with_retry_success_after_retries(self):
        """Test successful execution after retries."""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TransientError("Temporary failure")
            return "success"

        result = test_function()

        assert result == "success"
        assert call_count == 3

    def test_with_retry_failure_after_max_attempts(self):
        """Test failure after exhausting all retry attempts."""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=2, base_delay=0.01))
        def test_function():
            nonlocal call_count
            call_count += 1
            raise TransientError("Persistent failure")

        with pytest.raises(TransientError, match="Persistent failure"):
            test_function()

        assert call_count == 3  # Initial attempt + 2 retries

    def test_with_retry_non_retryable_exception(self):
        """Test immediate failure for non-retryable exceptions."""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3))
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError, match="Not retryable"):
            test_function()

        assert call_count == 1  # No retries for non-retryable exception


class TestRetryFunction:
    """Test retry_on_transient_error function."""

    def test_retry_function_success(self):
        """Test successful function execution."""

        def test_func(x, y):
            return x + y

        result = retry_on_transient_error(
            test_func, args=(2, 3), config=RetryConfig(max_attempts=3)
        )

        assert result == 5

    def test_retry_function_with_kwargs(self):
        """Test function execution with keyword arguments."""

        def test_func(x, y=10):
            return x * y

        result = retry_on_transient_error(
            test_func, args=(5,), kwargs={"y": 3}, config=RetryConfig(max_attempts=3)
        )

        assert result == 15

    def test_retry_function_with_boto3_exception_mapping(self):
        """Test function execution with boto3 exception mapping."""
        call_count = 0

        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Simulate a throttling exception
                raise ClientError(
                    error_response={"Error": {"Code": "ThrottlingException"}}, operation_name="test"
                )
            return "success"

        result = retry_on_transient_error(
            test_func,
            config=RetryConfig(max_attempts=3, base_delay=0.01),
            execution_context={"operation": "test"},
        )

        assert result == "success"
        assert call_count == 3


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state (normal operation)."""
        breaker = CircuitBreaker(failure_threshold=3)

        def test_func():
            return "success"

        result = breaker.call(test_func)
        assert result == "success"
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)

        def failing_func():
            raise ValueError("Test failure")

        # First failure
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 1

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == "OPEN"
        assert breaker.failure_count == 2

    def test_circuit_breaker_open_state_blocks_calls(self):
        """Test circuit breaker blocks calls when open."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)

        def failing_func():
            raise Exception("Test failure")

        # Trigger circuit opening
        with pytest.raises(Exception):
            breaker.call(failing_func)

        # Circuit should be open and block subsequent calls
        from ...dbapi.exceptions import OperationalError

        with pytest.raises(OperationalError, match="Circuit breaker is OPEN"):
            breaker.call(failing_func)

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)

        def initially_failing_func():
            return "recovered"

        # Trigger circuit opening
        def failing_func():
            raise Exception("Test failure")

        with pytest.raises(Exception):
            breaker.call(failing_func)
        assert breaker.state == "OPEN"

        # Wait for recovery timeout
        time.sleep(0.02)

        # Next call should enter half-open state and succeed
        result = breaker.call(initially_failing_func)
        assert result == "recovered"
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0


class TestStatementExecutorErrorHandling:
    """Test error handling in StatementExecutor."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock connection for testing."""
        connection = Mock()
        connection.connection_params = Mock()
        connection.connection_params.database_name = "test_db"
        connection.connection_params.cluster_identifier = "test-cluster"
        connection.connection_params.workgroup_name = None
        connection.connection_params.region = "us-east-1"
        connection.connection_params.secret_arn = None
        connection.connection_params.db_user = "test_user"
        connection.get_transaction_id.return_value = None

        # Mock the boto3 client
        mock_client = Mock()
        connection.client = mock_client

        return connection

    def test_execute_statement(self, mock_connection):
        """Test statement execution."""
        executor = StatementExecutor(mock_connection)

        # Mock successful execution
        mock_connection.client.execute_statement.return_value = {"Id": "stmt-123"}
        mock_connection.client.describe_statement.return_value = {
            "Status": "FINISHED",
            "HasResultSet": True,
            "ResultMetadata": {"ColumnMetadata": []},
            "RecordsUpdated": 0,
        }

        result = executor.execute_statement("SELECT 1", timeout_seconds=30)

        assert result["statement_id"] == "stmt-123"

    def test_execute_statement_submission_failure(self, mock_connection):
        """Test statement submission failure with error mapping."""
        executor = StatementExecutor(mock_connection)

        # Mock submission failure
        boto3_error = ClientError(
            error_response={
                "Error": {"Code": "ValidationException", "Message": "Invalid SQL syntax"}
            },
            operation_name="execute_statement",
        )
        mock_connection.client.execute_statement.side_effect = boto3_error

        with pytest.raises(InvalidParameterError, match="Invalid SQL syntax"):
            executor.execute_statement("INVALID SQL")

    def test_polling_with_timeout_and_cancellation(self, mock_connection):
        """Test statement polling with timeout and cancellation."""
        executor = StatementExecutor(mock_connection)

        # Mock statement submission
        mock_connection.client.execute_statement.return_value = {"Id": "stmt-123"}

        # Mock polling that never completes (always returns STARTED)
        mock_connection.client.describe_statement.return_value = {"Status": "STARTED"}

        # Mock cancellation
        mock_connection.client.cancel_statement.return_value = {}

        with pytest.raises(StatementTimeoutError) as exc_info:
            executor.execute_statement("SELECT pg_sleep(1000)", timeout_seconds=0.1)

        # Verify timeout error details
        error = exc_info.value
        assert error.statement_id == "stmt-123"
        assert error.timeout_seconds == 0.1

        # Verify cancellation was attempted
        mock_connection.client.cancel_statement.assert_called_once_with(Id="stmt-123")

    def test_polling_statement_failure(self, mock_connection):
        """Test handling of statement execution failure."""
        executor = StatementExecutor(mock_connection)

        # Mock statement submission
        mock_connection.client.execute_statement.return_value = {"Id": "stmt-123"}

        # Mock statement failure
        mock_connection.client.describe_statement.return_value = {
            "Status": "FAILED",
            "Error": "Syntax error at line 1",
            "QueryString": "INVALID SQL",
        }

        from ...dbapi.exceptions import OperationalError

        with pytest.raises(
            OperationalError, match="Statement execution failed: Syntax error at line 1"
        ):
            executor.execute_statement("INVALID SQL")


class TestConnectionErrorHandling:
    """Test error handling in Connection class."""

    @pytest.fixture
    def mock_connection_params(self):
        """Create mock connection parameters."""
        params = Mock()
        params.database_name = "test_db"
        params.cluster_identifier = "test-cluster"
        params.workgroup_name = None
        params.region = "us-east-1"
        params.secret_arn = None
        params.db_user = "test_user"
        return params

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    def test_transaction_commit_failure(
        self, mock_client_class, mock_create_params, mock_connection_params
    ):
        """Test transaction commit failure with error mapping."""
        mock_create_params.return_value = mock_connection_params

        # Mock client manager
        mock_client_manager = Mock()
        mock_client = Mock()
        mock_client_manager.client = mock_client
        mock_client_class.return_value = mock_client_manager

        # Create connection
        conn = Connection("test-cluster", "test_db", "test_user", "us-east-1")
        conn.transaction_id = "txn-123"

        # Mock commit failure
        boto3_error = ClientError(
            error_response={
                "Error": {"Code": "InternalServerException", "Message": "Internal service error"}
            },
            operation_name="commit_transaction",
        )
        mock_client.commit_transaction.side_effect = boto3_error

        with pytest.raises(DatabaseError, match="Failed to commit transaction"):
            conn.commit()

        assert conn.transaction_id == "txn-123"  # Transaction ID should remain on failure

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    def test_transaction_rollback_success(
        self, mock_client_class, mock_create_params, mock_connection_params
    ):
        """Test successful transaction rollback."""
        mock_create_params.return_value = mock_connection_params

        # Mock client manager
        mock_client_manager = Mock()
        mock_client = Mock()
        mock_client_manager.client = mock_client
        mock_client_class.return_value = mock_client_manager

        # Create connection
        conn = Connection("test-cluster", "test_db", "test_user", "us-east-1")
        conn.transaction_id = "txn-456"

        # Mock successful rollback
        mock_client.rollback_transaction.return_value = {}

        conn.rollback()

        assert conn.transaction_id is None  # Transaction ID should be cleared

    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.create_connection_params"
    )
    @patch(
        "sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connection.RedshiftDataAPIClient"
    )
    def test_begin_transaction_failure(
        self, mock_client_class, mock_create_params, mock_connection_params
    ):
        """Test begin transaction failure with error mapping."""
        mock_create_params.return_value = mock_connection_params

        # Mock client manager
        mock_client_manager = Mock()
        mock_client = Mock()
        mock_client_manager.client = mock_client
        mock_client_class.return_value = mock_client_manager

        # Create connection
        conn = Connection("test-cluster", "test_db", "test_user", "us-east-1")

        # Mock begin transaction failure
        boto3_error = ClientError(
            error_response={
                "Error": {
                    "Code": "ClusterNotFoundFault",
                    "Message": "Cluster test-cluster not found",
                }
            },
            operation_name="begin_transaction",
        )
        mock_client.begin_transaction.side_effect = boto3_error

        with pytest.raises(DatabaseError, match="Failed to begin transaction"):
            conn.begin_transaction()

        assert conn.transaction_id is None  # No transaction should be created


if __name__ == "__main__":
    pytest.main([__file__])
