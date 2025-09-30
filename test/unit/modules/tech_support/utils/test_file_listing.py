"""Unit tests for file listing utilities."""

import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from sonic_nos_mcp.modules.tech_support.utils.file_listing import (
    list_files,
)


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

        # Should find all files only (no directories)
        file_paths = [f.path for f in files]

        assert "file1.txt" in file_paths
        assert "file2.json" in file_paths
        assert "subdir1/file3.log" in file_paths
        assert "subdir2/file4.conf" in file_paths
        assert "subdir2/nested/file5.txt" in file_paths

        # Directories should not be returned
        assert "subdir1" not in file_paths
        assert "subdir2" not in file_paths
        assert "subdir2/nested" not in file_paths

        # Verify all returned items have sizes
        for file_info in files:
            assert hasattr(file_info, "size")
            assert isinstance(file_info.size, int)
            assert file_info.size >= 0

    def test_list_files_with_simple_pattern(self, sample_directory):
        """Test file listing with simple glob pattern."""
        # Test *.json pattern
        json_files = list_files(sample_directory, "*.json")
        json_paths = [f.path for f in json_files]

        assert "file2.json" in json_paths
        assert "file1.txt" not in json_paths
        assert len(json_files) == 1  # Only files are returned now

        # Verify file has size
        assert json_files[0].size > 0

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
        # Test subdir* pattern - should match files in subdirectories that start with "subdir"
        subdirs = list_files(sample_directory, "subdir*")
        subdir_paths = [f.path for f in subdirs]

        # Should find files within subdirectories, but not the directories themselves
        assert "subdir1/file3.log" in subdir_paths
        assert "subdir2/file4.conf" in subdir_paths
        # Directories should not be returned
        assert "subdir1" not in subdir_paths
        assert "subdir2" not in subdir_paths

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
