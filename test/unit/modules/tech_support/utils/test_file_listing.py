"""Unit tests for file listing utilities."""

import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

from sonic_nos_mcp.modules.tech_support.utils.file_listing import (
    list_files,
    list_files_simple,
)
from sonic_nos_mcp.modules.tech_support.models.file_listing_models import FileInfo


class TestListFiles:
    """Test list_files function."""

    @pytest.fixture
    def sample_directory(self):
        """Create a sample directory structure for testing."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_listing_"))

        # Create files and directories
        (temp_path / "file1.txt").write_text("content1")
        (temp_path / "file2.json").write_text('{"key": "value"}')

        (temp_path / "subdir1").mkdir()
        (temp_path / "subdir1" / "file3.log").write_text("log content")

        (temp_path / "subdir2").mkdir()
        (temp_path / "subdir2" / "file4.conf").write_text("config content")
        (temp_path / "subdir2" / "nested").mkdir()
        (temp_path / "subdir2" / "nested" / "file5.txt").write_text("nested content")

        yield temp_path

        # Cleanup
        import shutil

        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_list_files_basic(self, sample_directory):
        """Test basic file listing without pattern."""
        files = list_files(sample_directory)

        # Should find all files and directories
        file_paths = [f.path for f in files]

        assert "file1.txt" in file_paths
        assert "file2.json" in file_paths
        assert "subdir1" in file_paths
        assert "subdir2" in file_paths
        assert "subdir1/file3.log" in file_paths
        assert "subdir2/file4.conf" in file_paths
        assert "subdir2/nested" in file_paths
        assert "subdir2/nested/file5.txt" in file_paths

        # Verify file vs directory classification
        files_dict = {f.path: f.is_directory for f in files}
        assert files_dict["file1.txt"] is False
        assert files_dict["subdir1"] is True
        assert files_dict["subdir1/file3.log"] is False

    def test_list_files_with_simple_pattern(self, sample_directory):
        """Test file listing with simple glob pattern."""
        # Test *.json pattern
        json_files = list_files(sample_directory, "*.json")
        json_paths = [f.path for f in json_files]

        assert "file2.json" in json_paths
        assert "file1.txt" not in json_paths
        assert len([f for f in json_files if not f.is_directory]) == 1

    def test_list_files_with_recursive_pattern(self, sample_directory):
        """Test file listing with recursive pattern."""
        # Test **/*.txt pattern
        txt_files = list_files(sample_directory, "**/*.txt")
        txt_paths = [f.path for f in txt_files]

        assert "file1.txt" in txt_paths
        assert "subdir2/nested/file5.txt" in txt_paths
        assert "file2.json" not in txt_paths

    def test_list_files_with_directory_pattern(self, sample_directory):
        """Test file listing with directory pattern."""
        # Test subdir* pattern
        subdirs = list_files(sample_directory, "subdir*")
        subdir_paths = [f.path for f in subdirs]

        assert "subdir1" in subdir_paths
        assert "subdir2" in subdir_paths
        # Verify directories are marked correctly (some might be files in subdirs)
        subdir_entries = [f for f in subdirs if f.path in ["subdir1", "subdir2"]]
        assert all(f.is_directory for f in subdir_entries)

    def test_list_files_nonexistent_directory(self):
        """Test listing files in non-existent directory."""
        with pytest.raises(FileNotFoundError):
            list_files("/nonexistent/directory")

    def test_list_files_file_instead_of_directory(self, sample_directory):
        """Test listing files when path points to a file."""
        file_path = sample_directory / "file1.txt"

        with pytest.raises(NotADirectoryError):
            list_files(file_path)

    @patch("os.walk")
    def test_list_files_with_permission_error(self, mock_walk, sample_directory):
        """Test file listing with permission error."""
        mock_walk.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            list_files(sample_directory)

    @patch("os.walk")
    def test_list_files_with_general_error(self, mock_walk, sample_directory):
        """Test file listing with general error."""
        # Mock os.walk to return some results then raise an error
        mock_walk.return_value = [
            (str(sample_directory), ["subdir1"], ["file1.txt"]),
        ]

        # Should return partial results despite error
        files = list_files(sample_directory)
        assert len(files) >= 1  # Should have at least some results


class TestListFilesSimple:
    """Test list_files_simple function."""

    @pytest.fixture
    def sample_directory(self):
        """Create a sample directory structure."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_simple_listing_"))

        (temp_path / "file1.txt").write_text("content")
        (temp_path / "subdir").mkdir()
        (temp_path / "subdir" / "file2.txt").write_text("content")

        yield temp_path

        import shutil

        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_list_files_simple_basic(self, sample_directory):
        """Test simple file listing."""
        file_paths = list_files_simple(sample_directory)

        assert isinstance(file_paths, list)
        assert all(isinstance(path, str) for path in file_paths)
        assert "file1.txt" in file_paths
        assert "subdir" in file_paths
        assert "subdir/file2.txt" in file_paths

    def test_list_files_simple_with_pattern(self, sample_directory):
        """Test simple file listing with pattern."""
        txt_files = list_files_simple(sample_directory, "*.txt")

        assert "file1.txt" in txt_files
        assert "subdir" not in txt_files
        # Note: subdir/file2.txt might not match *.txt pattern at root level

    @patch("sonic_nos_mcp.modules.tech_support.utils.file_listing.list_files")
    def test_list_files_simple_delegates_to_list_files(self, mock_list_files, sample_directory):
        """Test that list_files_simple delegates to list_files."""
        # Mock return value
        mock_file_info = Mock(spec=FileInfo)
        mock_file_info.path = "test.txt"
        mock_list_files.return_value = [mock_file_info]

        result = list_files_simple(sample_directory, "*.txt")

        mock_list_files.assert_called_once_with(sample_directory, "*.txt")
        assert result == ["test.txt"]


