"""
Unit tests for DB-API 2.0 exception hierarchy and boto3 exception mapping.
"""

import unittest

from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

from ...dbapi.exceptions import (  # DB-API 2.0 standard exceptions; Redshift Data API specific exceptions; Mapping utilities
    AuthenticationError,
    ClusterNotFoundError,
    DatabaseError,
    DataError,
    Error,
    IntegrityError,
    InterfaceError,
    InternalError,
    InvalidParameterError,
    NotSupportedError,
    OperationalError,
    ProgrammingError,
    StatementExecutionError,
    StatementLimitExceededError,
    StatementTimeoutError,
    Warning,
    _extract_cluster_id_from_message,
    _extract_statement_id_from_message,
    handle_redshift_data_api_error,
    map_boto3_exception,
)


class TestDBAPIExceptionHierarchy(unittest.TestCase):
    """Test the DB-API 2.0 exception hierarchy structure."""

    def test_exception_inheritance(self):
        """Test that all exceptions inherit from the correct base classes."""
        # Test base exceptions
        self.assertTrue(issubclass(Error, Exception))
        self.assertTrue(issubclass(Warning, Exception))

        # Test database error hierarchy
        self.assertTrue(issubclass(InterfaceError, Error))
        self.assertTrue(issubclass(DatabaseError, Error))

        # Test specific database errors
        self.assertTrue(issubclass(DataError, DatabaseError))
        self.assertTrue(issubclass(OperationalError, DatabaseError))
        self.assertTrue(issubclass(IntegrityError, DatabaseError))
        self.assertTrue(issubclass(InternalError, DatabaseError))
        self.assertTrue(issubclass(ProgrammingError, DatabaseError))
        self.assertTrue(issubclass(NotSupportedError, DatabaseError))

    def test_redshift_specific_exceptions(self):
        """Test Redshift Data API specific exceptions."""
        self.assertTrue(issubclass(StatementTimeoutError, OperationalError))
        self.assertTrue(issubclass(StatementLimitExceededError, OperationalError))
        self.assertTrue(issubclass(ClusterNotFoundError, OperationalError))
        self.assertTrue(issubclass(AuthenticationError, OperationalError))
        self.assertTrue(issubclass(InvalidParameterError, ProgrammingError))

    def test_statement_timeout_error_attributes(self):
        """Test StatementTimeoutError custom attributes."""
        error = StatementTimeoutError(
            "Statement timed out", statement_id="stmt-123", timeout_seconds=300
        )
        self.assertEqual(str(error), "Statement timed out (Statement ID: stmt-123, Timeout: 300s)")
        self.assertEqual(error.statement_id, "stmt-123")
        self.assertEqual(error.timeout_seconds, 300)

    def test_statement_limit_exceeded_error_attributes(self):
        """Test StatementLimitExceededError custom attributes."""
        error = StatementLimitExceededError(
            "Too many active statements",
            limit_type="active_statements",
            current_count=10,
            max_count=5,
        )
        self.assertEqual(
            str(error), "Too many active statements (Limit type: active_statements, Usage: 10/5)"
        )
        self.assertEqual(error.limit_type, "active_statements")
        self.assertEqual(error.current_count, 10)
        self.assertEqual(error.max_count, 5)

    def test_cluster_not_found_error_attributes(self):
        """Test ClusterNotFoundError custom attributes."""
        error = ClusterNotFoundError("Cluster not found", cluster_identifier="my-cluster")
        self.assertEqual(str(error), "Cluster not found (Cluster: my-cluster)")
        self.assertEqual(error.cluster_identifier, "my-cluster")

    def test_statement_execution_error_attributes(self):
        """Test StatementExecutionError custom attributes."""
        error = StatementExecutionError(
            "Statement execution failed: syntax error", statement_id="stmt-456"
        )

        # Test attributes
        self.assertEqual(error.statement_id, "stmt-456")

        # Test string representation includes statement ID
        error_str = str(error)
        self.assertEqual(
            error_str, "Statement execution failed: syntax error (Statement ID: stmt-456)"
        )

        # Test without statement ID
        error_no_id = StatementExecutionError("Statement execution failed: syntax error")
        self.assertEqual(str(error_no_id), "Statement execution failed: syntax error")


