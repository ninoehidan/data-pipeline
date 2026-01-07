import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from sagemaker_studio.sql_engine.resource_fetching_definition import (
    FetchMode,
    ResourceFetchingDefinition,
)
from sagemaker_studio.sql_engine.sql_executor import SqlExecutor


class TestGetResources(unittest.TestCase):
    def setUp(self):
        self.svc = SqlExecutor()
        if not hasattr(self.svc, "_transformer_classes"):
            self.svc._transformer_classes = {}
        self.engine = Mock(name="Engine")

    def _register_transformer(self, connection_type, transformer_obj):
        self.svc._transformer_classes[connection_type] = transformer_obj

    def test_unsupported_connection_type_raises(self):
        with self.assertRaises(ValueError) as cm:
            self.svc.get_resources(
                engine=self.engine,
                connection_type="unknown",
                resource_type="DATABASE",
                parents={},
            )
        self.assertIn("Unsupported connection type", str(cm.exception))

    def test_metadata_unsupported_action_raises(self):
        class Tx:
            @staticmethod
            def get_resources_action(resource_type, parents):
                return ResourceFetchingDefinition(
                    mode=FetchMode.SQLALCHEMY_METADATA,
                    default_type="SCHEMA",
                    children=(),
                    sqlalchemy_action=object(),
                )

        self._register_transformer("redshift", Tx)

        with self.assertRaises(ValueError) as cm:
            self.svc.get_resources(
                engine=self.engine,
                connection_type="redshift",
                resource_type="SCHEMA",
                parents={"DATABASE": "dev"},
            )
        self.assertIn("Unsupported SQLAlchemy metadata action", str(cm.exception))

    def test_sql_execution_happy_path(self):
        class Tx:
            @staticmethod
            def get_resources_action(resource_type, parents):
                return ResourceFetchingDefinition.from_sql_execution(
                    "SELECT name FROM t",
                    default_type="TABLE",
                    children=("COLUMN",),
                    sql_parameters={"p": 1},
                )

        self._register_transformer("pg", Tx)
        df = pd.DataFrame({"name": ["a", "b"], "ignored": [1, 2]})
        self.svc.execute = Mock(return_value=df)

        out = self.svc.get_resources(
            engine=self.engine,
            connection_type="pg",
            resource_type=None,
            parents={},
        )
        self.svc.execute.assert_called_once_with(self.engine, "SELECT name FROM t", {"p": 1})
        self.assertEqual([r.name for r in out], ["a", "b"])
        self.assertEqual([r.type for r in out], ["TABLE", "TABLE"])
        self.assertEqual([r.children for r in out], [["COLUMN"], ["COLUMN"]])

    def test_sql_execution_empty_dataframe_yields_no_resources(self):
        class Tx:
            @staticmethod
            def get_resources_action(resource_type, parents):
                return ResourceFetchingDefinition.from_sql_execution(
                    "SELECT 1 WHERE 0=1",
                    default_type="DATABASE",
                    children=("SCHEMA",),
                )

        self._register_transformer("pg", Tx)
        empty_df = pd.DataFrame()
        self.svc.execute = Mock(return_value=empty_df)

        out = self.svc.get_resources(
            engine=self.engine,
            connection_type="pg",
            resource_type=None,
            parents={},
        )
        self.assertEqual(out, [])

    def test_unsupported_fetch_mode_raises(self):
        class Tx:
            @staticmethod
            def get_resources_action(resource_type, parents):
                return SimpleNamespace(
                    mode="WEIRD_MODE",
                    default_type="SCHEMA",
                    children=("TABLE",),
                    sqlalchemy_action=None,
                    sql=None,
                    sql_parameters=None,
                )

        self._register_transformer("pg", Tx)
        self.svc.execute = Mock()

        with self.assertRaises(ValueError) as cm:
            self.svc.get_resources(
                engine=self.engine,
                connection_type="pg",
                resource_type=None,
                parents={},
            )
        self.assertIn("Unsupported resource fetching mode", str(cm.exception))
