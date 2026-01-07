"""
Tests for SQLAlchemy dialect reflection capabilities.

This module tests the reflection and metadata introspection functionality
of the Redshift Data API dialect.
"""

from unittest.mock import Mock

from sqlalchemy import types

from ..dialect import RedshiftDataAPIDialect
from ..types import GEOMETRY, SUPER


class TestReflection:
    """Test reflection and metadata introspection methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.dialect = RedshiftDataAPIDialect()
        self.mock_connection = Mock()

    def test_get_schema_names(self):
        """Test getting list of schema names."""
        # Mock the query result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([("public",), ("analytics",), ("staging",)]))
        self.mock_connection.execute.return_value = mock_result

        # Call the method
        schemas = self.dialect.get_schema_names(self.mock_connection)

        # Verify the query was called correctly
        expected_query = """
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
ORDER BY schema_name
"""
        self.mock_connection.execute.assert_called_once()
        called_query = self.mock_connection.execute.call_args[0][0]
        # Now we expect a TextClause object, so we need to check its text attribute
        assert str(called_query).strip() == expected_query.strip()

        # Verify the result
        assert schemas == ["public", "analytics", "staging"]

    def test_get_table_names_default_schema(self):
        """Test getting table names from default schema."""
        # Mock the query result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([("users",), ("orders",), ("products",)]))
        self.mock_connection.execute.return_value = mock_result

        # Call the method without specifying schema
        tables = self.dialect.get_table_names(self.mock_connection)

        # Verify the query was called with default schema
        self.mock_connection.execute.assert_called_once()
        call_args = self.mock_connection.execute.call_args
        assert call_args[0][1] == ("public",)  # Default schema

        # Verify the result
        assert tables == ["users", "orders", "products"]

    def test_get_table_names_specific_schema(self):
        """Test getting table names from specific schema."""
        # Mock the query result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([("fact_sales",), ("dim_customer",)]))
        self.mock_connection.execute.return_value = mock_result

        # Call the method with specific schema
        tables = self.dialect.get_table_names(self.mock_connection, schema="analytics")

        # Verify the query was called with specified schema
        self.mock_connection.execute.assert_called_once()
        call_args = self.mock_connection.execute.call_args
        assert call_args[0][1] == ("analytics",)

        # Verify the result
        assert tables == ["fact_sales", "dim_customer"]

    def test_get_view_names(self):
        """Test getting view names."""
        # Mock the query result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([("customer_summary",), ("sales_report",)]))
        self.mock_connection.execute.return_value = mock_result

        # Call the method
        views = self.dialect.get_view_names(self.mock_connection, schema="analytics")

        # Verify the query was called correctly
        expected_query = """
