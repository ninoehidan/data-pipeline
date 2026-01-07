"""
JDBC vendor enumeration.
Migrated from JdbcVendor.java
"""

from enum import Enum


class JdbcVendor(Enum):
    """JDBC vendor types."""

    MYSQL = "mysql"
    ORACLE = "oracle"
    REDSHIFT = "redshift"
    POSTGRESQL = "postgresql"
    SQLSERVER = "sqlserver"
    MONGODB = "mongodb"
    DOCUMENTDB = "documentdb"
    SNOWFLAKE = "snowflake"

    @classmethod
    def from_string(cls, vendor: str) -> "JdbcVendor":
        """Create JdbcVendor from string (case insensitive)."""
        return cls[vendor.upper()]
