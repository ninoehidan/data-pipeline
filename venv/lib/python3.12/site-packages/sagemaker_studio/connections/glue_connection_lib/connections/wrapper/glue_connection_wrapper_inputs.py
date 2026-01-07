"""
Glue Connection Wrapper Inputs.
Input data class for wrapper initialization.
"""

from dataclasses import dataclass
from typing import Any, Dict

from botocore.client import BaseClient


@dataclass
class GlueConnectionWrapperInputs:
    """
    Input parameters for GlueConnectionWrapper.

    This class contains all the necessary inputs to create and configure
    a Glue connection wrapper, including the connection object, additional options,
    and AWS clients.

    The connection parameter should be the AWS Glue Connection object as returned by:
    boto3.client('glue').get_connection(Name='connection-name', ApplyOverrideForComputeEnvironment='SPARK')['Connection']
    """

    connection: Dict[str, Any]  # AWS Glue Connection object from boto3
    kms_client: BaseClient  # KMS client for encryption/decryption
    secrets_manager_client: BaseClient  # Secrets Manager client for secret retrieval
    additional_options: Dict[
        str, str
    ]  # Additional connection options for customization (e.g., MongoDB disableUpdateUri, Redshift DBUser).
    # Note: integrate these directly into AWS Glue Connection properties (requires updating existing connections).

    def __post_init__(self):
        """Validate inputs after initialization."""
        from ..utils.additional_options_validator import AdditionalOptionsValidator

        connection_type = self.connection.get("ConnectionType", "").lower()
        AdditionalOptionsValidator.validate(connection_type, self.additional_options)
