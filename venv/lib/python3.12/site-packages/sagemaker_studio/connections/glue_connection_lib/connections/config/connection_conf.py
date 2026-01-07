"""Base Connection Configuration class."""

from abc import ABC, abstractmethod
from typing import Dict


class _ConnectionConf(ABC):
    """Base class for connection configurations."""

    def __init__(self):
        self._map: Dict[str, str] = {}

    def __call__(self, key: str) -> str:
        """Get value by key."""
        return self._map[key]

    def update(self, key: str, value: str) -> None:
        """Update configuration with key-value pair."""
        self._map[key] = value

    @abstractmethod
    def as_map(self) -> Dict[str, str]:
        """Convert to dictionary format for Spark options."""
        pass
