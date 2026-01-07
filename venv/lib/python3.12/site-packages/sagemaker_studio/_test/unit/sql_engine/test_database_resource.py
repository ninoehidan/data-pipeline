import unittest

from sagemaker_studio.sql_engine.database_resource import DatabaseResource


class TestDatabaseResource(unittest.TestCase):
    def test_requires_name_and_type(self):
        with self.assertRaises(TypeError):
            DatabaseResource()
        with self.assertRaises(TypeError):
            DatabaseResource(name="public")
        with self.assertRaises(TypeError):
            DatabaseResource(type="SCHEMA")

    def test_children_defaults_to_empty_list(self):
        r = DatabaseResource(name="public", type="SCHEMA")
        self.assertIsInstance(r.children, list)
        self.assertEqual(r.children, [])
