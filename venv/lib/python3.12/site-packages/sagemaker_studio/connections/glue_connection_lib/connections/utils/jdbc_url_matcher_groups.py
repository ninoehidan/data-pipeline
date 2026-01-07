"""
JDBC URL regex group names.
"""

from enum import Enum


class JdbcUrlMatcherGroups(Enum):

    VENDOR = "vendor"
    HOST = "host"
    PORT = "port"
    DATABASE = "database"
    SERVICE_OR_SID = "serviceOrSid"

    # SQL Server
    APPLICATION_NAME = "application"
    INSTANCE_NAME = "instance"

    # Snowflake JDBC
    ACCOUNT = "account"
    USER = "user"
    SNOWFLAKE_DATABASE = "db"
    WAREHOUSE = "warehouse"
    ROLE = "role"

    def get_group_name(self) -> str:
        """Get the group name"""
        return self.value
