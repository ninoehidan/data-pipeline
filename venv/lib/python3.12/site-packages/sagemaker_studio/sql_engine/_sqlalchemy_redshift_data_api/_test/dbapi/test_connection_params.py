"""
Unit tests for connection parameter parsing and validation.
"""

import pytest

from ...dbapi.connection_params import (
    ConnectionParams,
    create_connection_params,
    parse_connection_url,
)
from ...dbapi.exceptions import InterfaceError


class TestConnectionParams:
    """Test ConnectionParams dataclass validation."""

    def test_valid_provisioned_connection_params(self):
        """Test creating valid provisioned connection parameters."""
        params = ConnectionParams(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="myuser",
            region="us-east-1",
        )

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.db_user == "myuser"
        assert params.region == "us-east-1"
        assert params.workgroup_name is None
        assert params.secret_arn is None
        assert params.with_event is False
        assert params.is_serverless is False

    def test_valid_serverless_connection_params(self):
        """Test creating valid serverless connection parameters."""
        params = ConnectionParams(
            workgroup_name="my-workgroup",
            database_name="mydb",
            db_user="myuser",
            region="us-east-1",
        )

        assert params.cluster_identifier is None
        assert params.database_name == "mydb"
        assert params.db_user == "myuser"
        assert params.region == "us-east-1"
        assert params.workgroup_name == "my-workgroup"
        assert params.is_serverless is True

    def test_connection_params_with_optional_fields(self):
        """Test connection parameters with optional fields."""
        params = ConnectionParams(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="myuser",
            region="us-east-1",
            secret_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret",
            with_event=True,
        )

        assert params.secret_arn == "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret"
        assert params.with_event is True

    def test_connection_params_minimal_provisioned(self):
        """Test minimal provisioned connection parameters (no db_user)."""
        params = ConnectionParams(cluster_identifier="my-cluster", database_name="mydb")

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.db_user is None
        assert params.region == "us-east-1"  # Default value
        assert params.is_serverless is False

    def test_connection_params_minimal_serverless(self):
        """Test minimal serverless connection parameters (no db_user)."""
        params = ConnectionParams(workgroup_name="my-workgroup", database_name="mydb")

        assert params.workgroup_name == "my-workgroup"
        assert params.database_name == "mydb"
        assert params.db_user is None
        assert params.region == "us-east-1"  # Default value
        assert params.is_serverless is True

    def test_missing_database(self):
        """Test validation fails when database is missing."""
        with pytest.raises(InterfaceError, match="database_name is required"):
            ConnectionParams(cluster_identifier="my-cluster", database_name="")

    def test_missing_cluster_identifier_and_workgroup(self):
        """Test validation fails when both cluster_identifier and workgroup_name are missing."""
        with pytest.raises(
            InterfaceError, match="cluster_identifier is required for provisioned configuration"
        ):
            ConnectionParams(database_name="mydb")

    def test_missing_workgroup_for_serverless(self):
        """Test validation fails when workgroup_name is missing for serverless."""
        with pytest.raises(
            InterfaceError, match="workgroup_name is required for serverless configuration"
        ):
            ConnectionParams(
                database_name="mydb",
                workgroup_name="",  # Empty workgroup_name triggers serverless mode
            )

    def test_invalid_cluster_identifier_format(self):
        """Test validation fails for invalid cluster identifier format."""
        with pytest.raises(InterfaceError, match="cluster_identifier must be lettersnumbers"):
            ConnectionParams(
                cluster_identifier="my_cluster!", database_name="mydb"  # Invalid character
            )

    def test_cluster_identifier_too_long(self):
        """Test validation fails for cluster identifier that's too long."""
        long_name = "a" * 64  # 64 characters, max is 63
        with pytest.raises(InterfaceError, match="cluster_identifier must be lettersnumbers"):
            ConnectionParams(cluster_identifier=long_name, database_name="mydb")

    def test_invalid_workgroup_name_format(self):
        """Test validation fails for invalid workgroup name format."""
        with pytest.raises(InterfaceError, match="workgroup_name must be lettersnumbers"):
            ConnectionParams(
                workgroup_name="my_workgroup!", database_name="mydb"  # Invalid character
            )

    def test_workgroup_name_too_long(self):
        """Test validation fails for workgroup name that's too long."""
        long_name = "a" * 65  # 65 characters, max is 64
        with pytest.raises(InterfaceError, match="workgroup_name must be lettersnumbers"):
            ConnectionParams(workgroup_name=long_name, database_name="mydb")

    def test_invalid_database_format(self):
        """Test validation fails for invalid database format."""
        with pytest.raises(InterfaceError, match="database_name must be lettersnumbers"):
            ConnectionParams(
                cluster_identifier="my-cluster", database_name="my-db!"  # Invalid character
            )

    def test_database_too_long(self):
        """Test validation fails for database name that's too long."""
        long_name = "a" * 65  # 65 characters, max is 64
        with pytest.raises(InterfaceError, match="database_name must be lettersnumbers"):
            ConnectionParams(cluster_identifier="my-cluster", database_name=long_name)

    def test_invalid_db_user_format(self):
        """Test validation allows any characters in db_user (only length validation)."""
        # This should now pass since we only validate length, not format
        params = ConnectionParams(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="my-user!",  # Special characters now allowed
        )
        assert params.db_user == "my-user!"

    def test_db_user_too_long(self):
        """Test validation fails for db_user that's too long."""
        long_name = "a" * 129  # 129 characters, max is 128
        with pytest.raises(InterfaceError, match="db_user must be max 128 characters"):
            ConnectionParams(
                cluster_identifier="my-cluster", database_name="mydb", db_user=long_name
            )

    def test_invalid_region_format(self):
        """Test validation fails for invalid region format."""
        with pytest.raises(InterfaceError, match="region must be a valid AWS region"):
            ConnectionParams(
                cluster_identifier="my-cluster",
                database_name="mydb",
                region="US_EAST_1",  # Invalid format
            )

    def test_is_serverless_property(self):
        """Test is_serverless property detection."""
        # Provisioned cluster
        provisioned = ConnectionParams(cluster_identifier="my-cluster", database_name="mydb")
        assert provisioned.is_serverless is False

        # Serverless workgroup
        serverless = ConnectionParams(workgroup_name="my-workgroup", database_name="mydb")
        assert serverless.is_serverless is True

    def test_to_dict_provisioned(self):
        """Test converting provisioned connection parameters to dictionary."""
        params = ConnectionParams(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="myuser",
            region="us-east-1",
            secret_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret",
            with_event=True,
        )

        result = params.to_dict()
        expected = {
            "database_name": "mydb",
            "region": "us-east-1",
            "with_event": True,
            "cluster_identifier": "my-cluster",
            "db_user": "myuser",
            "secret_arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret",
        }

        assert result == expected

    def test_to_dict_serverless(self):
        """Test converting serverless connection parameters to dictionary."""
        params = ConnectionParams(
            workgroup_name="my-workgroup",
            database_name="mydb",
            db_user="myuser",
            region="us-east-1",
        )

        result = params.to_dict()
        expected = {
            "database_name": "mydb",
            "region": "us-east-1",
            "with_event": False,
            "workgroup_name": "my-workgroup",
            "db_user": "myuser",
        }

        assert result == expected

    def test_to_dict_minimal(self):
        """Test converting minimal connection parameters to dictionary."""
        params = ConnectionParams(cluster_identifier="my-cluster", database_name="mydb")

        result = params.to_dict()
        expected = {
            "database_name": "mydb",
            "region": "us-east-1",
            "with_event": False,
            "cluster_identifier": "my-cluster",
        }

        assert result == expected

    def test_connection_params_with_aws_credentials(self):
        """Test connection parameters with explicit AWS credentials."""
        params = ConnectionParams(
            cluster_identifier="my-cluster",
            database_name="mydb",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            aws_session_token="session-token-example",
        )

        assert params.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert params.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert params.aws_session_token == "session-token-example"
        assert params.profile_name is None

    def test_connection_params_with_profile_name(self):
        """Test connection parameters with AWS profile name."""
        params = ConnectionParams(
            cluster_identifier="my-cluster", database_name="mydb", profile_name="my-profile"
        )

        assert params.profile_name == "my-profile"
        assert params.aws_access_key_id is None
        assert params.aws_secret_access_key is None
        assert params.aws_session_token is None

    def test_aws_credentials_validation_profile_and_explicit(self):
        """Test validation fails when both profile_name and explicit credentials are provided."""
        with pytest.raises(
            InterfaceError, match="Cannot specify both profile_name and explicit AWS credentials"
        ):
            ConnectionParams(
                cluster_identifier="my-cluster",
                database_name="mydb",
                profile_name="my-profile",
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            )

    def test_aws_credentials_validation_access_key_without_secret(self):
        """Test validation fails when aws_access_key_id is provided without aws_secret_access_key."""
        with pytest.raises(
            InterfaceError,
            match="aws_secret_access_key is required when aws_access_key_id is provided",
        ):
            ConnectionParams(
                cluster_identifier="my-cluster",
                database_name="mydb",
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            )

    def test_aws_credentials_validation_secret_without_access_key(self):
        """Test validation fails when aws_secret_access_key is provided without aws_access_key_id."""
        with pytest.raises(
            InterfaceError,
            match="aws_access_key_id is required when aws_secret_access_key is provided",
        ):
            ConnectionParams(
                cluster_identifier="my-cluster",
                database_name="mydb",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            )

    def test_aws_credentials_validation_session_token_without_keys(self):
        """Test validation fails when aws_session_token is provided without access key and secret."""
        with pytest.raises(
            InterfaceError,
            match="aws_session_token requires both aws_access_key_id and aws_secret_access_key",
        ):
            ConnectionParams(
                cluster_identifier="my-cluster",
                database_name="mydb",
                aws_session_token="session-token-example",
            )

    def test_aws_credentials_validation_invalid_access_key_format(self):
        """Test validation fails for invalid aws_access_key_id format."""
        with pytest.raises(
            InterfaceError,
            match="aws_access_key_id must be 16-128 uppercase lettersnumbers characters",
        ):
            ConnectionParams(
                cluster_identifier="my-cluster",
                database_name="mydb",
                aws_access_key_id="invalid-key",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            )

    def test_aws_credentials_validation_short_access_key(self):
        """Test validation fails for aws_access_key_id that's too short."""
        with pytest.raises(
            InterfaceError,
            match="aws_access_key_id must be 16-128 uppercase lettersnumbers characters",
        ):
            ConnectionParams(
                cluster_identifier="my-cluster",
                database_name="mydb",
                aws_access_key_id="SHORTKEY",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            )

    def test_aws_credentials_validation_short_secret_key(self):
        """Test validation fails for aws_secret_access_key that's too short."""
        with pytest.raises(
            InterfaceError, match="aws_secret_access_key must be at least 16 characters"
        ):
            ConnectionParams(
                cluster_identifier="my-cluster",
                database_name="mydb",
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="short",
            )

    def test_aws_credentials_validation_invalid_profile_name(self):
        """Test validation fails for invalid profile_name format."""
        with pytest.raises(
            InterfaceError,
            match="profile_name must be lettersnumbers with underscores, dots, and hyphens",
        ):
            ConnectionParams(
                cluster_identifier="my-cluster",
                database_name="mydb",
                profile_name="invalid profile!",
            )

    def test_aws_credentials_validation_long_profile_name(self):
        """Test validation fails for profile_name that's too long."""
        long_name = "a" * 65  # 65 characters, max is 64
        with pytest.raises(
            InterfaceError,
            match="profile_name must be lettersnumbers with underscores, dots, and hyphens",
        ):
            ConnectionParams(
                cluster_identifier="my-cluster", database_name="mydb", profile_name=long_name
            )

    def test_to_dict_with_aws_credentials(self):
        """Test converting connection parameters with AWS credentials to dictionary."""
        params = ConnectionParams(
            cluster_identifier="my-cluster",
            database_name="mydb",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            aws_session_token="session-token-example",
        )

        result = params.to_dict()
        expected = {
            "database_name": "mydb",
            "region": "us-east-1",
            "with_event": False,
            "cluster_identifier": "my-cluster",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "aws_session_token": "session-token-example",
        }

        assert result == expected

    def test_to_dict_with_profile_name(self):
        """Test converting connection parameters with profile name to dictionary."""
        params = ConnectionParams(
            cluster_identifier="my-cluster", database_name="mydb", profile_name="my-profile"
        )

        result = params.to_dict()
        expected = {
            "database_name": "mydb",
            "region": "us-east-1",
            "with_event": False,
            "cluster_identifier": "my-cluster",
            "profile_name": "my-profile",
        }

        assert result == expected


