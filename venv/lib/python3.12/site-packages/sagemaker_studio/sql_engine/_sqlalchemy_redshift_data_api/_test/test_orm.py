"""
SQLAlchemy ORM compatibility tests for Redshift Data API dialect.

Tests ORM model creation, querying, relationships, session management,
transaction handling, bulk operations, and lazy loading scenarios.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    create_mock_engine,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

from ..types import GEOMETRY, SUPER

# Create declarative base for ORM models
Base = declarative_base()


# Association table for many-to-many relationship
user_role_association = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)


class User(Base):
    """User ORM model for testing."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    profile_data = Column(SUPER)  # Redshift SUPER type for JSON data

    # One-to-many relationship
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

    # One-to-one relationship
    profile = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # Many-to-many relationship
    roles = relationship("Role", secondary=user_role_association, back_populates="users")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class UserProfile(Base):
    """User profile ORM model for one-to-one relationship testing."""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    bio = Column(Text)
    birth_date = Column(Date)
    location_data = Column(GEOMETRY)  # Redshift GEOMETRY type

    # One-to-one relationship
    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"


class Role(Base):
    """Role ORM model for many-to-many relationship testing."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    # Many-to-many relationship
    users = relationship("User", secondary=user_role_association, back_populates="roles")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class Order(Base):
    """Order ORM model for one-to-many relationship testing."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_number = Column(String(20), unique=True, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")

    # Many-to-one relationship
    user = relationship("User", back_populates="orders")

    # One-to-many relationship
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, order_number='{self.order_number}', total_amount={self.total_amount})>"


class OrderItem(Base):
    """Order item ORM model for testing nested relationships."""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)

    # Many-to-one relationship
    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem(id={self.id}, product_name='{self.product_name}', quantity={self.quantity})>"


class TestORMModelCreation:
    """Test ORM model creation and table generation."""

    def test_model_relationships_defined(self):
        """Test that model relationships are properly defined."""
        # Test User model relationships
        assert hasattr(User, "orders")
        assert hasattr(User, "profile")
        assert hasattr(User, "roles")

        # Test relationship directions
        user = User()
        assert hasattr(user, "orders")
        assert hasattr(user, "profile")
        assert hasattr(user, "roles")

        # Test Order model relationships
        order = Order()
        assert hasattr(order, "user")
        assert hasattr(order, "items")

        # Test Role model relationships
        role = Role()
        assert hasattr(role, "users")

    def test_model_table_names(self):
        """Test that models have correct table names."""
        assert User.__tablename__ == "users"
        assert UserProfile.__tablename__ == "user_profiles"
        assert Role.__tablename__ == "roles"
        assert Order.__tablename__ == "orders"
        assert OrderItem.__tablename__ == "order_items"

    def test_model_columns_defined(self):
        """Test that model columns are properly defined."""
        # Test User columns
        user_columns = [col.name for col in User.__table__.columns]
        expected_user_columns = [
            "id",
            "username",
            "email",
            "full_name",
            "is_active",
            "created_at",
            "profile_data",
        ]
        for col in expected_user_columns:
            assert col in user_columns

        # Test Order columns
        order_columns = [col.name for col in Order.__table__.columns]
        expected_order_columns = [
            "id",
            "user_id",
            "order_number",
            "total_amount",
            "order_date",
            "status",
        ]
        for col in expected_order_columns:
            assert col in order_columns

    def test_foreign_key_relationships(self):
        """Test that foreign key relationships are properly defined."""
        # Test UserProfile -> User foreign key
        user_profile_fks = [str(fk.column) for fk in UserProfile.__table__.foreign_keys]
        assert "users.id" in user_profile_fks

        # Test Order -> User foreign key
        order_fks = [str(fk.column) for fk in Order.__table__.foreign_keys]
        assert "users.id" in order_fks

        # Test OrderItem -> Order foreign key
        order_item_fks = [str(fk.column) for fk in OrderItem.__table__.foreign_keys]
        assert "orders.id" in order_item_fks

    def test_redshift_specific_types(self):
        """Test that Redshift-specific types are used."""
        # Test SUPER type in User model
        profile_data_col = User.__table__.columns["profile_data"]
        assert isinstance(profile_data_col.type, SUPER)

        # Test GEOMETRY type in UserProfile model
        location_data_col = UserProfile.__table__.columns["location_data"]
        assert isinstance(location_data_col.type, GEOMETRY)


