import unittest

from sagemaker_studio.sql_engine.redshift_transformer import RedshiftTransformer
from sagemaker_studio.sql_engine.resource_fetching_definition import FetchMode


class TestRedshiftTransformerGetResourcesAction(unittest.TestCase):
    def test_database_returns_sql_execution_plan(self):
        plan = RedshiftTransformer.get_resources_action("DATABASE")
        self.assertIs(plan.mode, FetchMode.SQL_EXECUTION)
        self.assertIn("svv_redshift_databases", plan.sql.lower())
        self.assertEqual(plan.default_type, "DATABASE")
        self.assertEqual(plan.children, ("SCHEMA",))
        self.assertIsNone(plan.sql_parameters)

    def test_none_defaults_to_database(self):
        plan = RedshiftTransformer.get_resources_action(None)
        self.assertIs(plan.mode, FetchMode.SQL_EXECUTION)
        self.assertIn("svv_redshift_databases", plan.sql.lower())
        self.assertEqual(plan.default_type, "DATABASE")
        self.assertEqual(plan.children, ("SCHEMA",))
        self.assertIsNone(plan.sql_parameters)

    def test_schema_requires_database_parent_and_builds_sql(self):
        plan = RedshiftTransformer.get_resources_action("SCHEMA", parents={"DATABASE": "dev"})
        self.assertIs(plan.mode, FetchMode.SQL_EXECUTION)
        self.assertIn("svv_all_schemas", plan.sql.lower())
        self.assertIn(
            "not in ('pg_catalog', 'pg_internal', 'information_schema')".lower(), plan.sql.lower()
        )
        self.assertEqual(plan.default_type, "SCHEMA")
        self.assertEqual(plan.children, ("TABLE",))
        self.assertEqual(plan.sql_parameters, {"database": "dev"})

    def test_schema_with_parents_none_produces_none_parameter(self):
        plan = RedshiftTransformer.get_resources_action("SCHEMA", parents=None)
        self.assertEqual(plan.sql_parameters, {"database": None})

    def test_schema_raises_when_database_missing_from_mapping(self):
        with self.assertRaises(KeyError):
            RedshiftTransformer.get_resources_action("SCHEMA", parents={})

    def test_table_requires_database_and_schema_parents_and_builds_sql(self):
        plan = RedshiftTransformer.get_resources_action(
            "TABLE", parents={"DATABASE": "dev", "SCHEMA": "public"}
        )
        self.assertIs(plan.mode, FetchMode.SQL_EXECUTION)
        self.assertIn("svv_all_tables", plan.sql.lower())
        self.assertIn("table_type in ('table','external table')".lower(), plan.sql.lower())
        self.assertEqual(plan.default_type, "TABLE")
        self.assertEqual(plan.children, ("COLUMN",))
        self.assertEqual(plan.sql_parameters, {"database": "dev", "schema": "public"})

    def test_table_raises_when_schema_missing(self):
        with self.assertRaises(KeyError):
            RedshiftTransformer.get_resources_action(
                "TABLE", parents={"DATABASE": "dev"}  # SCHEMA missing
            )

    def test_table_raises_when_database_missing(self):
        with self.assertRaises(KeyError):
            RedshiftTransformer.get_resources_action(
                "TABLE", parents={"SCHEMA": "public"}  # DATABASE missing
            )

    def test_column_requires_database_schema_table_and_builds_sql(self):
        plan = RedshiftTransformer.get_resources_action(
            "COLUMN",
            parents={"DATABASE": "dev", "SCHEMA": "public", "TABLE": "users"},
        )
        self.assertIs(plan.mode, FetchMode.SQL_EXECUTION)
        self.assertIn("svv_all_columns", plan.sql.lower())
        self.assertIn("order by ordinal_position".lower(), plan.sql.lower())
        self.assertEqual(plan.default_type, "COLUMN")
        self.assertEqual(plan.children, ())
        self.assertEqual(
            plan.sql_parameters,
            {"database": "dev", "schema": "public", "table": "users"},
        )

    def test_column_raises_when_any_parent_missing(self):
        with self.assertRaises(KeyError):
            RedshiftTransformer.get_resources_action(
                "COLUMN",
                parents={"DATABASE": "dev", "SCHEMA": "public"},
            )
        with self.assertRaises(KeyError):
            RedshiftTransformer.get_resources_action(
                "COLUMN",
                parents={"DATABASE": "dev", "TABLE": "users"},
            )
        with self.assertRaises(KeyError):
            RedshiftTransformer.get_resources_action(
                "COLUMN",
                parents={"SCHEMA": "public", "TABLE": "users"},
            )

    def test_unsupported_resource_type_raises_value_error(self):
        with self.assertRaises(ValueError) as cm:
            RedshiftTransformer.get_resources_action("VIEW")
        self.assertIn("Unsupported resource type", str(cm.exception))
