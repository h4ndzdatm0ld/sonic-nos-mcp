"""Unit tests for list_tool."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from sonic_nos_mcp.modules.tech_support.tools.list_tool import list_tech_support_files
from sonic_nos_mcp.modules.tech_support.models.file_listing_models import (
    ListTechSupportFilesRequest,
    ListTechSupportFilesResponse,
    FileInfo,
)


class TestListTechSupportFiles:
    """Test list_tech_support_files function."""

    @pytest.fixture
    def sample_directory(self):
        """Create a sample directory structure."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_list_tool_"))

        # Create files and directories
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.json").write_text('{"key": "value"}')
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "nested_file.log").write_text("log content")

        yield temp_dir

        # Cleanup
        import shutil

        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_list_tech_support_files_basic(self, sample_directory):
        """Test basic file listing."""
        request = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern=None)

        response = list_tech_support_files(request)

        assert isinstance(response, ListTechSupportFilesResponse)
        assert response.success is True
        assert response.error_message is None
        assert len(response.files) > 0

        # Verify file information structure
        file_paths = [f.path for f in response.files]
        assert "file1.txt" in file_paths
        assert "file2.json" in file_paths
        assert "subdir" in file_paths
        assert "subdir/nested_file.log" in file_paths

        # Verify FileInfo objects are properly constructed
        for file_info in response.files:
            assert isinstance(file_info, FileInfo)
            assert hasattr(file_info, "path")
            assert hasattr(file_info, "is_directory")

    def test_list_tech_support_files_with_pattern(self, sample_directory):
        """Test file listing with pattern filter."""
        request = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern="*.json")

        response = list_tech_support_files(request)

        assert response.success is True
        assert response.error_message is None

        file_paths = [f.path for f in response.files]
        assert "file2.json" in file_paths
        assert "file1.txt" not in file_paths

    def test_list_tech_support_files_with_recursive_pattern(self, sample_directory):
        """Test file listing with recursive pattern."""
        request = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern="**/*.log")

        response = list_tech_support_files(request)

        assert response.success is True
        file_paths = [f.path for f in response.files]
        assert "subdir/nested_file.log" in file_paths

    def test_list_tech_support_files_nonexistent_directory(self):
        """Test listing files in non-existent directory."""
        request = ListTechSupportFilesRequest(extract_dir="/nonexistent/directory", pattern=None)

        response = list_tech_support_files(request)

        assert response.success is False
        assert "Failed to list files" in response.error_message
        assert response.files == []

    @patch("sonic_nos_mcp.modules.tech_support.tools.list_tool.list_files")
    def test_list_tech_support_files_underlying_function_success(self, mock_list_files, sample_directory):
        """Test successful delegation to underlying list_files function."""
        # Mock the underlying list_files function
        mock_file_info1 = Mock()
        mock_file_info1.path = "test1.txt"
        mock_file_info1.is_directory = False

        mock_file_info2 = Mock()
        mock_file_info2.path = "testdir"
        mock_file_info2.is_directory = True

        mock_list_files.return_value = [mock_file_info1, mock_file_info2]

        request = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern="*.txt")

        response = list_tech_support_files(request)

        # Verify delegation
        mock_list_files.assert_called_once_with(str(sample_directory), "*.txt")

        # Verify response conversion
        assert response.success is True
        assert response.error_message is None
        assert len(response.files) == 2

        # Verify FileInfo objects are created correctly
        assert response.files[0].path == "test1.txt"
        assert response.files[0].is_directory is False
        assert response.files[1].path == "testdir"
        assert response.files[1].is_directory is True

    @patch("sonic_nos_mcp.modules.tech_support.tools.list_tool.list_files")
    def test_list_tech_support_files_underlying_function_failure(self, mock_list_files, sample_directory):
        """Test when underlying list_files function fails."""
        mock_list_files.side_effect = Exception("Underlying function failed")

        request = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern=None)

        response = list_tech_support_files(request)

        assert response.success is False
        assert "Failed to list files" in response.error_message
        assert response.files == []

    @patch("sonic_nos_mcp.modules.tech_support.tools.list_tool.list_files")
    def test_list_tech_support_files_with_permission_error(self, mock_list_files, sample_directory):
        """Test when list_files raises PermissionError."""
        mock_list_files.side_effect = PermissionError("Permission denied")

        request = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern=None)

        response = list_tech_support_files(request)

        assert response.success is False
        assert "Failed to list files" in response.error_message
        assert response.files == []

    def test_list_tech_support_files_empty_directory(self, sample_directory):
        """Test listing files in empty directory."""
        # Clear the directory
        import shutil

        for item in sample_directory.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        request = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern=None)

        response = list_tech_support_files(request)

        assert response.success is True
        assert response.error_message is None
        assert response.files == []

    def test_list_tech_support_files_with_various_patterns(self, sample_directory):
        """Test file listing with various pattern types."""
        # Test directory pattern
        request1 = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern="sub*")
        response1 = list_tech_support_files(request1)
        assert response1.success is True

        # Test file extension pattern
        request2 = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern="*.txt")
        response2 = list_tech_support_files(request2)
        assert response2.success is True

        # Test no matches pattern
        request3 = ListTechSupportFilesRequest(extract_dir=str(sample_directory), pattern="*.nonexistent")
        response3 = list_tech_support_files(request3)
        assert response3.success is True
        assert response3.files == []  # No matches should still succeed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