class TestParseConnectionUrl:
    """Test connection URL parsing functionality."""

    def test_provisioned_basic_url(self):
        """Test parsing basic provisioned connection URL."""
        url = "redshift_data_api://my-cluster/mydb"
        params = parse_connection_url(url)

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.db_user is None
        assert params.region == "us-east-1"  # Default
        assert params.workgroup_name is None
        assert params.is_serverless is False

    def test_provisioned_url_with_params(self):
        """Test parsing provisioned connection URL with parameters."""
        url = "redshift_data_api://my-cluster/mydb?region=us-west-2&db_user=myuser"
        params = parse_connection_url(url)

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.db_user == "myuser"
        assert params.region == "us-west-2"
        assert params.workgroup_name is None
        assert params.is_serverless is False

    def test_serverless_basic_url(self):
        """Test parsing basic serverless connection URL."""
        url = "redshift_data_api:///mydb?workgroup_name=my-workgroup"
        params = parse_connection_url(url)

        assert params.cluster_identifier is None
        assert params.database_name == "mydb"
        assert params.db_user is None
        assert params.region == "us-east-1"  # Default
        assert params.workgroup_name == "my-workgroup"
        assert params.is_serverless is True

    def test_serverless_url_with_params(self):
        """Test parsing serverless connection URL with parameters."""
        url = (
            "redshift_data_api:///mydb?region=us-west-2&db_user=myuser&workgroup_name=my-workgroup"
        )
        params = parse_connection_url(url)

        assert params.cluster_identifier is None
        assert params.database_name == "mydb"
        assert params.db_user == "myuser"
        assert params.region == "us-west-2"
        assert params.workgroup_name == "my-workgroup"
        assert params.is_serverless is True

    def test_connection_url_with_all_params(self):
        """Test parsing connection URL with all optional parameters."""
        url = (
            "redshift_data_api://my-cluster/mydb?"
            "region=us-east-1&db_user=myuser&"
            "secret_arn=arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret&"
            "with_event=true"
        )
        params = parse_connection_url(url)

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.db_user == "myuser"
        assert params.region == "us-east-1"
        assert params.secret_arn == "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret"
        assert params.with_event is True

    def test_sqlalchemy_driver_format(self):
        """Test parsing URL with SQLAlchemy driver specification format."""
        url = "redshift_data_api+redshift_data_api://my-cluster/mydb"
        params = parse_connection_url(url)

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.region == "us-east-1"

    def test_empty_url(self):
        """Test parsing empty URL raises error."""
        with pytest.raises(InterfaceError, match="Connection URL cannot be empty"):
            parse_connection_url("")

    def test_invalid_scheme(self):
        """Test parsing URL with invalid scheme raises error."""
        url = "postgresql://my-cluster/mydb"
        with pytest.raises(InterfaceError, match="Invalid URL scheme 'postgresql'"):
            parse_connection_url(url)

    def test_invalid_driver_scheme(self):
        """Test parsing URL with invalid driver scheme raises error."""
        url = "postgresql+redshift_data_api://my-cluster/mydb"
        with pytest.raises(
            InterfaceError, match="Invalid URL scheme 'postgresql\\+redshift_data_api'"
        ):
            parse_connection_url(url)

    def test_missing_database(self):
        """Test parsing URL without database raises error."""
        url = "redshift_data_api://my-cluster/"
        with pytest.raises(InterfaceError, match="Database name must be specified"):
            parse_connection_url(url)

    def test_missing_database_serverless(self):
        """Test parsing serverless URL without database raises error."""
        url = "redshift_data_api:///?workgroup_name=my-workgroup"
        with pytest.raises(InterfaceError, match="Database name must be specified"):
            parse_connection_url(url)

    def test_duplicate_parameter(self):
        """Test parsing URL with duplicate parameter raises error."""
        url = "redshift_data_api://my-cluster/mydb?region=us-east-1&region=us-west-2"
        with pytest.raises(InterfaceError, match="Parameter 'region' specified multiple times"):
            parse_connection_url(url)

    def test_both_cluster_and_workgroup(self):
        """Test parsing URL with both cluster and workgroup raises error."""
        url = "redshift_data_api://my-cluster/mydb?workgroup_name=my-workgroup"
        with pytest.raises(
            InterfaceError, match="Cannot specify both cluster_identifier and workgroup_name"
        ):
            parse_connection_url(url)

    def test_serverless_without_workgroup(self):
        """Test parsing serverless URL without workgroup raises error."""
        url = "redshift_data_api:///mydb"
        with pytest.raises(InterfaceError, match="workgroup_name parameter is required"):
            parse_connection_url(url)

    def test_with_event_true_variations(self):
        """Test parsing with_event parameter with various true values."""
        true_values = ["true", "1", "yes", "on", "True", "YES", "ON"]

        for value in true_values:
            url = f"redshift_data_api://my-cluster/mydb?with_event={value}"
            params = parse_connection_url(url)
            assert params.with_event is True, f"Failed for value: {value}"

    def test_with_event_false_variations(self):
        """Test parsing with_event parameter with various false values."""
        false_values = ["false", "0", "no", "off", "False", "NO", "OFF"]

        for value in false_values:
            url = f"redshift_data_api://my-cluster/mydb?with_event={value}"
            params = parse_connection_url(url)
            assert params.with_event is False, f"Failed for value: {value}"

    def test_with_event_invalid_value(self):
        """Test parsing with_event parameter with invalid value raises error."""
        url = "redshift_data_api://my-cluster/mydb?with_event=maybe"
        with pytest.raises(InterfaceError, match="Invalid value for with_event: 'maybe'"):
            parse_connection_url(url)

    def test_malformed_url(self):
        """Test parsing malformed URL raises error."""
        url = "not-a-valid-url"
        with pytest.raises(InterfaceError, match="Invalid URL format"):
            parse_connection_url(url)

    def test_url_with_port_ignored(self):
        """Test that port in URL is ignored (not used by Data API)."""
        url = "redshift_data_api://my-cluster:5439/mydb"
        params = parse_connection_url(url)

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"

    def test_url_with_username_ignored(self):
        """Test that username in URL is ignored (use db_user parameter instead)."""
        url = "redshift_data_api://user@my-cluster/mydb?db_user=realuser"
        params = parse_connection_url(url)

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.db_user == "realuser"

    def test_url_with_aws_credentials(self):
        """Test parsing URL with AWS credential parameters."""
        url = (
            "redshift_data_api://my-cluster/mydb?"
            "aws_access_key_id=AKIAIOSFODNN7EXAMPLE&"
            "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY&"
            "aws_session_token=session-token-example"
        )
        params = parse_connection_url(url)

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert params.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert params.aws_session_token == "session-token-example"
        assert params.profile_name is None

    def test_url_with_profile_name(self):
        """Test parsing URL with AWS profile name parameter."""
        url = "redshift_data_api://my-cluster/mydb?profile_name=my-profile"
        params = parse_connection_url(url)

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.profile_name == "my-profile"
        assert params.aws_access_key_id is None
        assert params.aws_secret_access_key is None
        assert params.aws_session_token is None

    def test_url_with_serverless_and_aws_credentials(self):
        """Test parsing serverless URL with AWS credential parameters."""
        url = (
            "redshift_data_api:///mydb?"
            "workgroup_name=my-workgroup&"
            "aws_access_key_id=AKIAIOSFODNN7EXAMPLE&"
            "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        params = parse_connection_url(url)

        assert params.cluster_identifier is None
        assert params.database_name == "mydb"
        assert params.workgroup_name == "my-workgroup"
        assert params.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert params.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert params.aws_session_token is None
        assert params.is_serverless is True

    def test_url_aws_credentials_validation_profile_and_explicit(self):
        """Test URL parsing fails when both profile_name and explicit credentials are provided."""
        url = (
            "redshift_data_api://my-cluster/mydb?"
            "profile_name=my-profile&"
            "aws_access_key_id=AKIAIOSFODNN7EXAMPLE"
        )
        with pytest.raises(
            InterfaceError, match="Cannot specify both profile_name and explicit AWS credentials"
        ):
            parse_connection_url(url)

    def test_url_aws_credentials_validation_access_key_without_secret(self):
        """Test URL parsing fails when aws_access_key_id is provided without aws_secret_access_key."""
        url = "redshift_data_api://my-cluster/mydb?aws_access_key_id=AKIAIOSFODNN7EXAMPLE"
        with pytest.raises(
            InterfaceError,
            match="aws_secret_access_key is required when aws_access_key_id is provided",
        ):
            parse_connection_url(url)

    def test_url_aws_credentials_validation_secret_without_access_key(self):
        """Test URL parsing fails when aws_secret_access_key is provided without aws_access_key_id."""
        url = "redshift_data_api://my-cluster/mydb?aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        with pytest.raises(
            InterfaceError,
            match="aws_access_key_id is required when aws_secret_access_key is provided",
        ):
            parse_connection_url(url)

    def test_url_aws_credentials_validation_session_token_without_keys(self):
        """Test URL parsing fails when aws_session_token is provided without access key and secret."""
        url = "redshift_data_api://my-cluster/mydb?aws_session_token=session-token-example"
        with pytest.raises(
            InterfaceError,
            match="aws_session_token requires both aws_access_key_id and aws_secret_access_key",
        ):
            parse_connection_url(url)

    def test_url_aws_credentials_validation_invalid_access_key_format(self):
        """Test URL parsing fails for invalid aws_access_key_id format."""
        url = (
            "redshift_data_api://my-cluster/mydb?"
            "aws_access_key_id=invalid-key&"
            "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        with pytest.raises(
            InterfaceError,
            match="aws_access_key_id must be 16-128 uppercase lettersnumbers characters",
        ):
            parse_connection_url(url)

    def test_url_aws_credentials_validation_short_secret_key(self):
        """Test URL parsing fails for aws_secret_access_key that's too short."""
        url = (
            "redshift_data_api://my-cluster/mydb?"
            "aws_access_key_id=AKIAIOSFODNN7EXAMPLE&"
            "aws_secret_access_key=short"
        )
        with pytest.raises(
            InterfaceError, match="aws_secret_access_key must be at least 16 characters"
        ):
            parse_connection_url(url)

    def test_url_aws_credentials_validation_invalid_profile_name(self):
        """Test URL parsing fails for invalid profile_name format."""
        url = "redshift_data_api://my-cluster/mydb?profile_name=invalid%20profile!"
        with pytest.raises(
            InterfaceError,
            match="profile_name must be lettersnumbers with underscores, dots, and hyphens",
        ):
            parse_connection_url(url)