SELECT table_name
FROM information_schema.views
WHERE table_schema = %s
ORDER BY table_name
"""
        called_query = self.mock_connection.execute.call_args[0][0]
        # Now we expect a TextClause object, so we need to check its text attribute
        assert str(called_query).strip() == expected_query.strip()

        # Verify the result
        assert views == ["customer_summary", "sales_report"]

    def test_get_columns_basic_types(self):
        """Test getting column information with basic data types."""
        # Mock the query result with various column types
        mock_result = Mock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [
                    ("id", "integer", "NO", None, None, None, None, 1),
                    ("name", "varchar", "YES", None, 255, None, None, 2),
                    ("price", "decimal", "YES", None, None, 10, 2, 3),
                    ("created_at", "timestamp", "NO", "now()", None, None, None, 4),
                    ("is_active", "boolean", "YES", "true", None, None, None, 5),
                ]
            )
        )
        self.mock_connection.execute.return_value = mock_result

        # Call the method
        columns = self.dialect.get_columns(self.mock_connection, "products", schema="public")

        # Verify the result structure
        assert len(columns) == 5

        # Check first column (integer)
        col1 = columns[0]
        assert col1["name"] == "id"
        assert isinstance(col1["type"], types.Integer)
        assert col1["nullable"] is False
        assert col1["default"] is None
        assert col1["autoincrement"] is False

        # Check second column (varchar with length)
        col2 = columns[1]
        assert col2["name"] == "name"
        assert isinstance(col2["type"], types.VARCHAR)
        assert col2["nullable"] is True

        # Check third column (decimal with precision/scale)
        col3 = columns[2]
        assert col3["name"] == "price"
        assert isinstance(col3["type"], types.Numeric)
        assert col3["nullable"] is True

        # Check fourth column (timestamp with default)
        col4 = columns[3]
        assert col4["name"] == "created_at"
        assert isinstance(col4["type"], types.TIMESTAMP)
        assert col4["nullable"] is False
        assert col4["default"] == "now()"

        # Check fifth column (boolean)
        col5 = columns[4]
        assert col5["name"] == "is_active"
        assert isinstance(col5["type"], types.Boolean)
        assert col5["nullable"] is True
        assert col5["default"] == "true"

    def test_get_columns_redshift_specific_types(self):
        """Test getting column information with Redshift-specific types."""
        # Mock the query result with Redshift-specific types
        mock_result = Mock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [
                    ("metadata", "super", "YES", None, None, None, None, 1),
                    ("location", "geometry", "YES", None, None, None, None, 2),
                ]
            )
        )
        self.mock_connection.execute.return_value = mock_result

        # Call the method
        columns = self.dialect.get_columns(self.mock_connection, "spatial_data")

        # Verify Redshift-specific types are handled
        assert len(columns) == 2

        # Check SUPER type
        col1 = columns[0]
        assert col1["name"] == "metadata"
        assert isinstance(col1["type"], SUPER)

        # Check GEOMETRY type
        col2 = columns[1]
        assert col2["name"] == "location"
        assert isinstance(col2["type"], GEOMETRY)

    def test_get_column_type_mapping(self):
        """Test the _get_column_type method for various type mappings."""
        # Test basic types
        assert isinstance(self.dialect._get_column_type("integer"), types.Integer)
        assert isinstance(self.dialect._get_column_type("bigint"), types.BigInteger)
        assert isinstance(self.dialect._get_column_type("smallint"), types.SmallInteger)
        assert isinstance(self.dialect._get_column_type("text"), types.Text)
        assert isinstance(self.dialect._get_column_type("boolean"), types.Boolean)
        assert isinstance(self.dialect._get_column_type("date"), types.Date)
        assert isinstance(self.dialect._get_column_type("real"), types.Float)
        assert isinstance(self.dialect._get_column_type("double precision"), types.Float)

        # Test types with parameters
        varchar_type = self.dialect._get_column_type("varchar", char_max_length=100)
        assert isinstance(varchar_type, types.VARCHAR)

        numeric_type = self.dialect._get_column_type(
            "numeric", numeric_precision=10, numeric_scale=2
        )
        assert isinstance(numeric_type, types.Numeric)

        # Test Redshift-specific types
        assert isinstance(self.dialect._get_column_type("super"), SUPER)
        assert isinstance(self.dialect._get_column_type("geometry"), GEOMETRY)

        # Test unknown type defaults to Text
        assert isinstance(self.dialect._get_column_type("unknown_type"), types.Text)

    def test_get_indexes(self):
        """Test getting index information (should return empty for Redshift)."""
        indexes = self.dialect.get_indexes(self.mock_connection, "test_table")

        # Redshift doesn't have traditional indexes, should return empty list
        assert indexes == []

    def test_get_pk_constraint_with_primary_key(self):
        """Test getting primary key constraint information."""
        # Mock the query result with primary key columns
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([("id", 1), ("tenant_id", 2)]))
        self.mock_connection.execute.return_value = mock_result

        # Call the method
        pk_info = self.dialect.get_pk_constraint(self.mock_connection, "users")

        # Verify the result
        assert pk_info["constrained_columns"] == ["id", "tenant_id"]
        assert pk_info["name"] is None  # Redshift doesn't always name PK constraints

    def test_get_pk_constraint_no_primary_key(self):
        """Test getting primary key constraint when none exists."""
        # Mock empty query result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        self.mock_connection.execute.return_value = mock_result

        # Call the method
        pk_info = self.dialect.get_pk_constraint(self.mock_connection, "logs")

        # Verify the result
        assert pk_info["constrained_columns"] == []
        assert pk_info["name"] is None

    def test_get_foreign_keys(self):
        """Test getting foreign key information."""
        # Mock the query result with foreign key information
        mock_result = Mock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [
                    ("user_id", "public", "users", "id", "fk_orders_user"),
                    ("product_id", "public", "products", "id", "fk_orders_product"),
                ]
            )
        )
        self.mock_connection.execute.return_value = mock_result

        # Call the method
        fk_info = self.dialect.get_foreign_keys(self.mock_connection, "orders")

        # Verify the result
        assert len(fk_info) == 2

        # Check first foreign key
        fk1 = fk_info[0]
        assert fk1["name"] == "fk_orders_user"
        assert fk1["constrained_columns"] == ["user_id"]
        assert fk1["referred_schema"] == "public"
        assert fk1["referred_table"] == "users"
        assert fk1["referred_columns"] == ["id"]

        # Check second foreign key
        fk2 = fk_info[1]
        assert fk2["name"] == "fk_orders_product"
        assert fk2["constrained_columns"] == ["product_id"]
        assert fk2["referred_schema"] == "public"
        assert fk2["referred_table"] == "products"
        assert fk2["referred_columns"] == ["id"]

    def test_get_foreign_keys_empty(self):
        """Test getting foreign keys when none exist."""
        # Mock empty query result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        self.mock_connection.execute.return_value = mock_result

        # Call the method
        fk_info = self.dialect.get_foreign_keys(self.mock_connection, "standalone_table")

        # Verify the result
        assert fk_info == []


class TestReflectionIntegration:
    """Integration tests for reflection with SQLAlchemy."""

    def test_reflection_methods_exist(self):
        """Test that all required reflection methods exist on the dialect."""
        dialect = RedshiftDataAPIDialect()

        # Check that all required reflection methods exist
        required_methods = [
            "get_schema_names",
            "get_table_names",
            "get_view_names",
            "get_columns",
            "get_indexes",
            "get_pk_constraint",
            "get_foreign_keys",
        ]

        for method_name in required_methods:
            assert hasattr(dialect, method_name), f"Missing method: {method_name}"
            assert callable(getattr(dialect, method_name)), f"Method not callable: {method_name}"
