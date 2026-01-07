"""
Unit tests for dataframeutils module.
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

# Mock external dependencies before importing dataframeutils
sys.modules["pyiceberg"] = MagicMock()
sys.modules["pyiceberg.catalog"] = MagicMock()
sys.modules["pyiceberg.exceptions"] = MagicMock()
sys.modules["awswrangler"] = MagicMock()
sys.modules["awswrangler.catalog"] = MagicMock()
sys.modules["awswrangler.s3"] = MagicMock()

# Import after mocking - this is necessary for proper module mocking
from sagemaker_studio import dataframeutils  # noqa: E402


class TestReadCatalogTable:
    """Test cases for read_catalog_table function."""

    def test_read_native_catalog_with_format(self):
        """Test reading from NATIVE catalog with explicit format."""
        with patch("sagemaker_studio.utils.dataframeutils._ensure_project") as mock_ensure_project:
            # Setup mocks
            mock_project = Mock()
            mock_connection = Mock()
            mock_catalog = Mock()
            mock_catalog.type = "NATIVE"
            mock_catalog.id = "123456789012"

            mock_ensure_project.return_value = mock_project
            mock_project.connection.return_value = mock_connection
            mock_connection.catalog.return_value = mock_catalog

            # Create expected DataFrame
            expected_df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

            # Configure the mocked awswrangler module chain
            import sys

            mock_wr = sys.modules["awswrangler"]
            # Reset the mock to avoid interference from other tests
            mock_wr.reset_mock()
            mock_wr.catalog.get_table_location.return_value = "s3://bucket/path/table/"
            mock_wr.s3.read_parquet.return_value = expected_df

            # Test
            result = dataframeutils.read_catalog_table(
                database="test_db", table="test_table", format="parquet", catalog="test_catalog"
            )

            # Assertions
            pd.testing.assert_frame_equal(result, expected_df)
            mock_connection.catalog.assert_called_once_with(id="test_catalog")
            mock_wr.catalog.get_table_location.assert_called_once_with(
                database="test_db", table="test_table", catalog_id="123456789012"
            )
            mock_wr.s3.read_parquet.assert_called_once_with(path="s3://bucket/path/table/")

    def test_read_native_catalog_auto_format(self):
        """Test reading from NATIVE catalog with auto-detected format."""
        with patch("sagemaker_studio.utils.dataframeutils._ensure_project") as mock_ensure_project:
            # Setup mocks
            mock_project = Mock()
            mock_connection = Mock()
            mock_catalog = Mock()
            mock_catalog.type = "NATIVE"
            mock_catalog.id = "123456789012"

            mock_ensure_project.return_value = mock_project
            mock_project.connection.return_value = mock_connection
            mock_connection.catalog.return_value = mock_catalog

            # Create expected DataFrame
            expected_df = pd.DataFrame({"col1": [1, 2]})

            # Configure the mocked awswrangler module chain
            import sys

            mock_wr = sys.modules["awswrangler"]
            # Reset the mock to avoid interference from other tests
            mock_wr.reset_mock()
            mock_wr.catalog.get_table_parameters.return_value = {"classification": "csv"}
            mock_wr.catalog.get_table_location.return_value = "s3://bucket/path/table/"
            mock_wr.s3.read_csv.return_value = expected_df

            # Test
            result = dataframeutils.read_catalog_table(database="test_db", table="test_table")

            # Assertions
            pd.testing.assert_frame_equal(result, expected_df)
            mock_wr.catalog.get_table_parameters.assert_called_once_with(
                database="test_db", table="test_table", catalog_id="123456789012"
            )
            mock_wr.s3.read_csv.assert_called_once_with(path="s3://bucket/path/table/")

    def test_read_native_catalog_fallback_format(self):
        """Test reading from NATIVE catalog with fallback to parquet when no classification."""
        with patch("sagemaker_studio.utils.dataframeutils._ensure_project") as mock_ensure_project:
            # Setup mocks
            mock_project = Mock()
            mock_connection = Mock()
            mock_catalog = Mock()
            mock_catalog.type = "NATIVE"
            mock_catalog.id = "123456789012"

            mock_ensure_project.return_value = mock_project
            mock_project.connection.return_value = mock_connection
            mock_connection.catalog.return_value = mock_catalog

            # Create expected DataFrame
            expected_df = pd.DataFrame({"col1": [1, 2]})

            # Configure the mocked awswrangler module chain
            import sys

            mock_wr = sys.modules["awswrangler"]
            # Reset the mock to avoid interference from other tests
            mock_wr.reset_mock()
            mock_wr.catalog.get_table_parameters.return_value = {}  # No classification
            mock_wr.catalog.get_table_location.return_value = "s3://bucket/path/table/"
            mock_wr.s3.read_parquet.return_value = expected_df

            # Test
            result = dataframeutils.read_catalog_table(database="test_db", table="test_table")

            # Assertions
            pd.testing.assert_frame_equal(result, expected_df)
            mock_wr.s3.read_parquet.assert_called_once_with(path="s3://bucket/path/table/")

    def test_read_native_catalog_exception_fallback_format(self):
        """Test reading from NATIVE catalog with fallback to parquet when get_table_parameters fails."""
        with patch("sagemaker_studio.utils.dataframeutils._ensure_project") as mock_ensure_project:
            # Setup mocks
            mock_project = Mock()
            mock_connection = Mock()
            mock_catalog = Mock()
            mock_catalog.type = "NATIVE"
            mock_catalog.id = "123456789012"

            mock_ensure_project.return_value = mock_project
            mock_project.connection.return_value = mock_connection
            mock_connection.catalog.return_value = mock_catalog

            # Create expected DataFrame
            expected_df = pd.DataFrame({"col1": [1, 2]})

            # Configure the mocked awswrangler module chain
            import sys

            mock_wr = sys.modules["awswrangler"]
            # Reset the mock to avoid interference from other tests
            mock_wr.reset_mock()
            # Simulate exception when getting table parameters
            mock_wr.catalog.get_table_parameters.side_effect = Exception("Access denied")
            mock_wr.catalog.get_table_location.return_value = "s3://bucket/path/table/"
            mock_wr.s3.read_parquet.return_value = expected_df

            # Test
            result = dataframeutils.read_catalog_table(database="test_db", table="test_table")

            # Assertions
            pd.testing.assert_frame_equal(result, expected_df)
            mock_wr.catalog.get_table_parameters.assert_called_once_with(
                database="test_db", table="test_table", catalog_id="123456789012"
            )
            mock_wr.s3.read_parquet.assert_called_once_with(path="s3://bucket/path/table/")

    def test_read_native_catalog_unsupported_format(self):
        """Test reading from NATIVE catalog with unsupported format raises exception."""
        with patch("sagemaker_studio.utils.dataframeutils._ensure_project") as mock_ensure_project:
            # Setup mocks
            mock_project = Mock()
            mock_connection = Mock()
            mock_catalog = Mock()
            mock_catalog.type = "NATIVE"
            mock_catalog.id = "123456789012"

            mock_ensure_project.return_value = mock_project
            mock_project.connection.return_value = mock_connection
            mock_connection.catalog.return_value = mock_catalog

            # Configure the mocked awswrangler module chain
            import sys

            mock_wr = sys.modules["awswrangler"]
            mock_wr.catalog.get_table_location.return_value = "s3://bucket/path/"

            # Mock awswrangler.s3 to not have the unsupported format
            # Use delattr to ensure the attribute doesn't exist
            if hasattr(mock_wr.s3, "read_unsupported"):
                delattr(mock_wr.s3, "read_unsupported")

            with pytest.raises(
                Exception, match="Unsupported format 'unsupported' for AwsDataCatalog"
            ):
                dataframeutils.read_catalog_table(
                    database="test_db", table="test_table", format="unsupported"
                )

    @patch("sagemaker_studio.utils.dataframeutils._ensure_project")
    def test_read_unsupported_catalog_type(self, mock_ensure_project):
        """Test reading from unsupported catalog type raises ValueError."""
        # Setup mocks
        mock_project = Mock()
        mock_connection = Mock()
        mock_catalog = Mock()
        mock_catalog.type = "UNSUPPORTED"

        mock_ensure_project.return_value = mock_project
        mock_project.connection.return_value = mock_connection
        mock_connection.catalog.return_value = mock_catalog

        with pytest.raises(
            ValueError,
            match="Unable to read from catalog. Catalog type 'UNSUPPORTED' not supported.",
        ):
            dataframeutils.read_catalog_table(database="test_db", table="test_table")


class TestParseProjectPathFromS3RootPath:
    """Test cases for _parse_project_path_from_s3_root_path function."""

    def test_project_id_in_bucket_name(self):
        """Test when project ID is embedded in bucket name."""
        project_id = "abc123"
        s3_root = "s3://project-abc123-bucket/shared/data"

        result = dataframeutils._parse_project_path_from_s3_root_path(project_id, s3_root)

        assert result == "s3://project-abc123-bucket"

    def test_project_id_in_path_component(self):
        """Test when project ID appears as path component."""
        project_id = "abc123"
        s3_root = "s3://bucket/abc123/dev/data"

        result = dataframeutils._parse_project_path_from_s3_root_path(project_id, s3_root)

        assert result == "s3://bucket/abc123"

    def test_project_id_not_found_fallback(self):
        """Test fallback when project ID is not found."""
        project_id = "xyz789"
        s3_root = "s3://bucket/other/path"

        result = dataframeutils._parse_project_path_from_s3_root_path(project_id, s3_root)

        assert result == "s3://bucket/other/path"

    def test_trailing_slash_handling(self):
        """Test that trailing slashes are properly handled."""
        project_id = "abc123"
        s3_root = "s3://bucket/abc123/dev/"

        result = dataframeutils._parse_project_path_from_s3_root_path(project_id, s3_root)

        assert result == "s3://bucket/abc123"

    def test_minimal_s3_path(self):
        """Test with minimal S3 path structure."""
        project_id = "abc123"
        s3_root = "s3://bucket"

        result = dataframeutils._parse_project_path_from_s3_root_path(project_id, s3_root)

        assert result == "s3://bucket"


class TestDetermineTablePath:
    """Test cases for _determine_table_path function."""

    @patch("sagemaker_studio.utils.dataframeutils._parse_project_path_from_s3_root_path")
    def test_database_with_location_uri(self, mock_parse_path):
        """Test when database exists and has location_uri."""
        # Setup mocks
        mock_project = Mock()
        mock_catalog = Mock()
        mock_db = Mock()
        mock_db.name = "test_db"
        mock_db.location_uri = "s3://bucket/db/location/"
        mock_catalog.databases = [mock_db]

        result = dataframeutils._determine_table_path(
            mock_project, mock_catalog, "test_db", "test_table"
        )

        assert result == "s3://bucket/db/location/test_table"
        mock_parse_path.assert_not_called()

    def test_existing_table_location(self):
        """Test when table exists and has location."""
        # Setup mocks
        mock_project = Mock()
        mock_catalog = Mock()
        mock_catalog.id = "catalog123"
        mock_db = Mock()
        mock_db.name = "test_db"
        mock_db.location_uri = None
        mock_catalog.databases = [mock_db]

        # Configure the mocked awswrangler module
        import sys

        mock_wr = sys.modules["awswrangler"]
        mock_wr.reset_mock()
        mock_wr.catalog.get_table_location.return_value = "s3://bucket/table/location/"

        result = dataframeutils._determine_table_path(
            mock_project, mock_catalog, "test_db", "test_table"
        )

        assert result == "s3://bucket/table/location/"
        mock_wr.catalog.get_table_location.assert_called_once_with(
            database="test_db", table="test_table", catalog_id="catalog123"
        )

    def test_database_not_exists(self):
        """Test when database doesn't exist."""
        with patch(
            "sagemaker_studio.utils.dataframeutils._parse_project_path_from_s3_root_path"
        ) as mock_parse_path, patch(
            "sagemaker_studio.utils.dataframeutils._create_database_with_location"
        ) as mock_create_db:

            # Setup mocks
            mock_project = Mock()
            mock_project.id = "proj123"
            mock_project.s3.root = "s3://bucket/proj123/root"
            mock_catalog = Mock()
            mock_catalog.databases = []

            mock_parse_path.return_value = "s3://bucket/proj123"

            result = dataframeutils._determine_table_path(
                mock_project, mock_catalog, "test_db", "test_table"
            )

            assert result == "s3://bucket/proj123/catalog/test_db/test_table"
            mock_create_db.assert_called_once_with(
                mock_catalog, "test_db", "s3://bucket/proj123/catalog/test_db"
            )

    @patch("sagemaker_studio.utils.dataframeutils._parse_project_path_from_s3_root_path")
    def test_exception_fallback(self, mock_parse_path):
        """Test fallback when exception occurs."""
        # Setup mocks
        mock_project = Mock()
        mock_project.id = "proj123"
        mock_project.s3.root = "s3://bucket/proj123/root"
        mock_catalog = Mock()
        mock_catalog.databases = Mock(side_effect=Exception("Database access error"))

        mock_parse_path.return_value = "s3://bucket/proj123"

        result = dataframeutils._determine_table_path(
            mock_project, mock_catalog, "test_db", "test_table"
        )

        assert result == "s3://bucket/proj123/catalog/test_db/test_table"


