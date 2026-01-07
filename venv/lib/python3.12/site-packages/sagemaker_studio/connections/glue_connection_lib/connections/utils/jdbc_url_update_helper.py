"""
JDBC URL Update Helper - Python equivalent of JDBCUrlUpdateHelper.scala
"""

import logging
import re
from typing import Dict
from urllib.parse import quote

from ..constants import SparkOptionsKey
from .jdbc_connection_properties import JdbcConnectionProperties
from .jdbc_url import JdbcUrl

logger = logging.getLogger(__name__)


class JDBCUrlUpdateHelper:
    """Helper class for updating JDBC URLs based on vendor-specific requirements."""

    MONGO_CONNECTION_TRANSLATION_MAP = {
        SparkOptionsKey.URL: "connection.uri",
        SparkOptionsKey.USER: "username",
        SparkOptionsKey.PASSWORD: "password",
        SparkOptionsKey.ENFORCE_SSL: "ssl",
    }

    @staticmethod
    def update_url_in_props(
        vendor: str, url: str, props: Dict[str, str], additional_options: Dict[str, str]
    ) -> Dict[str, str]:
        """Update URL in properties based on vendor type."""
        vendor_lower = vendor.lower()

        if vendor_lower == "mysql":
            return JDBCUrlUpdateHelper._update_props_mysql(url, props)
        elif vendor_lower == "oracle":
            return JDBCUrlUpdateHelper._update_props_oracle(url, props)
        elif vendor_lower == "sqlserver":
            return JDBCUrlUpdateHelper._update_props_sql_server(url, props)
        elif vendor_lower == "redshift":
            return JDBCUrlUpdateHelper._update_props_redshift(url, props, additional_options)
        elif vendor_lower in ("mongodb", "documentdb"):
            return JDBCUrlUpdateHelper._update_url_mongodb(url, props, additional_options)
        else:
            return props

    @staticmethod
    def _create_result_with_url(props: Dict[str, str], url: str) -> Dict[str, str]:
        """Create result dictionary with URL properties."""
        result = props.copy()
        result[SparkOptionsKey.URL] = url
        result[SparkOptionsKey.FULL_URL] = url
        return result

    @staticmethod
    def _add_url_params(url: str, params: Dict[str, str]) -> str:
        """Add parameters to URL with proper separator."""
        if not params:
            return url

        new_url = url
        for key, value in params.items():
            sep = "&" if "?" in new_url else "?"
            new_url = f"{new_url}{sep}{key}={value}"
        return new_url

    @staticmethod
    def _update_props_mysql(url: str, props: Dict[str, str]) -> Dict[str, str]:
        """Update MySQL connection properties.

        Same as MySQLUtils.updateUrl in dataplane package.
        """
        new_url = url

        # Add performance properties
        perf_properties = {"useCursorFetch": "true"}
        new_url = JDBCUrlUpdateHelper._add_url_params(new_url, perf_properties)

        # Add zero date time behavior
        new_url = JDBCUrlUpdateHelper._add_url_params(
            new_url, {"zeroDateTimeBehavior": "convertToNull"}
        )

        # Add SSL properties
        ssl_property_keys = set(
            JdbcConnectionProperties.get_driver_connection_properties("mysql")
            .get_ssl_with_dn_match_properties()
            .keys()
        )
        ssl_query_params = {k: v for k, v in props.items() if k in ssl_property_keys}
        new_url = JDBCUrlUpdateHelper._add_url_params(new_url, ssl_query_params)

        return JDBCUrlUpdateHelper._create_result_with_url(props, new_url)

    @staticmethod
    def _update_props_oracle(url: str, props: Dict[str, str]) -> Dict[str, str]:
        """Update Oracle connection properties.

        Same as OracleUtils.updateUrl in dataplane package.
        """
        use_ssl = "javax.net.ssl.trustStore" in props or (
            props.get(SparkOptionsKey.ENFORCE_SSL, "").lower() == "true"
        )

        if use_ssl:
            new_url = JdbcUrl.from_url(url).get_connection_url(use_ssl=True, use_domain_match=True)
        else:
            connection_url = JdbcUrl.from_url(url).get_connection_url(
                use_ssl=False, use_domain_match=False
            )
            if connection_url.startswith("jdbc:oracle:thin://@"):
                connection_url = connection_url.replace(
                    "jdbc:oracle:thin://@", "jdbc:oracle:thin:@//"
                )
            new_url = connection_url

        return JDBCUrlUpdateHelper._create_result_with_url(props, new_url)

    @staticmethod
    def _update_props_sql_server(url: str, props: Dict[str, str]) -> Dict[str, str]:
        """Update SQL Server connection properties.

        Same as SQLServerUtils.updateUrl in dataplane package.
        """
        if "database=" in url or "databaseName=" in url:
            # If rawUrl is in SQL Server format, return rawUrl
            new_url = url
        else:
            # If rawUrl is in other jdbc format like MySQL format, convert it into SQL server format
            # Database can not be wild card but empty string instead, otherwise there will be connection error.
            # Notice: when database is empty string, the master database is connected
            parts = url.split(":")
            if len(parts) >= 4:
                database_part = parts[3].split("/")
                if len(database_part) > 1:
                    database_name = database_part[1]
                    index = url.rfind(f"/{database_name}")

                    if database_name == "%":
                        database_param = "database="
                    else:
                        # Add curly braces to escape anything inside
                        database_param = f"database={{{database_name}}}"

                    # Unlike other databases, sql server needs to use ";" to separate port number and database name
                    new_url = url[:index] + ";" + database_param
                else:
                    raise ValueError(f"Invalid SQL Server URL format: {url}")
            else:
                raise ValueError(f"Invalid SQL Server URL format: {url}")

        # Handle SSL
        if props.get("encrypt", "").lower() == "true":
            new_url = JdbcUrl.from_url(new_url).get_connection_url(
                use_ssl=True, use_domain_match=True
            )
        else:
            new_url = JdbcUrl.from_url(new_url).get_connection_url(
                use_ssl=False, use_domain_match=False
            )

        return JDBCUrlUpdateHelper._create_result_with_url(props, new_url)

    @staticmethod
    def _update_props_redshift(
        url: str, props: Dict[str, str], additional_options: Dict[str, str]
    ) -> Dict[str, str]:
        """Update Redshift connection properties.

        Same as RedshiftWrapper.buildUrl in dataplane package.
        """
        # Convert to IAM URL if authenticationType is IAM or aws_iam_role is present
        is_iam = (
            props.get("authenticationType", "") == "IAM"
            or additional_options.get("aws_iam_role") is not None
        )
        updated_url = url
        if is_iam and ":iam://" not in url:
            updated_url = url.replace("jdbc:redshift://", "jdbc:redshift:iam://")

        # Add SSL properties if needed
        use_ssl = props.get(SparkOptionsKey.ENFORCE_SSL, props.get("ssl", "")).lower() == "true"
        if use_ssl:
            ssl_properties = (
                JdbcConnectionProperties.get_driver_connection_properties(
                    "redshift"
                ).get_ssl_with_dn_match_properties()
                if props.get("sslmode") == "verify-full"
                else JdbcConnectionProperties.get_driver_connection_properties(
                    "redshift"
                ).get_ssl_properties()
            )
            updated_url = JDBCUrlUpdateHelper._add_url_params(updated_url, ssl_properties)

        # Process IAM based JDBC URL options https://docs.aws.amazon.com/redshift/latest/mgmt/generating-iam-credentials-configure-jdbc-odbc.html
        # A valid JDBC URL is either jdbc:redshift://<cluster>:<region> or jdbc:redshift:iam://<cluster>:<region>
        if len(updated_url.split(":")) > 2 and updated_url.split(":")[2] == "iam":
            options = {}
            # basic use case
            if additional_options.get("DbUser"):
                options["DbUser"] = additional_options["DbUser"]

            if options:
                updated_url = JDBCUrlUpdateHelper._add_url_params(updated_url, options)

        updated_props = JDBCUrlUpdateHelper._create_result_with_url(props, updated_url)

        if is_iam and additional_options.get("aws_iam_role"):
            updated_props["aws_iam_role"] = additional_options["aws_iam_role"]

        return updated_props

    @staticmethod
    def _update_url_mongodb(
        url: str, props: Dict[str, str], additional_options: Dict[str, str]
    ) -> Dict[str, str]:
        """Update MongoDB/DocumentDB connection properties.

        Same as MongoConnection.updateOptionsUri in dataplane package.
        """
        # mongodb uses different key name than regular jdbc connections, e.g connection.uri vs url, username vs user,
        # so need to translate the property keys first
        # same logic in glueContext.processingMongoDbConnectionOptions()
        mongodb_props = {
            JDBCUrlUpdateHelper.MONGO_CONNECTION_TRANSLATION_MAP.get(k, k): v
            for k, v in props.items()
        }

        disable_update_uri = additional_options.get("disableUpdateUri", "false")
        updated_url = url

        JDBCUrlUpdateHelper._validate_mongo_uri(disable_update_uri, updated_url)

        if disable_update_uri == "true":
            return mongodb_props

        username = mongodb_props.get("username", "")
        password = mongodb_props.get(SparkOptionsKey.PASSWORD, "")

        # STEP-2 if Both UserName and password exists , prepare the URL by appending UserName and password in it
        if username and password:
            url_parts = updated_url.split("://")
            # The special characters in username and password must be encoded.
            # According to this reference: https://docs.mongodb.com/manual/reference/connection-string/, the
            # following characters must be encoded to form a valid Mongo URI.
            encoded_username = quote(username, safe="")
            encoded_password = quote(password, safe="")
            updated_url = f"{url_parts[0]}://{encoded_username}:{encoded_password}@{url_parts[1]}"

        # STEP-3 Below Options cannot be passed directly to the connector (https://www.mongodb.com/docs/spark-connector/current/configuration/write/) but these are important for Mongo DB that's why we are using URL append
        # Add SSL parameters
        if mongodb_props.get("ssl", "false") == "true" and "ssl=true" not in updated_url:
            ssl_params = {"ssl": "true"}
            if additional_options.get("ssl.domain_match", "true") != "true":
                ssl_params["sslInvalidHostNameAllowed"] = "true"
            updated_url = JDBCUrlUpdateHelper._add_mongo_url_params(updated_url, ssl_params)

        # Add retryWrites parameter
        if "retryWrites" in additional_options and "retryWrites" not in updated_url:
            retry_params = {"retryWrites": additional_options["retryWrites"]}
            updated_url = JDBCUrlUpdateHelper._add_mongo_url_params(updated_url, retry_params)

        result = mongodb_props.copy()
        result["connection.uri"] = updated_url
        if "ssl" in result:
            del result["ssl"]

        return result

    @staticmethod
    def _add_mongo_url_params(url: str, params: Dict[str, str]) -> str:
        """Add parameters to MongoDB URL with /? separator for first param."""
        if not params:
            return url

        new_url = url
        for key, value in params.items():
            sep = "&" if "/?" in new_url else "/?"
            new_url = f"{new_url}{sep}{key}={value}"
        return new_url

    @staticmethod
    def _validate_mongo_uri(disable_update_uri: str, url: str) -> bool:
        """Validate MongoDB URI format."""
        if disable_update_uri == "true":
            if not (url.startswith("mongodb://") or url.startswith("mongodb+srv://")):
                raise RuntimeError(
                    f"Mongo/DocumentDB URL {url} should start with 'mongodb://' or 'mongodb+srv://'"
                )
        else:
            pattern = (
                r"^mongodb(\+srv)?://(?P<host>.*)(:(?P<port>\d+))?(?:/|/(?P<database>[^/]*))?/?$"
            )
            if not re.match(pattern, url):
                raise RuntimeError(f"Mongo/DocumentDB connection URL {url} is not supported.")
        return True