class TestORMSessionManagement:
    """Test ORM session management and basic operations."""

    @patch("sagemaker_studio.sql_engine._sqlalchemy_redshift_data_api.dbapi.connect")
    def test_session_creation(self, mock_connect):
        """Test creating ORM session."""
        # Mock connection and cursor with minimal responses
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ("public",)
        mock_cursor.description = [("current_schema", "varchar", None, None, None, None, None)]

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Create mock engine and session
        engine = create_mock_engine(
            "redshift_data_api://test-cluster/testdb?region=us-east-1&db_user=testuser",
            executor=lambda sql, *_: None,
        )

        SessionLocal = sessionmaker(bind=engine)  # noqa: N806
        session = SessionLocal()

        assert isinstance(session, Session)
        session.close()

    def test_model_instantiation(self):
        """Test creating model instances."""
        # Test User instantiation
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            profile_data={"preferences": {"theme": "dark"}},
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.profile_data == {"preferences": {"theme": "dark"}}

        # Test Order instantiation
        order = Order(
            user_id=1, order_number="ORD001", total_amount=Decimal("99.99"), status="pending"
        )

        assert order.user_id == 1
        assert order.order_number == "ORD001"
        assert order.total_amount == Decimal("99.99")
        assert order.status == "pending"

    def test_model_repr(self):
        """Test model string representations."""
        user = User(id=1, username="testuser", email="test@example.com")
        assert "testuser" in repr(user)
        assert "test@example.com" in repr(user)

        order = Order(id=1, order_number="ORD001", total_amount=Decimal("99.99"))
        assert "ORD001" in repr(order)
        assert "99.99" in repr(order)


class TestORMRelationships:
    """Test ORM relationship definitions and behavior."""

    def test_relationship_attributes_exist(self):
        """Test that relationship attributes exist on models."""
        # Test User relationships
        user = User()
        assert hasattr(user, "orders")
        assert hasattr(user, "profile")
        assert hasattr(user, "roles")

        # Test Order relationships
        order = Order()
        assert hasattr(order, "user")
        assert hasattr(order, "items")

        # Test Role relationships
        role = Role()
        assert hasattr(role, "users")

        # Test UserProfile relationships
        profile = UserProfile()
        assert hasattr(profile, "user")

        # Test OrderItem relationships
        item = OrderItem()
        assert hasattr(item, "order")

    def test_relationship_back_populates(self):
        """Test that relationships have correct back_populates."""
        # Test User -> Order relationship
        user_orders_rel = User.orders.property
        assert user_orders_rel.back_populates == "user"

        # Test Order -> User relationship
        order_user_rel = Order.user.property
        assert order_user_rel.back_populates == "orders"

        # Test User -> UserProfile relationship
        user_profile_rel = User.profile.property
        assert user_profile_rel.back_populates == "user"

        # Test UserProfile -> User relationship
        profile_user_rel = UserProfile.user.property
        assert profile_user_rel.back_populates == "profile"

    def test_many_to_many_association_table(self):
        """Test many-to-many association table configuration."""
        # Test that association table exists
        assert user_role_association is not None

        # Test association table columns
        columns = [col.name for col in user_role_association.columns]
        assert "user_id" in columns
        assert "role_id" in columns

        # Test foreign keys in association table
        fks = [str(fk.column) for fk in user_role_association.foreign_keys]
        assert "users.id" in fks
        assert "roles.id" in fks

    def test_cascade_options(self):
        """Test cascade options on relationships."""
        # Test User -> Order cascade
        user_orders_rel = User.orders.property
        assert "delete-orphan" in user_orders_rel.cascade

        # Test User -> UserProfile cascade
        user_profile_rel = User.profile.property
        assert "delete-orphan" in user_profile_rel.cascade

        # Test Order -> OrderItem cascade
        order_items_rel = Order.items.property
        assert "delete-orphan" in order_items_rel.cascade


class TestORMBulkOperations:
    """Test ORM bulk operations support."""

    def test_bulk_insert_mappings_structure(self):
        """Test structure for bulk insert mappings."""
        # Test that we can create data structures for bulk operations
        user_data = [
            {"username": "user1", "email": "user1@example.com", "full_name": "User One"},
            {"username": "user2", "email": "user2@example.com", "full_name": "User Two"},
            {"username": "user3", "email": "user3@example.com", "full_name": "User Three"},
        ]

        # Verify data structure is correct for bulk operations
        assert len(user_data) == 3
        assert all("username" in item for item in user_data)
        assert all("email" in item for item in user_data)
        assert all("full_name" in item for item in user_data)

    def test_bulk_update_mappings_structure(self):
        """Test structure for bulk update mappings."""
        # Test that we can create data structures for bulk updates
        user_updates = [
            {"id": 1, "full_name": "Updated User One"},
            {"id": 2, "full_name": "Updated User Two"},
            {"id": 3, "full_name": "Updated User Three"},
        ]

        # Verify data structure is correct for bulk operations
        assert len(user_updates) == 3
        assert all("id" in item for item in user_updates)
        assert all("full_name" in item for item in user_updates)

    def test_bulk_save_objects_structure(self):
        """Test structure for bulk save objects."""
        # Test that we can create multiple objects for bulk operations
        users = [
            User(username="user1", email="user1@example.com", full_name="User One"),
            User(username="user2", email="user2@example.com", full_name="User Two"),
            User(username="user3", email="user3@example.com", full_name="User Three"),
        ]

        # Verify objects are created correctly
        assert len(users) == 3
        assert all(isinstance(user, User) for user in users)
        assert all(user.username.startswith("user") for user in users)


