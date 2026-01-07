"""JDBC Configuration class."""

from typing import Dict, Optional

from ..constants import JDBC_CONNECTION_TYPES, SparkOptionsKey
from .connection_conf import _ConnectionConf


class JDBCConf(_ConnectionConf):
    """JDBC connection configuration."""

    def __init__(
        self,
        user: Optional[str],
        password: Optional[str],
        vendor: str,
        url: str,
        enforce_ssl: str,
        custom_jdbc_cert: str,
        skip_custom_jdbc_cert_validation: str,
        custom_jdbc_cert_string: str,
        full_url: str,
    ):
        super().__init__()
        self.user = user
        self.password = password
        self.vendor = vendor
        self.url = url
        self.enforce_ssl = enforce_ssl
        self.custom_jdbc_cert = custom_jdbc_cert
        self.skip_custom_jdbc_cert_validation = skip_custom_jdbc_cert_validation
        self.custom_jdbc_cert_string = custom_jdbc_cert_string
        self.full_url = full_url

    def as_map(self) -> Dict[str, str]:
        """Convert to dictionary format for Spark options."""
        if self.vendor in JDBC_CONNECTION_TYPES or self.vendor.lower() in ("mongodb", "documentdb"):
            # JDBC connections such as Redshift/Oracle etc. and MongoDB/DocumentDB
            base_map = {
                SparkOptionsKey.VENDOR: self.vendor,
                SparkOptionsKey.URL: self.url,  # Deprecated, kept for backwards compatibility
                SparkOptionsKey.FULL_URL: self.full_url,
                SparkOptionsKey.ENFORCE_SSL: self.enforce_ssl,
                SparkOptionsKey.CUSTOM_JDBC_CERT: self.custom_jdbc_cert,
                SparkOptionsKey.SKIP_CUSTOM_JDBC_CERT_VALIDATION: self.skip_custom_jdbc_cert_validation,
                SparkOptionsKey.CUSTOM_JDBC_CERT_STRING: self.custom_jdbc_cert_string,
            }
            # Only add user and password if they are not null (for IAM authentication, they should be excluded)
            if self.user is not None and self.password is not None:
                base_map[SparkOptionsKey.USER] = self.user
                base_map[SparkOptionsKey.PASSWORD] = self.password
            option_map = base_map
        else:
            # Native JDBC connections such as Saphana/Teradata etc.
            base_map = {"url": self.full_url}
            # Only add username and password if they are not null (for IAM authentication, they should be excluded)
            if self.user is not None and self.password is not None:
                base_map["username"] = self.user
                base_map["password"] = self.password
            option_map = base_map

        option_map.update(self._map)
        return option_map
