import datetime
import sys
import unittest
from unittest.mock import Mock, call, patch

import botocore.exceptions

# Mock aws_embedded_metrics before importing  # noqa: E402
sys.modules["aws_embedded_metrics"] = Mock()
sys.modules["aws_embedded_metrics.sinks"] = Mock()
sys.modules["aws_embedded_metrics.sinks.stdout_sink"] = Mock()
sys.modules["aws_embedded_metrics.logger"] = Mock()
sys.modules["aws_embedded_metrics.logger.metrics_logger"] = Mock()
sys.modules["aws_embedded_metrics.logger.metrics_context"] = Mock()
sys.modules["aws_embedded_metrics.environment"] = Mock()
sys.modules["aws_embedded_metrics.environment.local_environment"] = Mock()

from sagemaker_studio.utils.loggerutils import (  # noqa: E402
    ACCESS_DENIED_PATTERNS,
    CONNECTION_ERROR_PATTERNS,
    DEFAULT_HTTP_CODE,
    FORBIDDEN_HTTP_CODE,
    METRIC_NAMESPACE,
    SERVICE_UNAVAILABLE_CODE,
    SUCCESS_HTTP_CODE,
    SUCCESS_MESSAGE,
    UX_ERROR_PATTERNS,
    ErrorChecker,
    _extract_codes,
    _set_context_properties,
    sync_with_metrics,
)


class TestErrorChecker(unittest.TestCase):
    def setUp(self):
        self.error_checker = ErrorChecker()

    def test_is_service_error_with_5xx_status_codes(self):
        """Test that 5xx HTTP status codes are classified as service errors."""
        # Test various 5xx codes
        self.assertTrue(self.error_checker.is_service_error("500"))
        self.assertTrue(self.error_checker.is_service_error("501"))
        self.assertTrue(self.error_checker.is_service_error("502"))
        self.assertTrue(self.error_checker.is_service_error("503"))
        self.assertTrue(self.error_checker.is_service_error("599"))

    def test_is_service_error_with_4xx_status_codes(self):
        """Test that 4xx HTTP status codes are classified as user errors."""
        # Test various 4xx codes
        self.assertFalse(self.error_checker.is_service_error("400"))
        self.assertFalse(self.error_checker.is_service_error("401"))
        self.assertFalse(self.error_checker.is_service_error("403"))
        self.assertFalse(self.error_checker.is_service_error("404"))
        self.assertFalse(self.error_checker.is_service_error("499"))

    def test_is_service_error_with_other_status_codes(self):
        """Test that non-5xx status codes are classified as user errors."""
        self.assertFalse(self.error_checker.is_service_error("200"))
        self.assertFalse(self.error_checker.is_service_error("300"))
        self.assertFalse(self.error_checker.is_service_error("600"))

    def test_is_service_error_with_non_numeric_codes_client_patterns(self):
        """Test error pattern matching for client errors."""
        # Test access denied patterns
        for pattern in ACCESS_DENIED_PATTERNS:
            self.assertFalse(self.error_checker.is_service_error(pattern))
            # Test with prefix
            self.assertFalse(self.error_checker.is_service_error(f"{pattern}SomeError"))

        # Test UX error patterns
        for pattern in UX_ERROR_PATTERNS:
            self.assertFalse(self.error_checker.is_service_error(pattern))
            # Test with prefix
            self.assertFalse(self.error_checker.is_service_error(f"{pattern}SomeError"))

        # Test connection error patterns
        for pattern in CONNECTION_ERROR_PATTERNS:
            self.assertFalse(self.error_checker.is_service_error(pattern))
            # Test with prefix
            self.assertFalse(self.error_checker.is_service_error(f"{pattern}SomeError"))

    def test_is_service_error_with_non_numeric_codes_service_patterns(self):
        """Test that non-client error patterns are classified as service errors."""
        self.assertTrue(self.error_checker.is_service_error("InternalServerError"))
        self.assertTrue(self.error_checker.is_service_error("UnknownError"))
        self.assertTrue(self.error_checker.is_service_error("ServiceFault"))

    def test_is_service_error_with_error_code_fallback(self):
        """Test fallback to error_code when http_code is not numeric."""
        # When http_code is non-numeric, should check error_code
        self.assertFalse(self.error_checker.is_service_error("non_numeric", "AccessDenied"))
        self.assertTrue(self.error_checker.is_service_error("non_numeric", "InternalError"))

    def test_is_service_error_with_empty_strings(self):
        """Test behavior with empty strings."""
        # Empty http_code and error_code should default to service error
        self.assertTrue(self.error_checker.is_service_error(""))
        self.assertTrue(self.error_checker.is_service_error("", ""))


