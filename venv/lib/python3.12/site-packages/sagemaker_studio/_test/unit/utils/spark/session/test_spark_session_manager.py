"""
Unit tests for SparkSessionManager.

This module tests the abstract base class for Spark session providers.
"""

import sys
from abc import ABC
from unittest.mock import Mock

import pytest

# Mock PySpark and gRPC modules before importing our code
pyspark_modules = [
    "pyspark",
    "pyspark.sql",
    "pyspark.sql.session",
    "pyspark.sql.connect",
    "pyspark.sql.connect.session",
    "pyspark.sql.connect.client",
    "grpc",
]

for module_name in pyspark_modules:
    if module_name not in sys.modules:
        mock_module = Mock()
        if module_name == "grpc":
            # Mock gRPC specific classes and functions
            mock_module.insecure_channel = Mock()
            mock_module.secure_channel = Mock()
            mock_module.UnaryUnaryClientInterceptor = Mock()
        sys.modules[module_name] = mock_module

from sagemaker_studio.utils.spark.session.spark_session_manager import (  # noqa: E402
    SparkSessionManager,
)


class TestSparkSessionManager:
    """Test cases for SparkSessionManager abstract base class."""

    def test_is_abstract_base_class(self):
        """Test that SparkSessionManager is an abstract base class."""
        assert issubclass(SparkSessionManager, ABC)

    def test_cannot_instantiate_directly(self):
        """Test that SparkSessionManager cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SparkSessionManager()

    def test_create_method_is_abstract(self):
        """Test that create method is abstract."""
        # Check that create is in the abstract methods
        assert "create" in SparkSessionManager.__abstractmethods__

    def test_stop_method_is_abstract(self):
        """Test that stop method is abstract."""
        # Check that stop is in the abstract methods
        assert "stop" in SparkSessionManager.__abstractmethods__

    def test_concrete_implementation_can_be_instantiated(self):
        """Test that concrete implementations can be instantiated."""

        class ConcreteSparkSessionManager(SparkSessionManager):
            def create(self):
                return "mock_session"

            def stop(self):
                pass

            def get_session_id(self):
                return "session_id"

        # Should be able to instantiate concrete implementation
        manager = ConcreteSparkSessionManager()
        assert isinstance(manager, SparkSessionManager)
        assert manager.create() == "mock_session"
        assert manager.get_session_id() == "session_id"
        manager.stop()  # Should not raise

    def test_partial_implementation_cannot_be_instantiated(self):
        """Test that partial implementations cannot be instantiated."""

        class PartialSparkSessionManager(SparkSessionManager):
            def create(self):
                return "mock_session"

            # Missing stop method implementation

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PartialSparkSessionManager()

    def test_interface_contract(self):
        """Test that the interface contract is properly defined."""

        class TestSparkSessionManager(SparkSessionManager):
            def create(self):
                return "test_session"

            def stop(self):
                return "stopped"

            def get_session_id(self):
                return "session_id"

        manager = TestSparkSessionManager()

        # Test that methods can be called and return expected types
        session = manager.create()
        assert session == "test_session"

        result = manager.stop()
        assert result == "stopped"

        result = manager.get_session_id()
        assert result == "session_id"
