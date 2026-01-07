import unittest

from sagemaker_studio.sql_engine.database_transformer import DatabaseTransformer
from sagemaker_studio.sql_engine.resource_fetching_definition import (
    FetchMode,
    SQLAlchemyMetadataAction,
)


class TestValidateRequiredFields(unittest.TestCase):
    def test_all_required_fields_present(self):
        required = ["host", "port", "user"]
        data = {"host": "db.local", "port": 5432, "user": "alice"}
        DatabaseTransformer.validate_required_fields(required, data)

    def test_missing_required_field_key_raises(self):
        required = ["host"]
        data = {}
        with self.assertRaises(ValueError) as cm:
            DatabaseTransformer.validate_required_fields(required, data)
        self.assertIn("host is required for connection", str(cm.exception))

    def test_empty_string_value_raises(self):
        required = ["password"]
        data = {"password": ""}
        with self.assertRaises(ValueError) as cm:
            DatabaseTransformer.validate_required_fields(required, data)
        self.assertIn("password is required for connection", str(cm.exception))

    def test_none_value_raises(self):
        required = ["password"]
        data = {"password": None}
        with self.assertRaises(ValueError) as cm:
            DatabaseTransformer.validate_required_fields(required, data)
        self.assertIn("password is required for connection", str(cm.exception))

    def test_zero_value_raises_under_current_truthiness_logic(self):
        required = ["timeout"]
        data = {"timeout": 0}
        with self.assertRaises(ValueError) as cm:
            DatabaseTransformer.validate_required_fields(required, data)
        self.assertIn("timeout is required for connection", str(cm.exception))

    def test_empty_list_value_raises(self):
        required = ["options"]
        data = {"options": []}
        with self.assertRaises(ValueError) as cm:
            DatabaseTransformer.validate_required_fields(required, data)
        self.assertIn("options is required for connection", str(cm.exception))

    def test_whitespace_string_is_considered_present(self):
        required = ["notes"]
        data = {"notes": "   "}
        DatabaseTransformer.validate_required_fields(required, data)

    def test_no_required_fields_is_noop(self):
        required = []
        data = {}
        DatabaseTransformer.validate_required_fields(required, data)


class TestGetResourcesAction(unittest.TestCase):
    def test_table_returns_sqlalchemy_plan(self):
        plan = DatabaseTransformer.get_resources_action(
            "TABLE", parents={"DATABASE": "dev", "SCHEMA": "public"}
        )
        self.assertIs(plan.mode, FetchMode.SQLALCHEMY_METADATA)
        self.assertIs(plan.sqlalchemy_action, SQLAlchemyMetadataAction.GET_TABLE_NAMES)
        self.assertEqual(plan.default_type, "TABLE")
        self.assertEqual(plan.children, ("COLUMN",))
        self.assertIsNone(plan.sql)

    def test_column_returns_sqlalchemy_plan(self):
        plan = DatabaseTransformer.get_resources_action(
            "COLUMN", parents={"DATABASE": "dev", "SCHEMA": "public", "TABLE": "users"}
        )
        self.assertIs(plan.mode, FetchMode.SQLALCHEMY_METADATA)
        self.assertIs(plan.sqlalchemy_action, SQLAlchemyMetadataAction.GET_COLUMN_NAMES)
        self.assertEqual(plan.default_type, "COLUMN")
        self.assertEqual(plan.children, ())
        self.assertIsNone(plan.sql)

    def test_database_returns_sqlalchemy_plan(self):
        plan = DatabaseTransformer.get_resources_action("DATABASE")
        self.assertIs(plan.mode, FetchMode.SQLALCHEMY_METADATA)
        self.assertIs(plan.sqlalchemy_action, SQLAlchemyMetadataAction.GET_SCHEMA_NAMES)
        self.assertEqual(plan.default_type, "DATABASE")
        self.assertEqual(plan.children, ("TABLE",))
        self.assertIsNone(plan.sql)

    def test_none_defaults_to_database(self):
        plan_none = DatabaseTransformer.get_resources_action(None)
        plan_db = DatabaseTransformer.get_resources_action("DATABASE")

        self.assertIs(plan_none.mode, FetchMode.SQLALCHEMY_METADATA)
        self.assertIs(plan_none.sqlalchemy_action, SQLAlchemyMetadataAction.GET_SCHEMA_NAMES)
        self.assertEqual(plan_none.default_type, "DATABASE")
        self.assertEqual(plan_none.children, ("TABLE",))
        self.assertEqual(
            (
                plan_none.mode,
                plan_none.sqlalchemy_action,
                plan_none.default_type,
                plan_none.children,
            ),
            (plan_db.mode, plan_db.sqlalchemy_action, plan_db.default_type, plan_db.children),
        )

    def test_parents_argument_is_ignored(self):
        noisy_parents = {"DATABASE": "prod", "SCHEMA": "weird", "TABLE": "t", "EXTRA": "no-op"}
        plan_with = DatabaseTransformer.get_resources_action("TABLE", parents=noisy_parents)
        plan_without = DatabaseTransformer.get_resources_action("TABLE", parents=None)
        self.assertEqual(
            (
                plan_with.mode,
                plan_with.sqlalchemy_action,
                plan_with.default_type,
                plan_with.children,
            ),
            (
                plan_without.mode,
                plan_without.sqlalchemy_action,
                plan_without.default_type,
                plan_without.children,
            ),
        )

    def test_unsupported_type_raises_value_error(self):
        with self.assertRaises(ValueError) as cm:
            DatabaseTransformer.get_resources_action("VIEW")
        self.assertIn("Unsupported resource type", str(cm.exception))


class TestGetRequiredResourceParent(unittest.TestCase):
    def test_returns_value_when_present(self):
        parents = {"DATABASE": "dev", "SCHEMA": "public"}
        self.assertEqual(
            DatabaseTransformer.get_required_resource_parent(parents, "DATABASE"), "dev"
        )
        self.assertEqual(
            DatabaseTransformer.get_required_resource_parent(parents, "SCHEMA"), "public"
        )

    def test_returns_none_when_parents_is_none(self):
        self.assertIsNone(DatabaseTransformer.get_required_resource_parent(None, "SCHEMA"))

    def test_raises_keyerror_when_missing(self):
        parents = {"DATABASE": "dev"}
        with self.assertRaises(KeyError) as cm:
            DatabaseTransformer.get_required_resource_parent(parents, "SCHEMA")
        self.assertIn("Required parent type 'SCHEMA' not found", str(cm.exception))

    def test_does_not_mutate_input_mapping(self):
        parents = {"DATABASE": "dev", "SCHEMA": "public"}
        _ = DatabaseTransformer.get_required_resource_parent(parents, "DATABASE")
        self.assertEqual(parents, {"DATABASE": "dev", "SCHEMA": "public"})
