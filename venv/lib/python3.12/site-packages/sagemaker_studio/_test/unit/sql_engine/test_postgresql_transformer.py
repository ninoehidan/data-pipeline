from unittest.mock import patch

import pytest

from sagemaker_studio.sql_engine.postgresql_transformer import PostgreSQLTransformer


def test_get_required_fields():
    assert PostgreSQLTransformer.get_required_fields() == [
        "host",
        "port",
        "database",
        "user",
        "password",
    ]


def test_to_sqlalchemy_config_returns_expected_connection_string():
    with patch.object(PostgreSQLTransformer, "validate_required_fields") as mocked:
        connection_data = {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "admin",
            "password": "secret",
        }
        result = PostgreSQLTransformer.to_sqlalchemy_config(connection_data)
        expected = "postgresql+psycopg2://admin:secret@localhost:5432/testdb"
        assert result == {"connection_string": expected}
        mocked.assert_called_once_with(
            ["host", "port", "database", "user", "password"], connection_data
        )


def test_to_sqlalchemy_config_raises_if_required_fields_missing():
    with patch.object(
        PostgreSQLTransformer,
        "validate_required_fields",
        side_effect=ValueError("Missing required fields"),
    ):
        with pytest.raises(ValueError):
            PostgreSQLTransformer.to_sqlalchemy_config({"host": "localhost"})
