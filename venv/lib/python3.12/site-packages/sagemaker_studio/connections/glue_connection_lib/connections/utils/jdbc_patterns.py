"""
JDBC URL patterns for parsing various database connection strings.
"""

import re
from typing import Dict, Pattern

# All JDBC URL patterns from Java implementation
JDBC_PATTERNS: Dict[str, Pattern] = {
    # Matches jdbc:redshift:iam://HOST:PORT/DATABASE for Redshift IAM authentication
    "JDBC_URL_PATTERN_REDSHIFT_IAM": re.compile(
        r"jdbc:(?P<vendor>redshift):iam://"
        r"(?P<host>.*):(?P<port>\d+)"
        r"(?:/|/(?P<database>[^/]*))?/?$"
    ),
    # Generic pattern (excludes sqlserver, oracle, snowflake)
    "JDBC_URL_PATTERN": re.compile(
        r"^jdbc:(?P<vendor>(?!sqlserver|oracle|snowflake).*)"
        r"://(?P<host>.*):(?P<port>\d+)/?(?P<database>[^/]*)/?$"
    ),
    # SQL Server patterns
    # Matches jdbc:sqlserver://SERVER_NAME:PORT;database[Name]=DB_NAME[;]
    "JDBC_URL_PATTERN_SQLSERVER": re.compile(
        r"jdbc:(?P<vendor>sqlserver)://(?P<host>.*):(?P<port>\d+)"
        r"(?:;|(?:;(?:database=|databaseName=)(?P<database>[^;]*)))?;?$"
    ),
    # Matches jdbc:sqlserver://SERVER_NAME:PORT/DB_NAME -- (/DBNAME is optional)
    "JDBC_URL_PATTERN_SQLSERVER_SLASH": re.compile(
        r"jdbc:(?P<vendor>sqlserver)://(?P<host>.*):(?P<port>\d+)" r"(?:/|/(?P<database>[^/]*))?/?$"
    ),
    # Matches jdbc:sqlserver://SERVER_NAME:PORT;database[Name]=DB_NAME[;]applicationName=APP_NAME[;]
    "JDBC_URL_PATTERN_SQLSERVER_APP_NAME": re.compile(
        r"jdbc:(?P<vendor>sqlserver)://(?P<host>.*):(?P<port>\d+)"
        r"(?:;|(?:;(?:database=|databaseName=)(?P<database>[^;]*)))?;?"
        r"(?:;|(?:;(?:applicationName=)(?P<application>[^;]*)))?;?$"
    ),
    # Oracle patterns
    # Matches jdbc:oracle:DRIVER_TYPE://@<host>:<port>/<service_name>
    # or jdbc:oracle:DRIVER_TYPE:@//<host>:<port>/<service_name>
    # /<service_name> is optional for both
    "JDBC_URL_PATTERN_ORACLE": re.compile(
        r"jdbc:(?P<vendor>oracle):(?P<driver>thin|oci|oci8|kprb):"
        r"(?:@//|//@)(?P<host>.*):(?P<port>\d+)(?:/|/(?P<serviceOrSid>[^/]*))?/?$"
    ),
    # Matches jdbc:oracle:DRIVER_TYPE://@<host>:<port>:<side>
    # or jdbc:oracle:DRIVER_TYPE:@//<host>:<port>:<sid>
    "JDBC_URL_PATTERN_ORACLE_SID": re.compile(
        r"jdbc:(?P<vendor>oracle):(?P<driver>thin|oci|oci8|kprb):"
        r"(?:@//|//@)(?P<host>.*):(?P<port>\d+)(?::|:(?P<serviceOrSid>.*))?$"
    ),
    # Matches jdbc:oracle://HOST:PORT/SERVICE_NAME
    "JDBC_URL_PATTERN_ORACLE_NODRIVER": re.compile(
        r"jdbc:(?P<vendor>oracle)://(?P<host>.*):(?P<port>\d+)" r"(?:/|/(?P<serviceOrSid>.*))?/?$"
    ),
    # Matches jdbc:oracle:thin:@(DESCRIPTION= tns config
    "JDBC_URL_PATTERN_ORACLE_TNS": re.compile(
        r"jdbc:(?P<vendor>oracle):(?P<driver>thin|oci|oci8|kprb):@"
        r"\(\s*DESCRIPTION\s*=.*?"
        r"\(\s*HOST\s*=\s*(?P<host>[^)\s]+)\s*\).*"
        r"\(\s*PORT\s*=\s*(?P<port>\d+)\s*\).*?\).*?\s*"
        r"(\(\s*CONNECT_DATA\s*=.*?"
        r"\(\s*SERVICE_NAME\s*=\s*(?P<serviceOrSid>([^)\s])+)\s*\)"
        r")?.*\)"
    ),
    # Snowflake patterns
    # Matches Snowflake JDBC URL with account, user, and optional parameters
    "JDBC_URL_PATTERN_SNOWFLAKE": re.compile(
        r"jdbc:(?P<vendor>snowflake)://"
        r"(?P<account>[^&]+)\.snowflakecomputing\.com/\?"
        r"user=(?P<user>[^&]+)"
        r"&db=(?P<db>[^&]+)"
        r"&role=(?P<role>[^&]+)"
        r"(?=.*(&warehouse=(?P<warehouse>[^&]*)))?"
        r".*$"
    ),
    # MongoDB patterns
    # Matches mongodb://HOST:PORT/DATABASE (database is optional)
    "MONGO_URL_PATTERN": re.compile(
        r"(?P<vendor>mongodb)://(?P<host>.*):(?P<port>\d+)(?:/|/(?P<database>[^/]*))?/?$"
    ),
    # Matches mongodb+srv://HOST/DATABASE (MongoDB Atlas, database is optional)
    "MONGO_ATLAS_URL_PATTERN": re.compile(
        r"(?P<vendor>mongodb)\+srv://(?P<host>[^/]*)(?:/|/(?P<database>[^/]*))?/?$"
    ),
}

# SQL Server instance patterns
SQL_SERVER_INSTANCE_PATTERNS: Dict[str, Pattern] = {
    # Matches jdbc:sqlserver://SERVER_NAME;INSTANCE_NAME:PORT;database[Name]=DB_NAME[;]
    "JDBC_URL_PATTERN_SQLSERVER_INSTANCE_NAME": re.compile(
        r"jdbc:(?P<vendor>sqlserver)://(?P<host>.*);instanceName=(?P<instance>[^;]*)"
        r":(?P<port>\d+)(?:;|(?:;(?:database=|databaseName=)(?P<database>[^;]*)))?;?$"
    ),
    # Matches jdbc:sqlserver://SERVER_NAME;INSTANCE_NAME:PORT;database[Name]=DB_NAME[;]applicationName=APP_NAME[;]
    "JDBC_URL_PATTERN_SQLSERVER_INSTANCE_NAME_APP_NAME": re.compile(
        r"jdbc:(?P<vendor>sqlserver)://(?P<host>.*);instanceName=(?P<instance>[^;]*)"
        r":(?P<port>\d+)(?:;|(?:;(?:database=|databaseName=)(?P<database>[^;]*)))?;?"
        r"(?:;|(?:;(?:applicationName=)(?P<application>[^;]*)))?;?$"
    ),
}
