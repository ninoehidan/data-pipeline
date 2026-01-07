"""
Additional Options Validator for security.
Validates additional_options values to prevent injection attacks.
"""

import re
from typing import Dict


class AdditionalOptionsValidator:
    """Validates additional_options parameter values to prevent injection attacks."""

    # Map of ConnectionType -> additional_options_key -> additional_options_val_regex
    BOOLEAN_PATTERN = r"^(true|false)$"
    CONNECTION_TYPE_PATTERNS = {
        "mongodb": {
            "retryWrites": BOOLEAN_PATTERN,
            "ssl.domain_match": BOOLEAN_PATTERN,
            "disableUpdateUri": BOOLEAN_PATTERN,
        },
        "redshift": {
            "DbUser": r"^[a-zA-Z0-9_\-\.@]+$",
        },
    }

    @classmethod
    def validate(cls, connection_type: str, additional_options: Dict[str, str]) -> None:
        """
        Validate additional_options parameter values to prevent injection.

        Args:
            connection_type: The connection type (for logging/context)
            additional_options: Dictionary of additional options to validate

        Raises:
            ValueError: If validation fails
        """
        if not additional_options:
            return

        # Get patterns for this connection type
        connection_patterns = cls.CONNECTION_TYPE_PATTERNS.get(connection_type, {})

        for key, value in additional_options.items():
            # Validate known parameter values against expected patterns
            if key in connection_patterns:
                pattern = connection_patterns[key]
                # Convert boolean values to lowercase for validation
                test_value = (
                    str(value).lower()
                    if key in ["retryWrites", "ssl.domain_match", "disableUpdateUri"]
                    else str(value)
                )
                if not re.match(pattern, test_value):
                    raise ValueError(
                        f"Invalid value for {connection_type} connection: "
                        f"Parameter '{key}' has invalid value '{value}'"
                    )