class TestEnsureDatabaseExists:
    """Test cases for _ensure_database_exists function."""

    @patch("sagemaker_studio.utils.dataframeutils._create_database_with_location")
    def test_database_already_exists(self, mock_create_db):
        """Test when database already exists."""
        # Setup mocks
        mock_project = Mock()
        mock_catalog = Mock()
        mock_db = Mock()
        mock_db.name = "test_db"
        mock_catalog.databases = [mock_db]

        dataframeutils._ensure_database_exists(mock_project, mock_catalog, "test_db")

        mock_create_db.assert_not_called()

    @patch("sagemaker_studio.utils.dataframeutils._parse_project_path_from_s3_root_path")
    @patch("sagemaker_studio.utils.dataframeutils._create_database_with_location")
    def test_create_database_with_user_path(self, mock_create_db, mock_parse_path):
        """Test creating database with user-provided path."""
        # Setup mocks
        mock_project = Mock()
        mock_catalog = Mock()
        mock_catalog.databases = []

        dataframeutils._ensure_database_exists(
            mock_project, mock_catalog, "test_db", user_path="s3://custom/path/"
        )

        mock_create_db.assert_called_once_with(mock_catalog, "test_db", "s3://custom/path")
        mock_parse_path.assert_not_called()

    @patch("sagemaker_studio.utils.dataframeutils._parse_project_path_from_s3_root_path")
    @patch("sagemaker_studio.utils.dataframeutils._create_database_with_location")
    def test_create_database_default_path(self, mock_create_db, mock_parse_path):
        """Test creating database with default project path."""
        # Setup mocks
        mock_project = Mock()
        mock_project.id = "proj123"
        mock_project.s3.root = "s3://bucket/proj123/root"
        mock_catalog = Mock()
        mock_catalog.databases = []

        mock_parse_path.return_value = "s3://bucket/proj123"

        dataframeutils._ensure_database_exists(mock_project, mock_catalog, "test_db")

        mock_create_db.assert_called_once_with(
            mock_catalog, "test_db", "s3://bucket/proj123/catalog/test_db"
        )

    def test_exception_handling(self):
        """Test exception handling when database operations fail."""
        # Setup mocks
        mock_project = Mock()
        mock_catalog = Mock()
        mock_catalog.databases = Mock(side_effect=Exception("Database error"))

        with pytest.raises(AttributeError, match="Failed to ensure database 'test_db' exists"):
            dataframeutils._ensure_database_exists(mock_project, mock_catalog, "test_db")


