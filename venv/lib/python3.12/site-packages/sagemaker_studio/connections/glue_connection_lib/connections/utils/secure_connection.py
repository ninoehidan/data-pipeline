"""
Connection Sanitization Utility to prevent credential exposure in logs.
"""

from typing import Any, Dict


def sanitize_connection_for_logging(connection: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize connection object for safe logging by masking sensitive fields.

    Args:
        connection: Connection object with potential credentials

    Returns:
        Sanitized connection safe for logging

    Example:
        connection = wrapper.get_resolved_connection()
        safe_connection = sanitize_connection_for_logging(connection)
        logger.debug(f"Connection details: {safe_connection}")
    """
    return _sanitize_dict(connection)


def _sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize dictionary by masking sensitive fields."""
    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        if _is_sensitive_key(key):
            # Mask sensitive keys regardless of value type
            sanitized[key] = "***MASKED***"
        elif isinstance(value, dict):
            # Only recurse if key is not sensitive
            sanitized[key] = _sanitize_dict(value)
        else:
            sanitized[key] = value
    return sanitized


def _is_sensitive_key(key: str) -> bool:
    """Check if key contains sensitive terms (case-insensitive substring matching)."""
    sensitive_terms = [
        "password",
        "pass",
        "user",
        "token",
        "secret",
        "credential",
        "key",
        "client",
        "auth",
        "principal",
        "role",
        "arn",
    ]
    return any(term in key.lower() for term in sensitive_terms)
