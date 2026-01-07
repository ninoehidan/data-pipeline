"""
Test additional options validator for security.
"""

import unittest

from sagemaker_studio.connections.glue_connection_lib.connections.utils.additional_options_validator import (
    AdditionalOptionsValidator,
)


class TestAdditionalOptionsValidator(unittest.TestCase):
    """Test additional options validation."""

    def test_injection_blocked(self):
        """Test that malicious injection is blocked."""
        malicious_options = {"retryWrites": "false&host=attacker.com&port=1337&admin=true"}

        with self.assertRaises(ValueError) as context:
            AdditionalOptionsValidator.validate("mongodb", malicious_options)

        self.assertIn("Invalid value", str(context.exception))

    def test_valid_options_accepted(self):
        """Test that valid options are accepted."""
        valid_options = {
            "retryWrites": "false",
            "disableUpdateUri": "true",
            "unknownParam": "anyValue",  # Unknown params are allowed, only known ones are validated
        }

        # Should not raise exception
        AdditionalOptionsValidator.validate("mongodb", valid_options)

    def test_unknown_parameters_allowed(self):
        """Test that unknown parameters are allowed (not validated)."""
        unknown_options = {
            "customParam": "customValue",
            "anotherParam": "with&special=chars",  # This would be injection but param is unknown
        }

        # Should not raise exception - unknown params bypass validation
        AdditionalOptionsValidator.validate("mongodb", unknown_options)

    def test_case_sensitive_booleans(self):
        """Test that both True/False and true/false are accepted."""
        # Test lowercase
        lowercase_options = {"retryWrites": "true", "disableUpdateUri": "false"}
        AdditionalOptionsValidator.validate("mongodb", lowercase_options)

        # Test uppercase
        uppercase_options = {"retryWrites": "True", "ssl.domain_match": "False"}
        AdditionalOptionsValidator.validate("mongodb", uppercase_options)

    def test_dbuser_validation(self):
        """Test DbUser parameter validation."""
        # Valid DbUser
        valid_options = {"DbUser": "validuser123"}
        AdditionalOptionsValidator.validate("redshift", valid_options)

        # Invalid DbUser with injection attempt
        invalid_options = {"DbUser": "user&malicious=param"}
        with self.assertRaises(ValueError):
            AdditionalOptionsValidator.validate("redshift", invalid_options)


if __name__ == "__main__":
    unittest.main()