class TestBoto3ExceptionMapping(unittest.TestCase):
    """Test mapping of boto3 exceptions to DB-API exceptions."""

    def test_no_credentials_error_mapping(self):
        """Test mapping of NoCredentialsError."""
        boto3_error = NoCredentialsError()
        mapped_error = map_boto3_exception(boto3_error)

        self.assertIsInstance(mapped_error, AuthenticationError)
        self.assertIn("AWS credentials error", str(mapped_error))

    def test_partial_credentials_error_mapping(self):
        """Test mapping of PartialCredentialsError."""
        boto3_error = PartialCredentialsError(provider="test", cred_var="AWS_ACCESS_KEY_ID")
        mapped_error = map_boto3_exception(boto3_error)

        self.assertIsInstance(mapped_error, AuthenticationError)
        self.assertIn("AWS credentials error", str(mapped_error))

    def test_non_client_error_mapping(self):
        """Test mapping of non-ClientError boto3 exceptions."""
        boto3_error = Exception("Some AWS service error")
        mapped_error = map_boto3_exception(boto3_error)

        self.assertIsInstance(mapped_error, OperationalError)
        self.assertIn("AWS service error", str(mapped_error))

    def test_authentication_error_codes(self):
        """Test mapping of authentication-related ClientError codes."""
        auth_error_codes = [
            "UnauthorizedOperation",
            "AccessDenied",
            "InvalidUserID.NotFound",
            "TokenRefreshRequired",
        ]

        for error_code in auth_error_codes:
            client_error = ClientError(
                error_response={
                    "Error": {"Code": error_code, "Message": f"Test {error_code} error"}
                },
                operation_name="TestOperation",
            )

            mapped_error = map_boto3_exception(client_error)
            self.assertIsInstance(mapped_error, AuthenticationError)
            self.assertIn(f"Test {error_code} error", str(mapped_error))

    def test_cluster_not_found_error_mapping(self):
        """Test mapping of ClusterNotFoundFault with cluster ID extraction."""
        client_error = ClientError(
            error_response={
                "Error": {
                    "Code": "ClusterNotFoundFault",
                    "Message": "Cluster: my-test-cluster not found",
                }
            },
            operation_name="TestOperation",
        )

        mapped_error = map_boto3_exception(client_error)
        self.assertIsInstance(mapped_error, ClusterNotFoundError)
        self.assertEqual(mapped_error.cluster_identifier, "my-test-cluster")

    def test_validation_error_mapping(self):
        """Test mapping of parameter validation errors."""
        validation_error_codes = [
            "ValidationException",
            "InvalidParameterValue",
            "MissingParameter",
        ]

        for error_code in validation_error_codes:
            client_error = ClientError(
                error_response={
                    "Error": {"Code": error_code, "Message": f"Test {error_code} error"}
                },
                operation_name="TestOperation",
            )

            mapped_error = map_boto3_exception(client_error)
            self.assertIsInstance(mapped_error, InvalidParameterError)

    def test_statement_timeout_error_mapping(self):
        """Test mapping of StatementTimeoutException with statement ID extraction."""
        client_error = ClientError(
            error_response={
                "Error": {
                    "Code": "StatementTimeoutException",
                    "Message": "Statement: abc123-def456 timed out after 300 seconds",
                }
            },
            operation_name="TestOperation",
        )

        mapped_error = map_boto3_exception(client_error)
        self.assertIsInstance(mapped_error, StatementTimeoutError)
        self.assertEqual(mapped_error.statement_id, "abc123-def456")

    def test_statement_limit_exceeded_error_mapping(self):
        """Test mapping of ActiveStatementsExceededException."""
        client_error = ClientError(
            error_response={
                "Error": {
                    "Code": "ActiveStatementsExceededException",
                    "Message": "Too many active statements",
                }
            },
            operation_name="TestOperation",
        )

        mapped_error = map_boto3_exception(client_error)
        self.assertIsInstance(mapped_error, StatementLimitExceededError)
        self.assertEqual(mapped_error.limit_type, "active_statements")

    def test_unknown_error_code_mapping(self):
        """Test mapping of unknown error codes defaults to OperationalError."""
        client_error = ClientError(
            error_response={
                "Error": {"Code": "UnknownErrorCode", "Message": "Unknown error occurred"}
            },
            operation_name="TestOperation",
        )

        mapped_error = map_boto3_exception(client_error)
        self.assertIsInstance(mapped_error, OperationalError)
        self.assertIn("Unknown error occurred", str(mapped_error))


class TestExtractionUtilities(unittest.TestCase):
    """Test utility functions for extracting information from error messages."""

    def test_extract_cluster_id_from_message(self):
        """Test cluster ID extraction from various message formats."""
        test_cases = [
            ("Cluster: my-cluster not found", "my-cluster"),
            ("cluster my-test-cluster-123 is not available", "my-test-cluster-123"),
            ("Cluster my_cluster_name does not exist", "my_cluster_name"),
            ("No cluster information", None),
            ("", None),
        ]

        for message, expected in test_cases:
            result = _extract_cluster_id_from_message(message)
            self.assertEqual(result, expected)

    def test_extract_statement_id_from_message(self):
        """Test statement ID extraction from various message formats."""
        test_cases = [
            ("Statement: abc123-def456 timed out", "abc123-def456"),
            ("statement 12345678-abcd-efgh failed", "12345678-abcd-efgh"),
            ("Statement abc-123-def-456 is running", "abc-123-def-456"),
            ("No statement information", None),
            ("", None),
        ]

        for message, expected in test_cases:
            result = _extract_statement_id_from_message(message)
            self.assertEqual(result, expected)


class TestErrorHandlingDecorator(unittest.TestCase):
    """Test the error handling decorator."""

    def test_decorator_maps_exceptions(self):
        """Test that the decorator properly maps exceptions."""

        @handle_redshift_data_api_error
        def test_function():
            raise NoCredentialsError()

        with self.assertRaises(AuthenticationError):
            test_function()

    def test_decorator_preserves_return_value(self):
        """Test that the decorator preserves return values when no exception occurs."""

        @handle_redshift_data_api_error
        def test_function():
            return "success"

        result = test_function()
        self.assertEqual(result, "success")

    def test_decorator_preserves_exception_chain(self):
        """Test that the decorator preserves the original exception in the chain."""

        @handle_redshift_data_api_error
        def test_function():
            raise NoCredentialsError()

        try:
            test_function()
        except AuthenticationError as e:
            self.assertIsInstance(e.__cause__, NoCredentialsError)
        else:
            self.fail("Expected AuthenticationError to be raised")


if __name__ == "__main__":
    unittest.main()
