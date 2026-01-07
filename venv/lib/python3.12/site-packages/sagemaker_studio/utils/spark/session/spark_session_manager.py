"""
Base Spark Session Provider.

This module provides the abstract base class for all Spark session providers.
"""

from abc import ABC, abstractmethod


class SparkSessionManager(ABC):
    """
    Abstract base class for Spark session providers.

    This defines the interface that all Spark session providers must implement.
    """

    @abstractmethod
    def create(self):
        """
        Create and return a SparkSession.

        Returns:
            SparkSession: A configured SparkSession object.
        """
        pass

    @abstractmethod
    def stop(self):
        """Stop the SparkSession and clean up resources."""
        pass

    @abstractmethod
    def get_session_id(self):
        pass
