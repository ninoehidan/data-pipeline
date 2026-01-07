import base64
import json
import urllib.parse
from unittest.mock import patch

import pytest

from sagemaker_studio.sql_engine.big_query_transformer import BigQueryTransformer


def test_get_required_fields():
    assert BigQueryTransformer.get_required_fields() == ["project_id"]


def test_to_sqlalchemy_config_builds_connection_string_and_encodes_data():
    with patch.object(BigQueryTransformer, "validate_required_fields") as mocked:
        connection_data = {
            "project_id": "test-proj",
            "client_email": "svc@test.iam.gserviceaccount.com",
            "private_key": "-----BEGIN PRIVATE KEY-----\nABC\n-----END PRIVATE KEY-----\n",
        }
        result = BigQueryTransformer.to_sqlalchemy_config(connection_data)
        assert "connection_string" in result
        cs = result["connection_string"]
        assert cs.startswith("bigquery://test-proj?")
        parsed = urllib.parse.urlparse(cs)
        params = urllib.parse.parse_qs(parsed.query)
        encoded = params.get("credentials_base64", [None])[0]
        assert encoded is not None
        decoded = json.loads(base64.b64decode(encoded).decode())
        assert decoded == connection_data
        mocked.assert_called_once_with(["project_id"], connection_data)


def test_to_sqlalchemy_config_raises_when_project_id_missing():
    with patch.object(
        BigQueryTransformer,
        "validate_required_fields",
        side_effect=ValueError("Missing required fields: project_id"),
    ):
        with pytest.raises(ValueError):
            BigQueryTransformer.to_sqlalchemy_config(
                {"client_email": "svc@test.iam.gserviceaccount.com", "private_key": "x"}
            )
