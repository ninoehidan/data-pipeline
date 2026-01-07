"""
Connection parameter parsing and validation for Redshift Data API.

This module handles parsing of connection URLs and validation of connection parameters.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import parse_qs

from .exceptions import InterfaceError


@dataclass
class ConnectionParams:
    """
    Connection parameters for Redshift Data API.

    Supports both provisioned and serverless configurations with auto-detection.

    Attributes:
        database_name: The database name (required for both configurations)
        region: The AWS region (defaults to 'us-east-1')
        db_user: The database user name (optional, can use IAM)
        cluster_identifier: The Redshift cluster identifier (for provisioned)
        workgroup_name: The workgroup name (for serverless)
        secret_arn: Optional secret ARN for authentication
        with_event: Whether to include event information
        aws_access_key_id: AWS access key ID for explicit credential authentication
        aws_secret_access_key: AWS secret access key for explicit credential authentication
        aws_session_token: AWS session token for temporary credentials
        profile_name: Named AWS profile for credential management
    """

    database_name: str
    region: str = "us-east-1"
    db_user: Optional[str] = None
    cluster_identifier: Optional[str] = None
    workgroup_name: Optional[str] = None
    secret_arn: Optional[str] = None
    with_event: bool = False
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    profile_name: Optional[str] = None

    def __post_init__(self):
        """Validate connection parameters after initialization."""
        self.validate()

    @property
    def is_serverless(self) -> bool:
        """Auto-detect serverless vs provisioned based on parameters."""
        return self.workgroup_name is not None and self.cluster_identifier is None

    def validate(self):
        """Validate that required parameters are present for the configuration type."""
        if not self.database_name:
            raise InterfaceError("database_name is required")

        if self.is_serverless:
            if not self.workgroup_name:
                raise InterfaceError("workgroup_name is required for serverless configuration")
        else:
            if not self.cluster_identifier:
                raise InterfaceError("cluster_identifier is required for provisioned configuration")

        # Validate AWS credential parameter combinations
        self._validate_aws_credentials()

        # Validate parameter formats
        self._validate_param_formats()

    def _validate_param_formats(self):
        """Validate parameter formats."""
        # Validate database name format (lettersnumbers, underscores, max 64 chars)
        if not re.match(r"^[a-zA-Z0-9_]{1,64}$", self.database_name):
            raise InterfaceError(
                "database_name must be lettersnumbers with underscores, max 64 characters"
            )

        # Validate cluster identifier if provided
        if self.cluster_identifier and not re.match(
            r"^[a-zA-Z0-9-]{1,63}$", self.cluster_identifier
        ):
            raise InterfaceError(
                "cluster_identifier must be lettersnumbers with hyphens, max 63 characters"
            )

        # Validate workgroup name if provided
        if self.workgroup_name and not re.match(r"^[a-zA-Z0-9-]{1,64}$", self.workgroup_name):
            raise InterfaceError(
                "workgroup_name must be lettersnumbers with hyphens, max 64 characters"
            )

        # Validate user name format if provided (only length check)
        if self.db_user and len(self.db_user) > 128:
            raise InterfaceError("db_user must be max 128 characters")

        # Validate AWS region format
        if not re.match(r"^[a-z0-9-]+$", self.region):
            raise InterfaceError("region must be a valid AWS region format")

    def _validate_aws_credentials(self):
        """Validate AWS credential parameter combinations."""
        # Cannot specify both profile_name and explicit AWS credentials
        if self.profile_name and (
            self.aws_access_key_id or self.aws_secret_access_key or self.aws_session_token
        ):
            raise InterfaceError("Cannot specify both profile_name and explicit AWS credentials")

        # If aws_access_key_id is provided, aws_secret_access_key is required
        if self.aws_access_key_id and not self.aws_secret_access_key:
            raise InterfaceError(
                "aws_secret_access_key is required when aws_access_key_id is provided"
            )

        # If aws_secret_access_key is provided, aws_access_key_id is required
        if self.aws_secret_access_key and not self.aws_access_key_id:
            raise InterfaceError(
                "aws_access_key_id is required when aws_secret_access_key is provided"
            )

        # aws_session_token can only be used with aws_access_key_id and aws_secret_access_key
        if self.aws_session_token and not (self.aws_access_key_id and self.aws_secret_access_key):
            raise InterfaceError(
                "aws_session_token requires both aws_access_key_id and aws_secret_access_key"
            )

        # Validate AWS credential formats if provided
        if self.aws_access_key_id and not re.match(r"^[A-Z0-9]{16,128}$", self.aws_access_key_id):
            raise InterfaceError(
                "aws_access_key_id must be 16-128 uppercase lettersnumbers characters"
            )

        if self.aws_secret_access_key and len(self.aws_secret_access_key) < 16:
            raise InterfaceError("aws_secret_access_key must be at least 16 characters")

        if self.profile_name and not re.match(r"^[a-zA-Z0-9_.-]{1,64}$", self.profile_name):
            raise InterfaceError(
                "profile_name must be lettersnumbers with underscores, dots, and hyphens, max 64 characters"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert connection parameters to dictionary."""
        result = {
            "database_name": self.database_name,
            "region": self.region,
            "with_event": self.with_event,
        }

        if self.cluster_identifier:
            result["cluster_identifier"] = self.cluster_identifier
        if self.workgroup_name:
            result["workgroup_name"] = self.workgroup_name
        if self.db_user:
            result["db_user"] = self.db_user
        if self.secret_arn:
            result["secret_arn"] = self.secret_arn
        if self.aws_access_key_id:
            result["aws_access_key_id"] = self.aws_access_key_id
        if self.aws_secret_access_key:
            result["aws_secret_access_key"] = self.aws_secret_access_key
        if self.aws_session_token:
            result["aws_session_token"] = self.aws_session_token
        if self.profile_name:
            result["profile_name"] = self.profile_name

        return result