class TestCreateDatabaseWithLocation:
    """Test cases for _create_database_with_location function."""

    def test_create_database_success(self):
        """Test successful database creation."""
        mock_catalog = Mock()
        mock_catalog.id = "catalog123"

        # Configure the mocked awswrangler module
        import sys

        mock_wr = sys.modules["awswrangler"]
        mock_wr.reset_mock()

        dataframeutils._create_database_with_location(
            mock_catalog, "test_db", "s3://bucket/db/location"
        )

        mock_wr.catalog.create_database.assert_called_once_with(
            name="test_db",
            database_input_args={"LocationUri": "s3://bucket/db/location"},
            catalog_id="catalog123",
        )

    def test_create_database_exception_handled(self):
        """Test that exceptions during database creation are handled gracefully."""
        mock_catalog = Mock()
        mock_catalog.id = "catalog123"

        # Configure the mocked awswrangler module
        import sys

        mock_wr = sys.modules["awswrangler"]
        mock_wr.reset_mock()
        mock_wr.catalog.create_database.side_effect = Exception("Database creation failed")

        # Should not raise exception
        dataframeutils._create_database_with_location(
            mock_catalog, "test_db", "s3://bucket/db/location"
        )

        mock_wr.catalog.create_database.assert_called_once()


class TestToCatalogTable:
    """Test cases for to_catalog_table function."""

    def test_write_native_catalog(self):
        """Test writing to NATIVE catalog."""
        with patch(
            "sagemaker_studio.utils.dataframeutils._ensure_project"
        ) as mock_ensure_project, patch(
            "sagemaker_studio.utils.dataframeutils._determine_table_path"
        ) as mock_determine_path, patch(
            "sagemaker_studio.utils.dataframeutils._ensure_database_exists"
        ) as mock_ensure_db:

            # Setup mocks
            mock_project = Mock()
            mock_connection = Mock()
            mock_catalog = Mock()
            mock_catalog.type = "NATIVE"
            mock_catalog.id = "catalog123"

            mock_ensure_project.return_value = mock_project
            mock_project.connection.return_value = mock_connection
            mock_connection.catalog.return_value = mock_catalog
            mock_determine_path.return_value = "s3://bucket/table/path"

            # Configure the mocked awswrangler module
            import sys

            mock_wr = sys.modules["awswrangler"]
            mock_wr.reset_mock()

            # Test DataFrame
            df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

            dataframeutils.to_catalog_table(
                df, database="test_db", table="test_table", format="parquet"
            )

            # Assertions
            mock_ensure_db.assert_called_once_with(
                mock_project, mock_catalog, "test_db", user_path="s3://bucket/table/path"
            )
            mock_wr.s3.to_parquet.assert_called_once_with(
                df=df,
                path="s3://bucket/table/path",
                database="test_db",
                table="test_table",
                dataset=True,
            )

    def test_write_native_catalog_unsupported_format(self):
        """Test writing to NATIVE catalog with unsupported format."""
        with patch(
            "sagemaker_studio.utils.dataframeutils._ensure_project"
        ) as mock_ensure_project, patch(
            "sagemaker_studio.utils.dataframeutils._determine_table_path"
        ) as mock_determine_path:

            # Setup mocks
            mock_project = Mock()
            mock_connection = Mock()
            mock_catalog = Mock()
            mock_catalog.type = "NATIVE"
            # Make databases iterable to prevent TypeError in _ensure_database_exists
            mock_db = Mock()
            mock_db.name = "test_db"
            mock_catalog.databases = [mock_db]

            mock_ensure_project.return_value = mock_project
            mock_project.connection.return_value = mock_connection
            mock_connection.catalog.return_value = mock_catalog
            mock_determine_path.return_value = "s3://bucket/table/path"

            # Configure the mocked awswrangler module
            import sys

            mock_wr = sys.modules["awswrangler"]
            mock_wr.reset_mock()

            # Mock awswrangler.s3 to not have the unsupported format
            if hasattr(mock_wr.s3, "to_unsupported"):
                delattr(mock_wr.s3, "to_unsupported")

            df = pd.DataFrame({"col1": [1, 2]})

            with pytest.raises(
                Exception, match="Unsupported format 'unsupported' for AwsDataCatalog"
            ):
                dataframeutils.to_catalog_table(
                    df, database="test_db", table="test_table", format="unsupported"
                )

    @patch("sagemaker_studio.utils.dataframeutils._ensure_project")
    @patch("sagemaker_studio.utils.dataframeutils._determine_table_path")
    @patch("sagemaker_studio.utils.dataframeutils._ensure_database_exists")
    def test_write_unsupported_catalog_type(
        self, mock_ensure_db, mock_determine_path, mock_ensure_project
    ):
        """Test writing to unsupported catalog type raises ValueError."""
        # Setup mocks
        mock_project = Mock()
        mock_connection = Mock()
        mock_catalog = Mock()
        mock_catalog.type = "UNSUPPORTED"

        mock_ensure_project.return_value = mock_project
        mock_project.connection.return_value = mock_connection
        mock_connection.catalog.return_value = mock_catalog
        mock_determine_path.return_value = "s3://bucket/table/path"

        df = pd.DataFrame({"col1": [1, 2]})

        with pytest.raises(
            ValueError,
            match="Unable to write to catalog. Catalog type 'UNSUPPORTED' not supported.",
        ):
            dataframeutils.to_catalog_table(df, database="test_db", table="test_table")


class TestPandasPatching:
    """Test cases for pandas monkey-patching functionality."""

    def test_pandas_read_catalog_table_patched(self):
        """Test that pandas.read_catalog_table is properly patched."""
        import pandas as pd

        assert hasattr(pd, "read_catalog_table")
        assert pd.read_catalog_table == dataframeutils.read_catalog_table

    def test_dataframe_to_catalog_table_patched(self):
        """Test that DataFrame.to_catalog_table is properly patched."""
        import pandas as pd

        df = pd.DataFrame({"col1": [1, 2]})
        assert hasattr(df, "to_catalog_table")
        # Check that the method exists and is callable
        assert callable(df.to_catalog_table)


if __name__ == "__main__":
    pytest.main([__file__])
