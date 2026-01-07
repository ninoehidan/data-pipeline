"""
Unit tests for complete JDBC URL utilities.
"""

import unittest

from sagemaker_studio.connections.glue_connection_lib.connections.utils.jdbc_url import JdbcUrl
from sagemaker_studio.connections.glue_connection_lib.connections.utils.jdbc_vendor import (
    JdbcVendor,
)


class TestJdbcUrl(unittest.TestCase):
    """Test cases for complete JdbcUrl class."""

    def test_from_url_mysql(self):
        """Test parsing MySQL JDBC URL."""
        url = "jdbc:mysql://localhost:3306/testdb"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.MYSQL)
        self.assertEqual(jdbc_url.host, "localhost")
        self.assertEqual(jdbc_url.port, 3306)
        self.assertEqual(jdbc_url.database, "testdb")

    def test_from_url_postgresql(self):
        """Test parsing PostgreSQL JDBC URL."""
        url = "jdbc:postgresql://myhost:5432/mydb"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.POSTGRESQL)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 5432)
        self.assertEqual(jdbc_url.database, "mydb")

    def test_from_url_redshift(self):
        """Test parsing Redshift JDBC URL."""
        url = "jdbc:redshift://cluster.abc123.us-east-1.redshift.amazonaws.com:5439/dev"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.REDSHIFT)
        self.assertEqual(jdbc_url.host, "cluster.abc123.us-east-1.redshift.amazonaws.com")
        self.assertEqual(jdbc_url.port, 5439)
        self.assertEqual(jdbc_url.database, "dev")

    def test_from_url_oracle_thin(self):
        """Test parsing Oracle thin JDBC URL."""
        url = "jdbc:oracle:thin://@myhost:1521/myservice"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.ORACLE)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1521)

    def test_from_url_oracle_sid(self):
        """Test parsing Oracle SID JDBC URL."""
        url = "jdbc:oracle:thin://@myhost:1521:mysid"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.ORACLE)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1521)

    def test_from_url_sqlserver_basic(self):
        """Test parsing SQL Server basic JDBC URL."""
        url = "jdbc:sqlserver://myhost:1433;databaseName=mydb"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.SQLSERVER)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1433)
        self.assertEqual(jdbc_url.database, "mydb")

    def test_from_url_sqlserver_slash(self):
        """Test parsing SQL Server slash format JDBC URL."""
        url = "jdbc:sqlserver://myhost:1433/mydb"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.SQLSERVER)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1433)
        self.assertEqual(jdbc_url.database, "mydb")

    def test_from_url_sqlserver_instance(self):
        """Test parsing SQL Server with instance name."""
        url = "jdbc:sqlserver://myhost;instanceName=SQLEXPRESS:1433;databaseName=mydb"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.SQLSERVER)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1433)
        self.assertEqual(jdbc_url.database, "mydb")
        self.assertEqual(jdbc_url.instance, "SQLEXPRESS")

    def test_from_url_snowflake(self):
        """Test parsing Snowflake JDBC URL."""
        url = "jdbc:snowflake://myaccount.snowflakecomputing.com/?user=myuser&db=mydb&role=myrole&warehouse=mywarehouse"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.SNOWFLAKE)
        self.assertEqual(jdbc_url.account, "myaccount")
        self.assertEqual(jdbc_url.user, "myuser")
        self.assertEqual(jdbc_url.database, "mydb")
        self.assertEqual(jdbc_url.role, "myrole")
        self.assertEqual(jdbc_url.warehouse, "mywarehouse")

    def test_from_url_mongodb(self):
        """Test parsing MongoDB JDBC URL."""
        url = "mongodb://myhost:27017/mydb"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.MONGODB)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 27017)
        self.assertEqual(jdbc_url.database, "mydb")

    # Error handling tests
    def test_from_url_invalid_format(self):
        """Test error for completely invalid URL format."""
        with self.assertRaises(ValueError):
            JdbcUrl.from_url("not-a-jdbc-url")

    def test_from_url_unsupported_vendor(self):
        """Test error for unsupported vendor."""
        with self.assertRaises(KeyError):
            JdbcUrl.from_url("jdbc:unsupported://host:1234/db")

    # Oracle advanced patterns
    def test_from_url_oracle_tns(self):
        """Test parsing Oracle TNS format."""
        url = "jdbc:oracle:thin:@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=myhost)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=myservice)))"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.ORACLE)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1521)
        self.assertEqual(jdbc_url.database, "myservice")

    def test_from_url_oracle_no_driver(self):
        """Test parsing Oracle URL without driver specification."""
        url = "jdbc:oracle://myhost:1521/myservice"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.ORACLE)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1521)
        self.assertEqual(jdbc_url.database, "myservice")

    def test_from_url_oracle_no_database(self):
        """Test parsing Oracle URL without database."""
        url = "jdbc:oracle:thin://@myhost:1521"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.ORACLE)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1521)
        self.assertIsNone(jdbc_url.database)

    # SQL Server advanced patterns
    def test_from_url_sqlserver_with_application(self):
        """Test parsing SQL Server with application name."""
        url = "jdbc:sqlserver://myhost:1433;databaseName=mydb;applicationName=myapp"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.SQLSERVER)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1433)
        self.assertEqual(jdbc_url.database, "mydb")
        self.assertEqual(jdbc_url.application, "myapp")

    def test_from_url_sqlserver_instance_with_app(self):
        """Test parsing SQL Server with instance and application name."""
        url = "jdbc:sqlserver://myhost;instanceName=SQLEXPRESS:1433;databaseName=mydb;applicationName=myapp"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.SQLSERVER)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1433)
        self.assertEqual(jdbc_url.database, "mydb")
        self.assertEqual(jdbc_url.instance, "SQLEXPRESS")
        self.assertEqual(jdbc_url.application, "myapp")

    def test_from_url_sqlserver_no_database(self):
        """Test parsing SQL Server without database."""
        url = "jdbc:sqlserver://myhost:1433"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.SQLSERVER)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 1433)
        self.assertIsNone(jdbc_url.database)

    # MongoDB Atlas
    def test_from_url_mongodb_atlas(self):
        """Test parsing MongoDB Atlas URL."""
        url = "mongodb+srv://cluster.abc123.mongodb.net/mydb"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.MONGODB)
        self.assertEqual(jdbc_url.host, "cluster.abc123.mongodb.net")
        self.assertEqual(jdbc_url.port, 0)  # Atlas doesn't use explicit port
        self.assertEqual(jdbc_url.database, "mydb")

    def test_from_url_mongodb_no_database(self):
        """Test parsing MongoDB URL without database."""
        url = "mongodb://myhost:27017"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.MONGODB)
        self.assertEqual(jdbc_url.host, "myhost")
        self.assertEqual(jdbc_url.port, 27017)
        self.assertIsNone(jdbc_url.database)

    # Snowflake variations
    def test_from_url_snowflake_minimal(self):
        """Test parsing minimal Snowflake URL."""
        url = "jdbc:snowflake://myaccount.snowflakecomputing.com/?user=myuser&db=mydb&role=myrole"
        jdbc_url = JdbcUrl.from_url(url)

        self.assertEqual(jdbc_url.vendor, JdbcVendor.SNOWFLAKE)
        self.assertEqual(jdbc_url.account, "myaccount")
        self.assertEqual(jdbc_url.user, "myuser")
        self.assertEqual(jdbc_url.database, "mydb")
        self.assertEqual(jdbc_url.role, "myrole")
        self.assertIsNone(jdbc_url.warehouse)

    # Connection URL generation tests
    def test_get_connection_url_mysql(self):
        """Test generating MySQL connection URL."""
        jdbc_url = JdbcUrl(vendor=JdbcVendor.MYSQL, host="localhost", port=3306, database="testdb")

        result = jdbc_url.get_connection_url()
        self.assertEqual(result, "jdbc:mysql://localhost:3306/testdb")

    def test_get_connection_url_oracle_ssl(self):
        """Test generating Oracle SSL connection URL."""
        jdbc_url = JdbcUrl(
            vendor=JdbcVendor.ORACLE,
            host="myhost.rds.amazonaws.com",
            port=1521,
            database="myservice",
        )

        result = jdbc_url.get_connection_url(use_ssl=True, use_domain_match=True)
        expected = (
            "jdbc:oracle:thin:@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=myhost.rds.amazonaws.com)(PORT=1521))"
            "(CONNECT_DATA=(SERVICE_NAME=myservice))"
            '(SECURITY=(SSL_SERVER_CERT_DN="C=US,ST=Washington,L=Seattle,O=Amazon.com,OU=RDS,CN=myhost.rds.amazonaws.com")))'
        )
        self.assertEqual(result, expected)

    def test_get_connection_url_snowflake(self):
        """Test generating Snowflake connection URL."""
        jdbc_url = JdbcUrl(
            vendor=JdbcVendor.SNOWFLAKE,
            account="myaccount",
            user="myuser",
            database="mydb",
            role="myrole",
            warehouse="mywarehouse",
        )

        result = jdbc_url.get_connection_url()
        expected = "jdbc:snowflake://myaccount.snowflakecomputing.com/?user=myuser&db=mydb&role=myrole&warehouse=mywarehouse"
        self.assertEqual(result, expected)

    def test_get_connection_url_sqlserver(self):
        """Test generating SQL Server connection URL."""
        jdbc_url = JdbcUrl(
            vendor=JdbcVendor.SQLSERVER,
            host="myhost",
            port=1433,
            database="mydb",
            application="myapp",
        )

        result = jdbc_url.get_connection_url()
        expected = "jdbc:sqlserver://myhost:1433;database={mydb};applicationName={myapp}"
        self.assertEqual(result, expected)

    def test_get_connection_url_oracle_no_ssl(self):
        """Test Oracle connection URL without SSL."""
        jdbc_url = JdbcUrl(vendor=JdbcVendor.ORACLE, host="myhost", port=1521, database="myservice")

        result = jdbc_url.get_connection_url()
        self.assertEqual(result, "jdbc:oracle:thin://@myhost:1521/myservice")

    def test_get_connection_url_oracle_ssl_non_rds(self):
        """Test Oracle SSL connection URL for non-RDS host."""
        jdbc_url = JdbcUrl(
            vendor=JdbcVendor.ORACLE, host="myhost.example.com", port=1521, database="myservice"
        )

        result = jdbc_url.get_connection_url(use_ssl=True, use_domain_match=True)
        expected = (
            "jdbc:oracle:thin:@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=myhost.example.com)(PORT=1521))"
            "(CONNECT_DATA=(SERVICE_NAME=myservice))"
            '(SECURITY=(SSL_SERVER_CERT_DN="CN=myhost.example.com")))'
        )
        self.assertEqual(result, expected)

    def test_get_connection_url_oracle_ssl_no_database(self):
        """Test Oracle SSL connection URL without database."""
        jdbc_url = JdbcUrl(vendor=JdbcVendor.ORACLE, host="myhost.rds.amazonaws.com", port=1521)

        result = jdbc_url.get_connection_url(use_ssl=True, use_domain_match=True)
        expected = (
            "jdbc:oracle:thin:@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=myhost.rds.amazonaws.com)(PORT=1521))"
            '(SECURITY=(SSL_SERVER_CERT_DN="C=US,ST=Washington,L=Seattle,O=Amazon.com,OU=RDS,CN=myhost.rds.amazonaws.com")))'
        )
        self.assertEqual(result, expected)

    def test_get_connection_url_oracle_ssl_no_domain_match(self):
        """Test Oracle SSL connection URL without domain matching."""
        jdbc_url = JdbcUrl(
            vendor=JdbcVendor.ORACLE,
            host="myhost.rds.amazonaws.com",
            port=1521,
            database="myservice",
        )

        result = jdbc_url.get_connection_url(use_ssl=True, use_domain_match=False)
        expected = (
            "jdbc:oracle:thin:@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=myhost.rds.amazonaws.com)(PORT=1521))"
            "(CONNECT_DATA=(SERVICE_NAME=myservice)))"
        )
        self.assertEqual(result, expected)

    def test_get_connection_url_oracle_no_ssl_no_database(self):
        """Test Oracle connection URL without SSL and without database."""
        jdbc_url = JdbcUrl(vendor=JdbcVendor.ORACLE, host="myhost", port=1521)

        result = jdbc_url.get_connection_url()
        self.assertEqual(result, "jdbc:oracle:thin://@myhost:1521/")

    def test_get_connection_url_sqlserver_domain_match(self):
        """Test SQL Server connection URL with domain matching."""
        jdbc_url = JdbcUrl(vendor=JdbcVendor.SQLSERVER, host="myhost", port=1433, database="mydb")

        result = jdbc_url.get_connection_url(use_domain_match=True)
        expected = "jdbc:sqlserver://myhost:1433;database={mydb};hostNameInCertificate=myhost"
        self.assertEqual(result, expected)

    def test_get_connection_url_sqlserver_instance(self):
        """Test SQL Server connection URL with instance name."""
        jdbc_url = JdbcUrl(
            vendor=JdbcVendor.SQLSERVER,
            host="myhost",
            port=1433,
            database="mydb",
            instance="SQLEXPRESS",
        )

        result = jdbc_url.get_connection_url()
        expected = "jdbc:sqlserver://myhost;instanceName={SQLEXPRESS}:1433;database={mydb}"
        self.assertEqual(result, expected)

    def test_get_connection_url_mongodb_atlas(self):
        """Test MongoDB Atlas connection URL generation."""
        jdbc_url = JdbcUrl(
            vendor=JdbcVendor.MONGODB,
            host="cluster.abc123.mongodb.net",
            port=0,  # Atlas doesn't use explicit port
            database="mydb",
        )

        result = jdbc_url.get_connection_url()
        self.assertEqual(result, "mongodb+srv://cluster.abc123.mongodb.net/mydb")

    def test_get_connection_url_mongodb_with_port(self):
        """Test MongoDB connection URL generation with explicit port."""
        jdbc_url = JdbcUrl(
            vendor=JdbcVendor.MONGODB,
            host="localhost",
            port=27017,
            database="mydb",
        )

        result = jdbc_url.get_connection_url()
        self.assertEqual(result, "mongodb://localhost:27017/mydb")

    def test_get_connection_url_snowflake_minimal(self):
        """Test Snowflake connection URL with minimal parameters."""
        jdbc_url = JdbcUrl(vendor=JdbcVendor.SNOWFLAKE, account="myaccount", user="myuser")

        result = jdbc_url.get_connection_url()
        self.assertEqual(result, "jdbc:snowflake://myaccount.snowflakecomputing.com/?user=myuser")

    def test_get_connection_url_unsupported_vendor(self):
        """Test error for unsupported vendor in URL generation."""
        jdbc_url = JdbcUrl(vendor=JdbcVendor.DOCUMENTDB, host="host", port=1234)

        with self.assertRaises(ValueError):
            jdbc_url.get_connection_url()

    # Database name escaping tests
    def test_escape_db_name_sqlserver(self):
        """Test database name escaping for SQL Server."""
        result = JdbcUrl.escape_db_name(JdbcVendor.SQLSERVER, "mydb")
        self.assertEqual(result, "{mydb}")

        # Already escaped
        result = JdbcUrl.escape_db_name(JdbcVendor.SQLSERVER, "{mydb}")
        self.assertEqual(result, "{mydb}")

    def test_escape_db_name_other_vendors(self):
        """Test database name escaping for other vendors."""
        result = JdbcUrl.escape_db_name(JdbcVendor.MYSQL, "mydb")
        self.assertEqual(result, "mydb")

    def test_escape_db_name_empty(self):
        """Test database name escaping with empty string."""
        result = JdbcUrl.escape_db_name(JdbcVendor.SQLSERVER, "")
        self.assertEqual(result, "")

    # Getter method tests
    def test_getter_methods(self):
        """Test all getter methods."""
        jdbc_url = JdbcUrl(vendor=JdbcVendor.MYSQL, host="localhost", port=3306, database="testdb")

        self.assertEqual(jdbc_url.get_vendor(), JdbcVendor.MYSQL)
        self.assertEqual(jdbc_url.get_host(), "localhost")
        self.assertEqual(jdbc_url.get_port(), 3306)
        self.assertEqual(jdbc_url.get_database(), "testdb")


if __name__ == "__main__":
    unittest.main()
