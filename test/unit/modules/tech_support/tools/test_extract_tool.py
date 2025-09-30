"""Unit tests for extract_tool."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from pydantic import ValidationError

from sonic_nos_mcp.modules.tech_support.tools.extract_tool import (
    extract_tech_support,
)
from sonic_nos_mcp.modules.tech_support.models.extraction_models import (
    ExtractTechSupportRequest,
)


class TestExtractTechSupportRequestValidation:
    """Test Pydantic validation in ExtractTechSupportRequest model."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        temp_file = Path(tempfile.mktemp(suffix=".txt"))
        temp_file.write_text("test content")

        yield temp_file

        if temp_file.exists():
            temp_file.unlink()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_validate_"))

        yield temp_dir

        import shutil

        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_valid_file_path_validation(self, temp_file):
        """Test validation with valid file path."""
        request = ExtractTechSupportRequest(file_path=str(temp_file))

        # Should create request successfully and normalize path
        assert request.file_path == str(temp_file.resolve())

    def test_nonexistent_file_validation(self):
        """Test validation with non-existent file."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractTechSupportRequest(file_path="/nonexistent/file.txt")

        error_str = str(exc_info.value)
        assert "does not exist" in error_str

    def test_directory_instead_of_file_validation(self, temp_dir):
        """Test validation with directory instead of file."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractTechSupportRequest(file_path=str(temp_dir))

        error_str = str(exc_info.value)
        assert "Expected a file" in error_str

    def test_valid_temp_dir_validation(self, temp_file, temp_dir):
        """Test validation with valid temp_dir."""
        request = ExtractTechSupportRequest(file_path=str(temp_file), temp_dir=str(temp_dir))

        # Should create request successfully and normalize path
        assert request.temp_dir == str(temp_dir.resolve())

    def test_temp_dir_is_file_validation(self, temp_file):
        """Test validation when temp_dir points to a file."""
        # Create another file to use as invalid temp_dir
        temp_file2 = Path(tempfile.mktemp(suffix=".txt"))
        temp_file2.write_text("content")

        try:
            with pytest.raises(ValidationError) as exc_info:
                ExtractTechSupportRequest(file_path=str(temp_file), temp_dir=str(temp_file2))

            error_str = str(exc_info.value)
            assert "exists but is not a directory" in error_str
        finally:
            if temp_file2.exists():
                temp_file2.unlink()

    def test_temp_dir_none_allowed(self, temp_file):
        """Test that temp_dir=None is allowed."""
        request = ExtractTechSupportRequest(file_path=str(temp_file), temp_dir=None)
        assert request.temp_dir is None

    def test_path_normalization(self, temp_file):
        """Test that paths are normalized to absolute paths."""
        # Test with relative path to existing file
        relative_path = Path(temp_file).name

        # Change to parent directory so relative path works
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_file.parent)
            request = ExtractTechSupportRequest(file_path=relative_path)

            # Path should be normalized to absolute
            assert Path(request.file_path).is_absolute()
            assert request.file_path == str(temp_file.resolve())
        finally:
            os.chdir(original_cwd)


