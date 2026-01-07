"""
Helper functions for secret key manipulation.
"""

import base64
import json
from typing import Dict, Optional

from ..constants import ConnectionPropertyKey


def get_connection_specific_secret_map(
    secret_map: Optional[Dict[str, str]],
    connection_type: Optional[str],
    auth_type: Optional[str] = None,
) -> Dict[str, str]:
    """
    Translate standard keys in the secrets into connection understandable keys.

    Args:
        secret_map: Dictionary containing secret key-value pairs
        connection_type: Type of connection (e.g., 'snowflake', 'mysql', etc.)
        auth_type: Authentication type (e.g., 'OAUTH2', 'BASIC', etc.)

    Returns:
        Dictionary with connection-specific secret keys
    """
    if not secret_map:
        return {}

    if not connection_type:
        return secret_map.copy()

    # Create a mutable copy
    result_map = secret_map.copy()

    connection_type_upper = connection_type.upper()

    if connection_type_upper == "SNOWFLAKE":
        if auth_type and auth_type.upper() == "OAUTH2":
            add_oauth2_token_keys(connection_type, result_map)
        else:
            # For basic authentication, use standard username/password mapping
            add_connection_type_secret_keys("sfUser", "sfPassword", result_map)
    elif connection_type_upper in [
        "JDBC",
        "MYSQL",
        "SQLSERVER",
        "ORACLE",
        "POSTGRESQL",
        "REDSHIFT",
        "DOCUMENTDB",
        "MONGODB",
    ]:
        add_connection_type_secret_keys("username", "password", result_map)
    elif connection_type_upper in ["VERTICA", "SAPHANA", "TERADATA", "AZURESQL"]:
        add_connection_type_secret_keys("user", "password", result_map)
    elif connection_type_upper == "OPENSEARCH":
        add_connection_type_secret_keys(
            "opensearch.net.http.auth.user", "opensearch.net.http.auth.pass", result_map
        )
    elif connection_type_upper == "BIGQUERY":
        if "credentials" not in result_map:
            secret_string = json.dumps(result_map)
            result_map["credentials"] = base64.b64encode(secret_string.encode("utf-8")).decode(
                "utf-8"
            )
    elif connection_type_upper == "DYNAMODB":
        # DDB uses IAM, no secret key transformation needed
        pass
    # For any other v2 types, use secret map as is

    return result_map


def add_connection_type_secret_keys(
    username_key: str, password_key: str, secret_map: Dict[str, str]
) -> None:
    """
    Add connection-specific username and password keys to the secret map.

    Args:
        username_key: The connection-specific username key
        password_key: The connection-specific password key
        secret_map: The secret map to modify in-place
    """
    # Handle USERNAME
    if ConnectionPropertyKey.USERNAME in secret_map:
        secret_map[username_key] = secret_map[ConnectionPropertyKey.USERNAME]
    else:
        username_key_found = find_key_ignore_case(secret_map, ConnectionPropertyKey.USERNAME)
        if username_key_found:
            secret_map[username_key] = secret_map[username_key_found]

    # Handle PASSWORD
    if ConnectionPropertyKey.PASSWORD in secret_map:
        secret_map[password_key] = secret_map[ConnectionPropertyKey.PASSWORD]
    else:
        password_key_found = find_key_ignore_case(secret_map, ConnectionPropertyKey.PASSWORD)
        if password_key_found:
            secret_map[password_key] = secret_map[password_key_found]


def add_oauth2_token_keys(connection_type: str, secret_map: Dict[str, str]) -> None:
    """
    Add OAuth2 token keys specific to the connection type.

    Args:
        connection_type: The connection type (e.g., 'SNOWFLAKE')
        secret_map: The secret map to modify in-place
    """
    connection_type_upper = connection_type.upper()

    if connection_type_upper == "SNOWFLAKE":
        if "ACCESS_TOKEN" in secret_map:
            secret_map["sftoken"] = secret_map["ACCESS_TOKEN"]


def find_key_ignore_case(secret_map: Dict[str, str], target_key: str) -> Optional[str]:
    """
    Find a key in the map ignoring case.

    Args:
        secret_map: Dictionary to search in
        target_key: Key to find (case-insensitive)

    Returns:
        The actual key if found, None otherwise
    """
    target_lower = target_key.lower()
    for key in secret_map.keys():
        if key.lower() == target_lower:
            return key
    return None