class TestExtractCodes(unittest.TestCase):
    def test_extract_codes_from_client_error(self):
        """Test extracting codes from botocore ClientError."""
        # Create a mock ClientError
        error_response = {
            "Error": {"Code": "ValidationException"},
            "ResponseMetadata": {"HTTPStatusCode": 400},
        }
        client_error = botocore.exceptions.ClientError(error_response, "TestOperation")

        http_code, error_code = _extract_codes(client_error)

        self.assertEqual(http_code, "400")
        self.assertEqual(error_code, "ValidationException")

    def test_extract_codes_from_endpoint_connection_error(self):
        """Test extracting codes from EndpointConnectionError."""
        endpoint_error = botocore.exceptions.EndpointConnectionError(
            endpoint_url="https://test.com"
        )

        http_code, error_code = _extract_codes(endpoint_error)

        self.assertEqual(http_code, SERVICE_UNAVAILABLE_CODE)
        self.assertEqual(error_code, "EndpointConnectionError")

    def test_extract_codes_from_no_credentials_error(self):
        """Test extracting codes from NoCredentialsError."""
        no_creds_error = botocore.exceptions.NoCredentialsError()

        http_code, error_code = _extract_codes(no_creds_error)

        self.assertEqual(http_code, FORBIDDEN_HTTP_CODE)
        self.assertEqual(error_code, "NoCredentials")

    def test_extract_codes_from_unknown_exception(self):
        """Test extracting codes from unknown exception types."""
        unknown_error = ValueError("test error")

        http_code, error_code = _extract_codes(unknown_error)

        self.assertEqual(http_code, DEFAULT_HTTP_CODE)
        self.assertEqual(error_code, "ValueError")


class TestSetContextProperties(unittest.TestCase):
    @patch("sagemaker_studio.utils.loggerutils._utils")
    def test_set_context_properties(self, mock_utils):
        """Test that all context properties are set correctly."""
        # Setup mocks
        mock_context = Mock()
        mock_utils._get_account_id.return_value = "123456789012"
        mock_utils._get_domain_id.return_value = "test-domain-id"
        mock_utils._get_user_id.return_value = "test-user-id"
        mock_utils._get_datazone_stage.return_value = "test-stage"

        operation = "TestOperation"
        http_code = "200"
        error_details = "Success"

        # Call the function
        _set_context_properties(mock_context, operation, http_code, error_details)

        # Verify namespace and dimensions
        self.assertEqual(mock_context.namespace, METRIC_NAMESPACE)
        self.assertFalse(mock_context.should_use_default_dimensions)
        mock_context.put_dimensions.assert_called_once_with({"Operation": operation})

        # Verify all properties are set
        expected_calls = [
            call("AccountId", "123456789012"),
            call("DataZoneDomainId", "test-domain-id"),
            call("Userid", "test-user-id"),
            call("Stage", "test-stage"),
            call("HTTPErrorCode", http_code),
            call("ErrorCode", error_details),
        ]
        mock_context.set_property.assert_has_calls(expected_calls, any_order=True)

        # Verify all utils methods were called
        mock_utils._get_account_id.assert_called_once()
        mock_utils._get_domain_id.assert_called_once()
        mock_utils._get_user_id.assert_called_once()
        mock_utils._get_datazone_stage.assert_called_once()


