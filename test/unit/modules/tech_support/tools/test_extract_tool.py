"""Unit tests for extract_tool."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from sonic_nos_mcp.modules.tech_support.tools.extract_tool import (
    extract_tech_support,
    _safe_abspath,
    _validate_inputs,
)
from sonic_nos_mcp.modules.tech_support.models.extraction_models import (
    ExtractTechSupportRequest,
    ExtractTechSupportResponse,
)


class TestSafeAbspath:
    """Test _safe_abspath utility function."""

    def test_safe_abspath_regular_path(self):
        """Test _safe_abspath with regular path."""
        result = _safe_abspath("test.txt")
        assert isinstance(result, str)
        assert Path(result).is_absolute()

    def test_safe_abspath_with_tilde(self):
        """Test _safe_abspath with home directory expansion."""
        result = _safe_abspath("~/test.txt")
        assert isinstance(result, str)
        assert "~" not in result  # Should be expanded
        assert Path(result).is_absolute()

    def test_safe_abspath_already_absolute(self):
        """Test _safe_abspath with already absolute path."""
        abs_path = "/absolute/path/test.txt"
        result = _safe_abspath(abs_path)
        assert result == str(Path(abs_path).resolve())


class TestValidateInputs:
    """Test _validate_inputs function."""

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

    def test_validate_inputs_valid_file(self, temp_file):
        """Test validation with valid file."""
        request = ExtractTechSupportRequest(file_path=str(temp_file))

        # Should not raise exception
        _validate_inputs(request)

    def test_validate_inputs_nonexistent_file(self):
        """Test validation with non-existent file."""
        request = ExtractTechSupportRequest(file_path="/nonexistent/file.txt")

        with pytest.raises(ValueError, match="does not exist"):
            _validate_inputs(request)

    def test_validate_inputs_directory_instead_of_file(self, temp_dir):
        """Test validation with directory instead of file."""
        request = ExtractTechSupportRequest(file_path=str(temp_dir))

        with pytest.raises(ValueError, match="Expected a file"):
            _validate_inputs(request)

    def test_validate_inputs_valid_temp_dir(self, temp_file, temp_dir):
        """Test validation with valid temp_dir."""
        request = ExtractTechSupportRequest(file_path=str(temp_file), temp_dir=str(temp_dir))

        # Should not raise exception
        _validate_inputs(request)

    def test_validate_inputs_temp_dir_is_file(self, temp_file):
        """Test validation when temp_dir points to a file."""
        # Create another file to use as invalid temp_dir
        temp_file2 = Path(tempfile.mktemp(suffix=".txt"))
        temp_file2.write_text("content")

        try:
            request = ExtractTechSupportRequest(file_path=str(temp_file), temp_dir=str(temp_file2))

            with pytest.raises(ValueError, match="exists but is not a directory"):
                _validate_inputs(request)
        finally:
            if temp_file2.exists():
                temp_file2.unlink()


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
        """Test extract_tech_support with invalid input."""
        request = ExtractTechSupportRequest(file_path="/nonexistent/file.txt")

        response = extract_tech_support(request)

        assert isinstance(response, ExtractTechSupportResponse)
        assert response.success is False
        assert "does not exist" in response.error_message
        assert response.extract_dir == ""
        assert response.files == []

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

                # Should pass temp_dir to extract_file (default remove_archives from request)
                call_args = mock_extract.call_args
                assert call_args[0][0] == str(temp_file)
                assert call_args[0][1] == str(temp_dir)
                # remove_archives comes from request (default False)
        finally:
            import shutil

            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def test_extract_tech_support_with_remove_archives(self, temp_file):
        """Test extract_tech_support with remove_archives=True."""
        request = ExtractTechSupportRequest(file_path=str(temp_file), remove_archives=True)

        with patch("sonic_nos_mcp.modules.tech_support.tools.extract_tool.extract_file") as mock_extract:
            mock_result = Mock()
            mock_result.success = True
            mock_result.error_message = None
            mock_result.extract_dir = "/tmp/extract"
            mock_extract.return_value = mock_result

            extract_tech_support(request)

            # Should pass remove_archives=True to extract_file
            mock_extract.assert_called_once_with(str(temp_file), None, remove_archives=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