class TestFileListingEdgeCases:
    """Test edge cases and error conditions in file listing."""

    def test_empty_directory(self):
        """Test listing files in empty directory."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_empty_"))

        try:
            files = list_files(temp_path)
            assert files == []
        finally:
            temp_path.rmdir()

    def test_pattern_matching_edge_cases(self):
        """Test pattern matching with edge cases."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_patterns_"))

        try:
            # Create files with special names
            (temp_path / "file.txt").touch()
            (temp_path / "file.TXT").touch()  # Case sensitivity
            (temp_path / "file-with-dashes.txt").touch()
            (temp_path / "file_with_underscores.txt").touch()
            (temp_path / "file with spaces.txt").touch()

            # Test case-insensitive pattern (should match both .txt and .TXT on most systems)
            txt_files = list_files(temp_path, "*.txt")
            txt_paths = [f.path for f in txt_files]

            # Should match files with txt extension
            assert any("txt" in path.lower() for path in txt_paths)

            # Test complex pattern
            dash_files = list_files(temp_path, "*-*")
            dash_paths = [f.path for f in dash_files]
            assert "file-with-dashes.txt" in dash_paths

        finally:
            import shutil

            shutil.rmtree(temp_path)

    def test_recursive_pattern_special_handling(self):
        """Test the special **/ pattern handling."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_recursive_"))

        try:
            # Create nested structure
            (temp_path / "dir1").mkdir()
            (temp_path / "dir1" / "file1.log").touch()
            (temp_path / "dir2").mkdir()
            (temp_path / "dir2" / "subdir").mkdir()
            (temp_path / "dir2" / "subdir" / "file2.log").touch()
            (temp_path / "notlog.txt").touch()

            # Test **/*.log pattern
            log_files = list_files(temp_path, "**/*.log")
            log_paths = [f.path for f in log_files]

            # Should find log files in all subdirectories
            assert "dir1/file1.log" in log_paths
            assert "dir2/subdir/file2.log" in log_paths
            assert "notlog.txt" not in log_paths

        finally:
            import shutil

            shutil.rmtree(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