class TestExtractTechSupport:
    """Test extract_tech_support function."""

    def setup_method(self):
        """Set up test method with extraction directory tracking."""
        self.extraction_dirs = []

    def teardown_method(self):
        """Clean up all extraction directories created during test."""
        import shutil

        for extract_dir in self.extraction_dirs:
            if Path(extract_dir).exists():
                try:
                    shutil.rmtree(extract_dir)
                except Exception as e:
                    print(f"Warning: Could not clean up {extract_dir}: {e}")
        self.extraction_dirs.clear()

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file."""
        temp_file = Path(tempfile.mktemp(suffix=".txt"))
        temp_file.write_text("test content")

        yield temp_file

        if temp_file.exists():
            temp_file.unlink()

    def test_extract_tech_support_invalid_input(self):
        """Test that invalid input is caught during model instantiation."""
        # With Pydantic validation, invalid input raises ValidationError during model creation
        with pytest.raises(ValidationError) as exc_info:
            ExtractTechSupportRequest(file_path="/nonexistent/file.txt")

        error_str = str(exc_info.value)
        assert "does not exist" in error_str

    @patch("sonic_nos_mcp.modules.tech_support.tools.extract_tool.extract_file")
    def test_extract_tech_support_extraction_failure(self, mock_extract_file, temp_file):
        """Test extract_tech_support when extract_file fails."""
        # Mock extract_file to return failure
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Extraction failed"
        mock_result.extract_dir = "/tmp/extract"
        mock_extract_file.return_value = mock_result

        request = ExtractTechSupportRequest(file_path=str(temp_file))
        response = extract_tech_support(request)

        assert response.success is False
        assert "Extraction failed" in response.error_message
        assert response.files == []

    @patch("sonic_nos_mcp.modules.tech_support.tools.extract_tool.extract_file")
    def test_extract_tech_support_extraction_exception(self, mock_extract_file, temp_file):
        """Test extract_tech_support when extract_file raises exception."""
        mock_extract_file.side_effect = Exception("Extraction exception")

        request = ExtractTechSupportRequest(file_path=str(temp_file))
        response = extract_tech_support(request)

        assert response.success is False
        assert "Extraction failed" in response.error_message
        assert response.files == []

    @patch("sonic_nos_mcp.modules.tech_support.tools.extract_tool.list_files_simple")
    @patch("sonic_nos_mcp.modules.tech_support.tools.extract_tool.extract_file")
    def test_extract_tech_support_success(self, mock_extract_file, mock_list_files, temp_file):
        """Test successful extract_tech_support."""
        # Mock successful extraction
        mock_result = Mock()
        mock_result.success = True
        mock_result.error_message = None
        mock_result.extract_dir = "/tmp/extract"
        mock_extract_file.return_value = mock_result

        # Mock file listing
        mock_list_files.return_value = ["file1.txt", "file2.json", "subdir/file3.log"]

        request = ExtractTechSupportRequest(file_path=str(temp_file))
        response = extract_tech_support(request)

        assert response.success is True
        assert response.error_message is None
        assert "/tmp/extract" in response.extract_dir or response.extract_dir.endswith("extract")
        assert response.files == ["file1.txt", "file2.json", "subdir/file3.log"]

    @patch("sonic_nos_mcp.modules.tech_support.tools.extract_tool.list_files_simple")
    @patch("sonic_nos_mcp.modules.tech_support.tools.extract_tool.extract_file")
    def test_extract_tech_support_list_files_error(self, mock_extract_file, mock_list_files, temp_file):
        """Test extract_tech_support when list_files_simple fails."""
        # Mock successful extraction
        mock_result = Mock()
        mock_result.success = True
        mock_result.error_message = None
        mock_result.extract_dir = "/tmp/extract"
        mock_extract_file.return_value = mock_result

        # Mock list_files_simple to fail
        mock_list_files.side_effect = Exception("List files failed")

        request = ExtractTechSupportRequest(file_path=str(temp_file))
        response = extract_tech_support(request)

        # Should still succeed but with empty file list
        assert response.success is True
        assert response.error_message is None
        assert "/tmp/extract" in response.extract_dir or response.extract_dir.endswith("extract")
        assert response.files == []  # Empty due to listing failure

    def test_extract_tech_support_with_temp_dir(self, temp_file):
        """Test extract_tech_support with custom temp_dir."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_custom_"))

        try:
            request = ExtractTechSupportRequest(file_path=str(temp_file), temp_dir=str(temp_dir))

            with patch("sonic_nos_mcp.modules.tech_support.tools.extract_tool.extract_file") as mock_extract:
                mock_result = Mock()
                mock_result.success = True
                mock_result.error_message = None
                mock_result.extract_dir = temp_dir
                mock_extract.return_value = mock_result

                extract_tech_support(request)

                # Should pass temp_dir to extract_file (automatic cleanup enabled)
                call_args = mock_extract.call_args
                # Compare normalized paths since Pydantic validators resolve symlinks
                assert call_args[0][0] == str(Path(temp_file).resolve())
                assert call_args[0][1] == str(Path(temp_dir).resolve())
        finally:
            import shutil

            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def test_extract_tech_support_with_simplified_api(self, temp_file):
        """Test extract_tech_support with simplified API (automatic cleanup)."""
        request = ExtractTechSupportRequest(file_path=str(temp_file))

        with patch("sonic_nos_mcp.modules.tech_support.tools.extract_tool.extract_file") as mock_extract:
            mock_result = Mock()
            mock_result.success = True
            mock_result.error_message = None
            mock_result.extract_dir = "/tmp/extract"
            mock_extract.return_value = mock_result

            extract_tech_support(request)

            # Should pass only file_path and temp_dir (automatic cleanup)
            # Compare normalized paths since Pydantic validators resolve symlinks
            expected_file_path = str(Path(temp_file).resolve())
            mock_extract.assert_called_once_with(expected_file_path, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
