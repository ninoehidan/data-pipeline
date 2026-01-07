import unittest

from sagemaker_studio.sql_engine.resource_fetching_definition import (
    FetchMode,
    ResourceFetchingDefinition,
    SQLAlchemyMetadataAction,
)


class TestResourceFetchingDefinition(unittest.TestCase):
    def test_sql_execution_factory_minimal(self):
        d = ResourceFetchingDefinition.from_sql_execution(
            "SELECT name FROM sys.databases",
            default_type="DATABASE",
        )
        self.assertIs(d.mode, FetchMode.SQL_EXECUTION)
        self.assertEqual(d.default_type, "DATABASE")
        self.assertEqual(d.children, ())
        self.assertEqual(d.sql, "SELECT name FROM sys.databases")
        self.assertIsNone(d.sql_parameters)
        self.assertIsNone(d.sqlalchemy_action)

    def test_sql_execution_factory_with_children_and_params_sequence(self):
        d = ResourceFetchingDefinition.from_sql_execution(
            "SELECT name FROM foo WHERE x = ? AND y = ?",
            default_type="TABLE",
            children=["COLUMN"],
            sql_parameters=[1, 2],
        )
        self.assertEqual(d.children, ("COLUMN",))
        self.assertEqual(d.sql_parameters, [1, 2])

    def test_sqlalchemy_metadata_factory_minimal(self):
        d = ResourceFetchingDefinition.from_sqlalchemy_metadata(
            SQLAlchemyMetadataAction.GET_SCHEMA_NAMES,
            default_type="SCHEMA",
        )
        self.assertIs(d.mode, FetchMode.SQLALCHEMY_METADATA)
        self.assertEqual(d.default_type, "SCHEMA")
        self.assertEqual(d.children, ())
        self.assertIsNone(d.sql)
        self.assertIs(d.sqlalchemy_action, SQLAlchemyMetadataAction.GET_SCHEMA_NAMES)

    def test_sqlalchemy_metadata_factory_with_children(self):
        d = ResourceFetchingDefinition.from_sqlalchemy_metadata(
            SQLAlchemyMetadataAction.GET_TABLE_NAMES,
            default_type="TABLE",
            children=["COLUMN"],
        )
        self.assertEqual(d.children, ("COLUMN",))

    def test_invariant_sql_execution_requires_sql(self):
        with self.assertRaises(ValueError) as cm:
            ResourceFetchingDefinition(
                mode=FetchMode.SQL_EXECUTION,
                default_type="TABLE",
                children=(),
                sql=None,
            )
        self.assertIn("requires `sql`", str(cm.exception))

    def test_invariant_sql_execution_forbids_sqlalchemy_action(self):
        with self.assertRaises(ValueError) as cm:
            ResourceFetchingDefinition(
                mode=FetchMode.SQL_EXECUTION,
                default_type="TABLE",
                children=(),
                sql="SELECT 1",
                sqlalchemy_action=SQLAlchemyMetadataAction.GET_TABLE_NAMES,
            )
        self.assertIn("must not set `sqlalchemy_action`", str(cm.exception))

    def test_invariant_metadata_requires_action(self):
        with self.assertRaises(ValueError) as cm:
            ResourceFetchingDefinition(
                mode=FetchMode.SQLALCHEMY_METADATA,
                default_type="SCHEMA",
                children=(),
                sqlalchemy_action=None,
            )
        self.assertIn("requires `sqlalchemy_action`", str(cm.exception))

    def test_invariant_metadata_forbids_sql(self):
        with self.assertRaises(ValueError) as cm:
            ResourceFetchingDefinition(
                mode=FetchMode.SQLALCHEMY_METADATA,
                default_type="SCHEMA",
                children=(),
                sqlalchemy_action=SQLAlchemyMetadataAction.GET_SCHEMA_NAMES,
                sql="SELECT 1",
            )
        self.assertIn("must not set `sql`", str(cm.exception))

    def test_unknown_mode_raises_value_error(self):
        with self.assertRaises(ValueError) as cm:
            ResourceFetchingDefinition(
                mode=object(),
                default_type="TABLE",
                children=(),
            )
        self.assertIn("Unknown mode", str(cm.exception))
