"""
JDBC Connection Properties - Python equivalent of JdbcConnectionProperties.java

Note: Environment variables may be different between Glue and EMR. These environment variables
are for now as per Glue context. As Sagemaker notebooks will use EMR, adding environment
variables as per EMR context may be needed in the future.
"""

from enum import Enum
from typing import Dict


def _get_jvm_property(property_name: str, default: str = "") -> str:
    """Get property from JVM system properties via Spark context."""
    try:
        from pyspark import SparkContext

        sc = SparkContext._active_spark_context
        if sc:
            return sc._gateway.jvm.java.lang.System.getProperty(property_name, default)
    except (ImportError, AttributeError):
        pass
    return default


class JdbcConnectionProperties(Enum):
    """JDBC connection properties for different database vendors."""

    MYSQL = {
        "no_ssl_properties": {},
        "ssl_properties": {"useSSL": "true"},
        "ssl_with_dn_match_properties": {
            "useSSL": "true",
            "verifyServerCertificate": "true",
            "trustCertificateKeyStoreUrl": _get_jvm_property("RDS_TRUSTSTORE_URL", ""),
            "trustCertificateKeyStorePassword": "amazon",
        },
        "ssl_properties_with_tls1_2": {"useSSL": "true", "enabledTLSProtocols": "TLSv1.2"},
        "ssl_properties_legacy_with_tls1_2": {"useSSL": "true", "tlsVersions": "TLSv1.2"},
        "ssl_dn_match_properties_with_tls1_2": {
            "useSSL": "true",
            "verifyServerCertificate": "true",
            "trustCertificateKeyStoreUrl": _get_jvm_property("RDS_TRUSTSTORE_URL", ""),
            "trustCertificateKeyStorePassword": "amazon",
            "enabledTLSProtocols": "TLSv1.2",
        },
        "ssl_dn_match_properties_legacy_with_tls1_2": {
            "useSSL": "true",
            "verifyServerCertificate": "true",
            "trustCertificateKeyStoreUrl": _get_jvm_property("RDS_TRUSTSTORE_URL", ""),
            "trustCertificateKeyStorePassword": "amazon",
            "tlsVersions": "TLSv1.2",
        },
    }

    POSTGRESQL = {
        "no_ssl_properties": {"loginTimeout": "10"},
        "ssl_properties": {"loginTimeout": "10", "sslmode": "require"},
        "ssl_with_dn_match_properties": {
            "loginTimeout": "10",
            "sslmode": "verify-full",
            "sslrootcert": _get_jvm_property("RDS_ROOT_CERT_PATH", ""),
        },
        "ssl_properties_with_tls1_2": {
            "loginTimeout": "10",
            "sslmode": "require",
            "ssl_min_protocol_version": "TLSv1.2",
        },
        "ssl_properties_legacy_with_tls1_2": {},
        "ssl_dn_match_properties_with_tls1_2": {
            "loginTimeout": "10",
            "sslmode": "verify-full",
            "sslrootcert": _get_jvm_property("RDS_ROOT_CERT_PATH", ""),
            "ssl_min_protocol_version": "TLSv1.2",
        },
        "ssl_dn_match_properties_legacy_with_tls1_2": {},
    }

    REDSHIFT = {
        "no_ssl_properties": {},
        "ssl_properties": {"ssl": "true", "sslmode": "verify-ca"},
        "ssl_with_dn_match_properties": {
            "ssl": "true",
            "sslmode": "verify-full",
            "sslrootcert": _get_jvm_property("REDSHIFT_ROOT_CERT_PATH", ""),
        },
        "ssl_properties_with_tls1_2": {
            "ssl": "true",
            "sslmode": "verify-ca",
            "ssl_min_protocol_version": "TLSv1.2",
        },
        "ssl_properties_legacy_with_tls1_2": {},
        "ssl_dn_match_properties_with_tls1_2": {
            "loginTimeout": "10",
            "sslmode": "verify-full",
            "sslrootcert": _get_jvm_property("REDSHIFT_ROOT_CERT_PATH", ""),
            "ssl_min_protocol_version": "TLSv1.2",
        },
        "ssl_dn_match_properties_legacy_with_tls1_2": {},
    }

    SQLSERVER = {
        "no_ssl_properties": {},
        "ssl_properties": {"encrypt": "true", "trustServerCertificate": "false"},
        "ssl_with_dn_match_properties": {"encrypt": "true", "trustServerCertificate": "false"},
        "ssl_properties_with_tls1_2": {
            "encrypt": "true",
            "trustServerCertificate": "false",
            "enabledTLSProtocols": "TLSv1.2",
        },
        "ssl_properties_legacy_with_tls1_2": {
            "encrypt": "true",
            "trustServerCertificate": "false",
            "sslProtocol": "TLSv1.2",
        },
        "ssl_dn_match_properties_with_tls1_2": {
            "encrypt": "true",
            "trustServerCertificate": "false",
            "enabledTLSProtocols": "TLSv1.2",
        },
        "ssl_dn_match_properties_legacy_with_tls1_2": {
            "encrypt": "true",
            "trustServerCertificate": "false",
            "sslProtocol": "TLSv1.2",
        },
    }

    ORACLE = {
        "no_ssl_properties": {},
        "ssl_properties": {
            "oracle.jdbc.J2EE13Compliant": "true",
            "javax.net.ssl.trustStore": _get_jvm_property("javax.net.ssl.trustStore", ""),
            "javax.net.ssl.trustStoreType": "JKS",
            "javax.net.ssl.trustStorePassword": "amazon",
        },
        "ssl_with_dn_match_properties": {
            "oracle.jdbc.J2EE13Compliant": "true",
            "javax.net.ssl.trustStore": _get_jvm_property("javax.net.ssl.trustStore", ""),
            "javax.net.ssl.trustStoreType": "JKS",
            "javax.net.ssl.trustStorePassword": "amazon",
            "oracle.net.ssl_server_dn_match": "TRUE",
        },
        "ssl_properties_with_tls1_2": {
            "oracle.jdbc.J2EE13Compliant": "true",
            "javax.net.ssl.trustStore": _get_jvm_property("javax.net.ssl.trustStore", ""),
            "javax.net.ssl.trustStoreType": "JKS",
            "javax.net.ssl.trustStorePassword": "amazon",
            "oracle.net.ssl_version": "1.2",
        },
        "ssl_properties_legacy_with_tls1_2": {},
        "ssl_dn_match_properties_with_tls1_2": {
            "oracle.jdbc.J2EE13Compliant": "true",
            "javax.net.ssl.trustStore": _get_jvm_property("javax.net.ssl.trustStore", ""),
            "javax.net.ssl.trustStoreType": "JKS",
            "javax.net.ssl.trustStorePassword": "amazon",
            "oracle.net.ssl_server_dn_match": "TRUE",
            "oracle.net.ssl_version": "1.2",
        },
        "ssl_dn_match_properties_legacy_with_tls1_2": {},
    }

    SNOWFLAKE = {  # type: ignore[var-annotated]
        "no_ssl_properties": {},
        "ssl_properties": {},
        "ssl_with_dn_match_properties": {},
        "ssl_properties_with_tls1_2": {},
        "ssl_properties_legacy_with_tls1_2": {},
        "ssl_dn_match_properties_with_tls1_2": {},
        "ssl_dn_match_properties_legacy_with_tls1_2": {},
    }

    @staticmethod
    def get_driver_connection_properties(driver_name: str) -> "JdbcConnectionProperties":
        """Get connection properties by driver name."""
        try:
            return JdbcConnectionProperties[driver_name.upper()]
        except KeyError:
            raise ValueError(f"Unsupported driver: {driver_name}")

    def get_no_ssl_properties(self) -> Dict[str, str]:
        """Get properties for non-SSL connections."""
        return self.value["no_ssl_properties"]

    def get_ssl_properties(self) -> Dict[str, str]:
        """Get properties for SSL connections."""
        return self.value["ssl_properties"]

    def get_ssl_with_dn_match_properties(self) -> Dict[str, str]:
        """Get properties for SSL connections with domain name matching."""
        return self.value["ssl_with_dn_match_properties"]

    def get_ssl_properties_with_tls1_2(self) -> Dict[str, str]:
        """Get properties for SSL connections with TLS 1.2."""
        return self.value["ssl_properties_with_tls1_2"]

    def get_ssl_properties_legacy_with_tls1_2(self) -> Dict[str, str]:
        """Get legacy properties for SSL connections with TLS 1.2."""
        return self.value["ssl_properties_legacy_with_tls1_2"]

    def get_ssl_dn_match_properties_with_tls1_2(self) -> Dict[str, str]:
        """Get properties for SSL connections with domain name matching and TLS 1.2."""
        return self.value["ssl_dn_match_properties_with_tls1_2"]

    def get_ssl_dn_match_properties_legacy_with_tls1_2(self) -> Dict[str, str]:
        """Get legacy properties for SSL connections with domain name matching and TLS 1.2."""
        return self.value["ssl_dn_match_properties_legacy_with_tls1_2"]
