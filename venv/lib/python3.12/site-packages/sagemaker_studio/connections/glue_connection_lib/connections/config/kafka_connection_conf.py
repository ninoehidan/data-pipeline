"""Kafka Connection Configuration class."""

from typing import Dict

from ..constants import ConnectionPropertyKey
from .connection_conf import _ConnectionConf


class KafkaConnectionConf(_ConnectionConf):
    """Kafka connection configuration."""

    def __init__(
        self,
        bootstrap_servers: str,
        security_protocol: str,
        kafka_client_keystore_password: str,
        kafka_client_key_password: str,
    ):
        super().__init__()
        self.bootstrap_servers = bootstrap_servers
        self.security_protocol = security_protocol
        self.kafka_client_keystore_password = kafka_client_keystore_password
        self.kafka_client_key_password = kafka_client_key_password

    def as_map(self) -> Dict[str, str]:
        """Convert to dictionary format for Spark options."""
        option_map = {
            "bootstrap.servers": self.bootstrap_servers,
            "securityProtocol": self.security_protocol,
            ConnectionPropertyKey.KAFKA_CLIENT_KEYSTORE_PASSWORD: self.kafka_client_keystore_password,
            ConnectionPropertyKey.KAFKA_CLIENT_KEY_PASSWORD: self.kafka_client_key_password,
        }

        option_map.update(self._map)
        return option_map
