from unittest.mock import patch

import pytest

from sagemaker_studio.sql_engine.mssql_transformer import MSSQLTransformer


def test_get_required_fields():
    assert MSSQLTransformer.get_required_fields() == [
        "host",
        "port",
        "database",
        "user",
        "password",
    ]


def test_to_sqlalchemy_config_builds_expected_connection_string():
    with patch.object(MSSQLTransformer, "validate_required_fields") as mocked:
        connection_data = {
            "host": "db.example.com",
            "port": 1433,
            "database": "testdb",
            "user": "admin",
            "password": "secret",
        }
        result = MSSQLTransformer.to_sqlalchemy_config(connection_data)
        expected = "mssql+pymssql://admin:secret@db.example.com:1433/testdb"
        assert result == {"connection_string": expected}
        mocked.assert_called_once_with(
            ["host", "port", "database", "user", "password"], connection_data
        )


def test_to_sqlalchemy_config_raises_when_required_fields_missing():
    with patch.object(
        MSSQLTransformer,
        "validate_required_fields",
        side_effect=ValueError("Missing required fields"),
    ):
        with pytest.raises(ValueError):
            MSSQLTransformer.to_sqlalchemy_config({"host": "db.example.com"})