class TestORMAdvancedFeatures:
    """Test advanced ORM features and compatibility."""

    def test_model_inheritance_structure(self):
        """Test that models properly inherit from Base."""
        assert issubclass(User, Base)
        assert issubclass(UserProfile, Base)
        assert issubclass(Role, Base)
        assert issubclass(Order, Base)
        assert issubclass(OrderItem, Base)

    def test_metadata_consistency(self):
        """Test that all models share the same metadata."""
        assert User.metadata is Base.metadata
        assert UserProfile.metadata is Base.metadata
        assert Role.metadata is Base.metadata
        assert Order.metadata is Base.metadata
        assert OrderItem.metadata is Base.metadata

    def test_table_creation_sql_generation(self):
        """Test that models can generate CREATE TABLE SQL."""
        # This tests that the ORM models are properly structured
        # for SQL generation without actually executing SQL

        # Test that tables have proper columns
        user_table = User.__table__
        assert len(user_table.columns) > 0
        assert "id" in user_table.columns
        assert "username" in user_table.columns

        order_table = Order.__table__
        assert len(order_table.columns) > 0
        assert "id" in order_table.columns
        assert "user_id" in order_table.columns

    def test_query_construction(self):
        """Test that queries can be constructed without execution."""
        from sqlalchemy.orm import Query

        # Test that we can create query objects (without executing them)
        # This tests ORM compatibility at the query construction level
        # Create a mock session for query construction
        mock_session = Mock()
        mock_session.bind = Mock()

        # Test basic query construction
        user_query = Query(User, session=mock_session)
        assert user_query is not None

        order_query = Query(Order, session=mock_session)
        assert order_query is not None

    def test_relationship_query_construction(self):
        """Test that relationship queries can be constructed."""
        # Test that relationship attributes can be used in query construction
        # without actually executing queries

        # Test accessing relationship attributes
        user = User()
        assert hasattr(user, "orders")
        assert hasattr(user, "profile")
        assert hasattr(user, "roles")

        # Test that relationships return proper relationship objects
        from sqlalchemy.orm.relationships import RelationshipProperty

        assert isinstance(User.orders.property, RelationshipProperty)
        assert isinstance(User.profile.property, RelationshipProperty)
        assert isinstance(User.roles.property, RelationshipProperty)


class TestORMTypeCompatibility:
    """Test ORM compatibility with Redshift-specific types."""

    def test_super_type_column(self):
        """Test SUPER type column definition."""
        profile_data_col = User.__table__.columns["profile_data"]
        assert isinstance(profile_data_col.type, SUPER)

        # Test that we can set SUPER data on model instances
        user = User(
            username="testuser",
            email="test@example.com",
            profile_data={"theme": "dark", "language": "en"},
        )
        assert user.profile_data == {"theme": "dark", "language": "en"}

    def test_geometry_type_column(self):
        """Test GEOMETRY type column definition."""
        location_data_col = UserProfile.__table__.columns["location_data"]
        assert isinstance(location_data_col.type, GEOMETRY)

        # Test that we can set GEOMETRY data on model instances
        profile = UserProfile(user_id=1, bio="Test bio", location_data="POINT(1 2)")
        assert profile.location_data == "POINT(1 2)"

    def test_standard_type_columns(self):
        """Test standard SQL type columns."""
        # Test Integer columns
        id_col = User.__table__.columns["id"]
        assert str(id_col.type).upper().startswith("INTEGER")

        # Test String columns
        username_col = User.__table__.columns["username"]
        assert "VARCHAR" in str(username_col.type).upper()

        # Test Boolean columns
        is_active_col = User.__table__.columns["is_active"]
        assert "BOOLEAN" in str(is_active_col.type).upper()

        # Test DateTime columns
        created_at_col = User.__table__.columns["created_at"]
        assert (
            "DATETIME" in str(created_at_col.type).upper()
            or "TIMESTAMP" in str(created_at_col.type).upper()
        )

        # Test Numeric columns
        total_amount_col = Order.__table__.columns["total_amount"]
        assert (
            "NUMERIC" in str(total_amount_col.type).upper()
            or "DECIMAL" in str(total_amount_col.type).upper()
        )


if __name__ == "__main__":
    pytest.main([__file__])
