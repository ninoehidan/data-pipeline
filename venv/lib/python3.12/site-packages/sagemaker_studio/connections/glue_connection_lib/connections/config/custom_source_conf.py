"""Custom Source Configuration class."""

from typing import Dict, Optional

from .connection_conf import _ConnectionConf


class CustomSourceConf(_ConnectionConf):
    """Custom source connection configuration."""

    def __init__(
        self,
        connection_type: str,
        class_name: str,
        url: str,
        user: Optional[str],
        password: Optional[str],
        secret_id: str,
    ):
        super().__init__()
        self.connection_type = connection_type
        self.class_name = class_name
        self.url = url
        self.user = user
        self.password = password
        self.secret_id = secret_id

    def as_map(self) -> Dict[str, str]:
        """Convert to dictionary format for Spark options."""
        option_map = {
            "connectionType": self.connection_type,
            "className": self.class_name,
            "url": self.url,
            "secretId": self.secret_id,
        }
        # Only add user and password if they are not null (for IAM authentication, they should be excluded)
        if self.user is not None and self.password is not None:
            option_map["user"] = self.user
            option_map["password"] = self.password

        option_map.update(self._map)
        return option_map
