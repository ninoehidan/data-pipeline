from unittest.mock import patch

import pytest

from sagemaker_studio.sql_engine.snowflake_transformer import SnowflakeTransformer


def test_get_required_fields():
    assert SnowflakeTransformer.get_required_fields() == [
        "account",
        "database",
        "user",
        "password",
        "warehouse",
    ]


def test_to_sqlalchemy_config_builds_expected_connection_string():
    with patch.object(SnowflakeTransformer, "validate_required_fields") as mocked:
        connection_data = {
            "account": "xy12345.eu-central-1",
            "database": "ANALYTICS",
            "user": "svc_user",
            "password": "s3cr3t",
            "warehouse": "WH_XS",
            "role": "ANALYST",
        }
        result = SnowflakeTransformer.to_sqlalchemy_config(connection_data)
        expected = "snowflake://svc_user:s3cr3t@xy12345.eu-central-1/ANALYTICS?warehouse=WH_XS"
        assert result["connection_string"] == expected
        assert result["connect_args"] == connection_data
        mocked.assert_called_once_with(
            ["account", "database", "user", "password", "warehouse"],
            connection_data,
        )


def test_to_sqlalchemy_config_raises_when_required_missing():
    with patch.object(
        SnowflakeTransformer, "validate_required_fields", side_effect=ValueError("missing")
    ):
        with pytest.raises(ValueError):
            SnowflakeTransformer.to_sqlalchemy_config({"user": "x"})


def _params(obj):
    return getattr(obj, "sql_parameters", {}) or {}


def test_get_resources_action_database_when_none():
    r = SnowflakeTransformer.get_resources_action(None)
    assert (
        getattr(r, "sql")
        == "SELECT database_name FROM snowflake.information_schema.databases ORDER BY database_name;"
    )
    assert getattr(r, "default_type") == "DATABASE"
    assert getattr(r, "children") == ("SCHEMA",)
    assert _params(r) == {}


def test_get_resources_action_database_explicit():
    r = SnowflakeTransformer.get_resources_action("DATABASE")
    assert (
        getattr(r, "sql")
        == "SELECT database_name FROM snowflake.information_schema.databases ORDER BY database_name;"
    )
    assert getattr(r, "default_type") == "DATABASE"
    assert getattr(r, "children") == ("SCHEMA",)
    assert _params(r) == {}


def test_get_resources_action_schema_requires_database_parent():
    r = SnowflakeTransformer.get_resources_action("SCHEMA", {"DATABASE": "DB1"})
    assert (
        getattr(r, "sql")
        == "SELECT schema_name FROM DB1.INFORMATION_SCHEMA.SCHEMATA ORDER BY schema_name;"
    )
    assert getattr(r, "default_type") == "SCHEMA"
    assert getattr(r, "children") == ("TABLE",)
    assert _params(r) == {}


def test_get_resources_action_table_uses_schema_param():
    r = SnowflakeTransformer.get_resources_action("TABLE", {"DATABASE": "DB1", "SCHEMA": "PUBLIC"})
    assert (
        getattr(r, "sql")
        == "SELECT table_name FROM DB1.INFORMATION_SCHEMA.TABLES WHERE table_schema = :schema ORDER BY table_name;"
    )
    assert getattr(r, "default_type") == "TABLE"
    assert getattr(r, "children") == ("COLUMN",)
    assert _params(r) == {"schema": "PUBLIC"}


def test_get_resources_action_column_uses_schema_and_table_params():
    r = SnowflakeTransformer.get_resources_action(
        "COLUMN", {"DATABASE": "DB1", "SCHEMA": "PUBLIC", "TABLE": "EVENTS"}
    )
    assert (
        getattr(r, "sql")
        == "SELECT column_name FROM DB1.INFORMATION_SCHEMA.COLUMNS WHERE table_schema = :schema AND table_name = :table ORDER BY ordinal_position"
    )
    assert getattr(r, "default_type") == "COLUMN"
    assert getattr(r, "children") == ()
    assert _params(r) == {"schema": "PUBLIC", "table": "EVENTS"}


def test_get_resources_action_missing_required_parent_raises():
    with pytest.raises(Exception):
        SnowflakeTransformer.get_resources_action("SCHEMA", {})
    with pytest.raises(Exception):
        SnowflakeTransformer.get_resources_action("TABLE", {"DATABASE": "DB1"})
    with pytest.raises(Exception):
        SnowflakeTransformer.get_resources_action("COLUMN", {"DATABASE": "DB1", "SCHEMA": "PUBLIC"})


def test_get_resources_action_unsupported_type_raises():
    with pytest.raises(ValueError):
        SnowflakeTransformer.get_resources_action("VIEW", {})