class TestCreateConnectionParams:
    """Test create_connection_params function."""

    def test_create_connection_params_provisioned(self):
        """Test creating provisioned connection parameters from keyword arguments."""
        params = create_connection_params(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="myuser",
            region="us-east-1",
        )

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.db_user == "myuser"
        assert params.region == "us-east-1"
        assert params.is_serverless is False

    def test_create_connection_params_serverless(self):
        """Test creating serverless connection parameters from keyword arguments."""
        params = create_connection_params(
            workgroup_name="my-workgroup",
            database_name="mydb",
            db_user="myuser",
            region="us-east-1",
        )

        assert params.workgroup_name == "my-workgroup"
        assert params.database_name == "mydb"
        assert params.db_user == "myuser"
        assert params.region == "us-east-1"
        assert params.is_serverless is True

    def test_create_connection_params_with_optional(self):
        """Test creating connection parameters with optional fields."""
        params = create_connection_params(
            cluster_identifier="my-cluster",
            database_name="mydb",
            db_user="myuser",
            region="us-east-1",
            secret_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret",
            with_event=True,
        )

        assert params.secret_arn == "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret"
        assert params.with_event is True

    def test_create_connection_params_minimal(self):
        """Test creating minimal connection parameters."""
        params = create_connection_params(cluster_identifier="my-cluster", database_name="mydb")

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.db_user is None
        assert params.region == "us-east-1"  # Default

    def test_create_connection_params_validation_missing_config(self):
        """Test that create_connection_params validates missing configuration."""
        with pytest.raises(
            InterfaceError, match="cluster_identifier is required for provisioned configuration"
        ):
            create_connection_params(database_name="mydb")

    def test_create_connection_params_validation_missing_database(self):
        """Test that create_connection_params validates missing database."""
        with pytest.raises(InterfaceError, match="database_name is required"):
            create_connection_params(cluster_identifier="my-cluster", database_name="")

    def test_create_connection_params_with_aws_credentials(self):
        """Test creating connection parameters with AWS credentials from keyword arguments."""
        params = create_connection_params(
            cluster_identifier="my-cluster",
            database_name="mydb",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            aws_session_token="session-token-example",
        )

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert params.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert params.aws_session_token == "session-token-example"
        assert params.profile_name is None

    def test_create_connection_params_with_profile_name(self):
        """Test creating connection parameters with AWS profile name from keyword arguments."""
        params = create_connection_params(
            cluster_identifier="my-cluster", database_name="mydb", profile_name="my-profile"
        )

        assert params.cluster_identifier == "my-cluster"
        assert params.database_name == "mydb"
        assert params.profile_name == "my-profile"
        assert params.aws_access_key_id is None
        assert params.aws_secret_access_key is None
        assert params.aws_session_token is None

    def test_create_connection_params_aws_credentials_validation(self):
        """Test that create_connection_params validates AWS credential combinations."""
        with pytest.raises(
            InterfaceError, match="Cannot specify both profile_name and explicit AWS credentials"
        ):
            create_connection_params(
                cluster_identifier="my-cluster",
                database_name="mydb",
                profile_name="my-profile",
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            )