def parse_connection_url(url: str) -> ConnectionParams:
    """
    Parse a Redshift Data API connection URL.

    Supported formats:
    - Provisioned: redshift_data_api://cluster_identifier/database
    - Provisioned with params: redshift_data_api://cluster_identifier/database?region=us-east-1&db_user=username
    - Serverless: redshift_data_api:///database
    - Serverless with params: redshift_data_api:///database?region=us-east-1&workgroup_name=my-workgroup&db_user=username

    Args:
        url: The connection URL string

    Returns:
        ConnectionParams: Parsed and validated connection parameters

    Raises:
        InterfaceError: If URL format is invalid or required parameters are missing
    """
    if not url:
        raise InterfaceError("Connection URL cannot be empty")

    # Custom URL parsing since urlparse doesn't handle schemes with underscores
    if "://" not in url:
        raise InterfaceError("Invalid URL format: missing '://'")

    try:
        scheme_part, rest = url.split("://", 1)
    except ValueError:
        raise InterfaceError("Invalid URL format")

    # Validate scheme
    scheme = scheme_part
    if "+" in scheme:
        # Handle SQLAlchemy driver specification format (dialect+driver://)
        dialect_part, driver_part = scheme.split("+", 1)
        if dialect_part != "redshift_data_api":
            raise InterfaceError(
                f"Invalid URL scheme '{scheme}'. Expected 'redshift_data_api' or 'redshift_data_api+driver'"
            )
        scheme = dialect_part

    if scheme != "redshift_data_api":
        raise InterfaceError(f"Invalid URL scheme '{scheme}'. Expected 'redshift_data_api'")

    # Split the rest into path and query parts
    if "?" in rest:
        path_part, query_part = rest.split("?", 1)
    else:
        path_part = rest
        query_part = ""

    # Parse path to extract cluster_identifier and database
    if path_part.startswith("//"):
        # Serverless format: ///database (path_part would be "//database")
        cluster_identifier = ""
        database = path_part[2:]  # Remove leading //
    elif "/" in path_part:
        # Provisioned format: cluster_identifier/database
        # Handle potential username@host:port format
        host_part, database = path_part.split("/", 1)

        # Extract cluster_identifier from host_part, ignoring username and port
        if "@" in host_part:
            # Format: username@cluster_identifier:port
            _, host_part = host_part.split("@", 1)

        if ":" in host_part:
            # Format: cluster_identifier:port
            cluster_identifier, _ = host_part.split(":", 1)
        else:
            cluster_identifier = host_part
    else:
        # Just cluster identifier, no database
        # Handle potential username@host:port format
        host_part = path_part

        # Extract cluster_identifier from host_part, ignoring username and port
        if "@" in host_part:
            # Format: username@cluster_identifier:port
            _, host_part = host_part.split("@", 1)

        if ":" in host_part:
            # Format: cluster_identifier:port
            cluster_identifier, _ = host_part.split(":", 1)
        else:
            cluster_identifier = host_part

        database = ""

    # Validate database is provided
    if not database:
        raise InterfaceError("Database name must be specified in URL path")

    # Parse query parameters
    try:
        query_params = parse_qs(query_part) if query_part else {}
    except Exception as e:
        raise InterfaceError(f"Invalid query parameters: {e}")

    def get_single_param(name: str, default: Optional[str] = None) -> Optional[str]:
        """Extract a single parameter value from query parameters."""
        values = query_params.get(name, [])
        if not values:
            return default
        if len(values) > 1:
            raise InterfaceError(f"Parameter '{name}' specified multiple times")
        return values[0]

    # Get parameters with defaults
    region = get_single_param("region", "us-east-1")
    db_user = get_single_param("db_user")
    workgroup_name = get_single_param("workgroup_name")
    secret_arn = get_single_param("secret_arn")
    with_event_str = get_single_param("with_event")

    # Get AWS credential parameters
    aws_access_key_id = get_single_param("aws_access_key_id")
    aws_secret_access_key = get_single_param("aws_secret_access_key")
    aws_session_token = get_single_param("aws_session_token")
    profile_name = get_single_param("profile_name")

    # Convert with_event to boolean
    with_event = False
    if with_event_str:
        with_event_str = with_event_str.lower()
        if with_event_str in ("true", "1", "yes", "on"):
            with_event = True
        elif with_event_str in ("false", "0", "no", "off"):
            with_event = False
        else:
            raise InterfaceError(
                f"Invalid value for with_event: '{with_event_str}'. "
                "Expected true/false, 1/0, yes/no, or on/off"
            )

    # Auto-detect configuration type and validate
    if cluster_identifier and workgroup_name:
        raise InterfaceError(
            "Cannot specify both cluster_identifier and workgroup_name. "
            "Use cluster_identifier for provisioned clusters or workgroup_name for serverless"
        )

    # For serverless (no cluster_identifier in hostname), workgroup_name is required
    if not cluster_identifier and not workgroup_name:
        raise InterfaceError(
            "For serverless configuration (redshift_data_api:///database), "
            "workgroup_name parameter is required"
        )

    # Create and validate connection parameters
    return ConnectionParams(
        database_name=database,
        region=region,
        db_user=db_user,
        cluster_identifier=cluster_identifier if cluster_identifier else None,
        workgroup_name=workgroup_name,
        secret_arn=secret_arn,
        with_event=with_event,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
        profile_name=profile_name,
    )


def create_connection_params(**kwargs) -> ConnectionParams:
    """
    Create connection parameters from keyword arguments.

    Args:
        **kwargs: Connection parameters as keyword arguments

    Returns:
        ConnectionParams: Validated connection parameters
    """
    return ConnectionParams(**kwargs)