class TestSyncWithMetricsDecorator(unittest.TestCase):
    def setUp(self):
        self.operation_name = "TestOperation"

    @patch("sagemaker_studio.utils.loggerutils.LogFileSink")
    @patch("sagemaker_studio.utils.loggerutils.MetricsContext")
    @patch("sagemaker_studio.utils.loggerutils._set_context_properties")
    @patch("sagemaker_studio.utils.loggerutils.logger")
    def test_successful_function_execution(
        self, mock_logger, mock_set_props, mock_context_cls, mock_sink_cls
    ):
        """Test decorator behavior with successful function execution."""
        # Setup mocks
        mock_context = Mock()
        mock_context_cls.return_value.empty.return_value = mock_context
        mock_sink = Mock()
        mock_sink_cls.return_value = mock_sink

        # Create a test function
        @sync_with_metrics(self.operation_name)
        def test_function():
            return "success"

        # Execute the function
        with patch("sagemaker_studio.utils.loggerutils.datetime") as mock_datetime:
            start_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
            end_time = datetime.datetime(2023, 1, 1, 12, 0, 1)  # 1 second later
            mock_datetime.now.side_effect = [start_time, end_time]

            result = test_function()

        # Verify function returned correctly
        self.assertEqual(result, "success")

        # Verify logging
        mock_logger.info.assert_any_call(
            f"Starting metric collection for operation: {self.operation_name}"
        )
        mock_logger.info.assert_any_call(f"Flushing metrics for operation: {self.operation_name}")
        mock_logger.info.assert_any_call(f"Flushed metrics for operation: {self.operation_name}")

        # Verify context properties were set
        mock_set_props.assert_called_once_with(
            mock_context, self.operation_name, SUCCESS_HTTP_CODE, SUCCESS_MESSAGE
        )

        # Verify metrics were put
        mock_context.put_metric.assert_any_call("Success", 1, "Count")
        mock_context.put_metric.assert_any_call("UserError", 0, "Count")
        mock_context.put_metric.assert_any_call("ServiceError", 0, "Count")

        # Verify sink was used
        mock_sink.accept.assert_called_once_with(mock_context)

    @patch("sagemaker_studio.utils.loggerutils.LogFileSink")
    @patch("sagemaker_studio.utils.loggerutils.MetricsContext")
    @patch("sagemaker_studio.utils.loggerutils._set_context_properties")
    @patch("sagemaker_studio.utils.loggerutils._extract_codes")
    @patch("sagemaker_studio.utils.loggerutils.ErrorChecker")
    @patch("sagemaker_studio.utils.loggerutils.logger")
    def test_function_raises_user_error(
        self,
        mock_logger,
        mock_error_checker_cls,
        mock_extract_codes,
        mock_set_props,
        mock_context_cls,
        mock_sink_cls,
    ):
        """Test decorator behavior when function raises a user error."""
        # Setup mocks
        mock_context = Mock()
        mock_context_cls.return_value.empty.return_value = mock_context
        mock_sink = Mock()
        mock_sink_cls.return_value = mock_sink

        mock_error_checker = Mock()
        mock_error_checker_cls.return_value = mock_error_checker
        mock_error_checker.is_service_error.return_value = False  # User error

        mock_extract_codes.return_value = ("400", "ValidationException")

        # Create a test function that raises an exception
        test_exception = ValueError("test error")

        @sync_with_metrics(self.operation_name)
        def test_function():
            raise test_exception

        # Execute the function and verify it raises
        with patch("sagemaker_studio.utils.loggerutils.datetime") as mock_datetime:
            start_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
            end_time = datetime.datetime(2023, 1, 1, 12, 0, 2)  # 2 seconds later
            mock_datetime.now.side_effect = [start_time, end_time]

            with self.assertRaises(ValueError):
                test_function()

        # Verify codes were extracted
        mock_extract_codes.assert_called_once_with(test_exception)

        # Verify error classification
        mock_error_checker.is_service_error.assert_called_once_with("400", "ValidationException")

        # Verify context properties were set
        mock_set_props.assert_called_once_with(
            mock_context, self.operation_name, "400", "ValidationException"
        )

        # Verify metrics were put (user error)
        mock_context.put_metric.assert_any_call("Success", 0, "Count")
        mock_context.put_metric.assert_any_call("UserError", 1, "Count")
        mock_context.put_metric.assert_any_call("ServiceError", 0, "Count")

        # Verify stack trace was set
        mock_context.set_property.assert_called_once()
        call_args = mock_context.set_property.call_args
        self.assertEqual(call_args[0][0], "StackTrace")
        self.assertIn("ValueError: test error", call_args[0][1])

    @patch("sagemaker_studio.utils.loggerutils.LogFileSink")
    @patch("sagemaker_studio.utils.loggerutils.MetricsContext")
    @patch("sagemaker_studio.utils.loggerutils._set_context_properties")
    @patch("sagemaker_studio.utils.loggerutils._extract_codes")
    @patch("sagemaker_studio.utils.loggerutils.ErrorChecker")
    @patch("sagemaker_studio.utils.loggerutils.logger")
    def test_function_raises_service_error(
        self,
        mock_logger,
        mock_error_checker_cls,
        mock_extract_codes,
        mock_set_props,
        mock_context_cls,
        mock_sink_cls,
    ):
        """Test decorator behavior when function raises a service error."""
        # Setup mocks
        mock_context = Mock()
        mock_context_cls.return_value.empty.return_value = mock_context
        mock_sink = Mock()
        mock_sink_cls.return_value = mock_sink

        mock_error_checker = Mock()
        mock_error_checker_cls.return_value = mock_error_checker
        mock_error_checker.is_service_error.return_value = True  # Service error

        mock_extract_codes.return_value = ("500", "InternalServerError")

        # Create a test function that raises an exception
        test_exception = Exception("internal error")

        @sync_with_metrics(self.operation_name)
        def test_function():
            raise test_exception

        # Execute the function and verify it raises
        with patch("sagemaker_studio.utils.loggerutils.datetime") as mock_datetime:
            start_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
            end_time = datetime.datetime(2023, 1, 1, 12, 0, 0, 500000)  # 0.5 seconds later
            mock_datetime.now.side_effect = [start_time, end_time]

            with self.assertRaises(Exception):
                test_function()

        # Verify error classification
        mock_error_checker.is_service_error.assert_called_once_with("500", "InternalServerError")

        # Verify metrics were put (service error)
        mock_context.put_metric.assert_any_call("Success", 0, "Count")
        mock_context.put_metric.assert_any_call("UserError", 0, "Count")
        mock_context.put_metric.assert_any_call("ServiceError", 1, "Count")

    @patch("sagemaker_studio.utils.loggerutils.LogFileSink")
    @patch("sagemaker_studio.utils.loggerutils.MetricsContext")
    @patch("sagemaker_studio.utils.loggerutils.logger")
    def test_metrics_flushing_failure_is_handled(
        self, mock_logger, mock_context_cls, mock_sink_cls
    ):
        """Test that metrics flushing failure is handled gracefully."""
        # Setup mocks to cause failure during metrics flushing
        mock_context = Mock()
        mock_context_cls.return_value.empty.return_value = mock_context
        mock_sink = Mock()
        mock_sink_cls.return_value = mock_sink
        mock_sink.accept.side_effect = Exception("metrics flush failed")

        @sync_with_metrics(self.operation_name)
        def test_function():
            return "success"

        # Execute the function - should not raise despite metrics failure
        result = test_function()

        # Function should still return successfully
        self.assertEqual(result, "success")

        # Should log the metrics failure
        mock_logger.exception.assert_called_once_with(
            f"Failed to flush metrics for operation: {self.operation_name}"
        )

    def test_decorator_preserves_function_attributes(self):
        """Test that the decorator preserves function attributes."""

        @sync_with_metrics(self.operation_name)
        def test_function(arg1, arg2="default"):
            """Test docstring."""
            return arg1 + arg2

        # Function should preserve name and docstring
        self.assertEqual(test_function.__name__, "test_function")
        self.assertEqual(test_function.__doc__, "Test docstring.")

    @patch("sagemaker_studio.utils.loggerutils.LogFileSink")
    @patch("sagemaker_studio.utils.loggerutils.MetricsContext")
    @patch("sagemaker_studio.utils.loggerutils._set_context_properties")
    def test_function_with_arguments(self, mock_set_props, mock_context_cls, mock_sink_cls):
        """Test that decorated function works with arguments."""
        mock_context = Mock()
        mock_context_cls.return_value.empty.return_value = mock_context

        @sync_with_metrics(self.operation_name)
        def test_function(a, b, c="default"):
            return a + b + c

        result = test_function("hello", "world", c="!")
        self.assertEqual(result, "helloworld!")
