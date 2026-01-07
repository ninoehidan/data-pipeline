from unittest.mock import patch

import pytest

from sagemaker_studio.sql_engine.mysql_transformer import MySQLTransformer


def test_get_required_fields():
    assert MySQLTransformer.get_required_fields() == [
        "host",
        "port",
        "database",
        "user",
        "password",
    ]


def test_to_sqlalchemy_config_returns_expected_result():
    with patch.object(MySQLTransformer, "validate_required_fields") as mocked:
        connection_data = {
            "host": "localhost",
            "port": 3306,
            "database": "testdb",
            "user": "root",
            "password": "secret",
        }
        result = MySQLTransformer.to_sqlalchemy_config(connection_data)
        expected_conn_str = "mysql+pymysql://root@localhost:3306/testdb"
        assert result["connection_string"] == expected_conn_str
        assert result["connect_args"] == connection_data
        mocked.assert_called_once_with(
            ["host", "port", "database", "user", "password"], connection_data
        )


def test_to_sqlalchemy_config_raises_if_required_fields_missing():
    with patch.object(
        MySQLTransformer,
        "validate_required_fields",
        side_effect=ValueError("Missing required fields"),
    ):
        with pytest.raises(ValueError):
            MySQLTransformer.to_sqlalchemy_config({"host": "localhost"})
