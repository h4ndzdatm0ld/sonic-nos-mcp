"""Unit tests for inspect_tool."""

import pytest
from unittest.mock import Mock, patch

from sonic_nos_mcp.modules.tech_support.tools.inspect_tool import (
    get_tech_support_file_content,
    inspect_tech_support_file,
)
from sonic_nos_mcp.modules.tech_support.models.text_chunking_models import (
    GetTechSupportFileContentRequest,
    GetTechSupportFileContentResponse,
    InspectTechSupportFileRequest,
    InspectTechSupportFileResponse,
)


class TestGetTechSupportFileContent:
    """Test get_tech_support_file_content function."""

    def test_get_tech_support_file_content_simple_chunking(self, sample_text_file):
        """Test simple file content chunking without pattern."""
        request = GetTechSupportFileContentRequest(
            file_path=str(sample_text_file), pattern=None, chunk_size="50", page=1  # String as per model
        )

        response = get_tech_support_file_content(request)

        assert isinstance(response, GetTechSupportFileContentResponse)
        assert response.success is True
        assert response.error_message is None
        assert response.page == 1
        assert response.total_pages >= 1
        assert response.file_path == str(sample_text_file)
        assert len(response.content) > 0
        assert response.matches == []

    def test_get_tech_support_file_content_with_pattern(self, sample_text_file):
        """Test file content with pattern matching."""
        request = GetTechSupportFileContentRequest(
            file_path=str(sample_text_file), pattern="ERROR", chunk_size="200", page=1  # String as per model
        )

        response = get_tech_support_file_content(request)

        assert response.success is True
        assert response.error_message is None
        assert response.page >= 1
        assert response.total_pages >= 1
        assert len(response.matches) > 0
        assert "ERROR" in response.matches[0]
        assert "ERROR" in response.content

    def test_get_tech_support_file_content_nonexistent_file(self):
        """Test with non-existent file."""
        request = GetTechSupportFileContentRequest(file_path="/nonexistent/file.txt", page=1)

        response = get_tech_support_file_content(request)

        assert response.success is False
        assert "Error getting file content" in response.content
        assert response.matches == []
        assert response.page == 1
        assert response.total_pages == 1
        assert "Failed to get file content" in response.error_message

    @patch("sonic_nos_mcp.modules.tech_support.tools.inspect_tool.FileProcessor")
    def test_get_tech_support_file_content_processor_exception(self, mock_processor_class, sample_text_file):
        """Test when FileProcessor raises exception during construction."""
        mock_processor_class.side_effect = Exception("FileProcessor construction failed")

        request = GetTechSupportFileContentRequest(file_path=str(sample_text_file), page=1)

        response = get_tech_support_file_content(request)

        assert response.success is False
        assert "Error getting file content: FileProcessor construction failed" in response.content
        assert response.matches == []
        assert "Failed to get file content" in response.error_message


class TestInspectTechSupportFile:
    """Test inspect_tech_support_file legacy function."""

    def test_inspect_tech_support_file_basic(self, sample_text_file):
        """Test basic inspect functionality."""
        request = InspectTechSupportFileRequest(file_path=str(sample_text_file), chunk_size=100, page=1)

        response = inspect_tech_support_file(request)

        assert isinstance(response, InspectTechSupportFileResponse)
        assert response.success is True
        assert response.error_message is None
        assert response.page == 1
        assert response.total_pages >= 1
        assert response.file_path == str(sample_text_file)
        assert len(response.content) > 0

    @patch("sonic_nos_mcp.modules.tech_support.tools.inspect_tool.get_tech_support_file_content")
    def test_inspect_tech_support_file_delegates_to_unified(self, mock_unified_function, sample_text_file):
        """Test that inspect function delegates to unified function."""
        mock_unified_response = Mock()
        mock_unified_response.content = "Unified content"
        mock_unified_response.page = 2
        mock_unified_response.total_pages = 3
        mock_unified_response.file_path = str(sample_text_file)
        mock_unified_response.success = True
        mock_unified_response.error_message = None
        mock_unified_function.return_value = mock_unified_response

        request = InspectTechSupportFileRequest(file_path=str(sample_text_file), chunk_size=50, page=2)

        response = inspect_tech_support_file(request)

        # Verify delegation occurred
        mock_unified_function.assert_called_once()
        call_args = mock_unified_function.call_args[0][0]
        assert call_args.file_path == str(sample_text_file)
        assert call_args.pattern is None
        assert call_args.chunk_size == "50"  # Should be string after conversion
        assert call_args.page == 2

        # Verify response conversion
        assert response.content == "Unified content"
        assert response.page == 2
        assert response.total_pages == 3
        assert response.file_path == str(sample_text_file)
        assert response.success is True
        assert response.error_message is None


class TestInspectToolIntegration:
    """Test integration between inspect tool functions."""

    def test_inspect_vs_get_content_consistency(self, sample_text_file):
        """Test consistency between inspect and get_content functions."""
        # Use inspect function (legacy)
        inspect_request = InspectTechSupportFileRequest(file_path=str(sample_text_file), chunk_size=100, page=1)
        inspect_response = inspect_tech_support_file(inspect_request)

        # Use get_content function (unified)
        get_request = GetTechSupportFileContentRequest(
            file_path=str(sample_text_file), pattern=None, chunk_size="100", page=1  # String as per model
        )
        get_response = get_tech_support_file_content(get_request)

        # Should return essentially the same content
        assert inspect_response.success == get_response.success
        assert inspect_response.page == get_response.page
        assert inspect_response.total_pages == get_response.total_pages
        assert inspect_response.file_path == get_response.file_path
        assert len(inspect_response.content) > 0
        assert len(get_response.content) > 0

    def test_error_handling_consistency(self):
        """Test error handling consistency between functions."""
        nonexistent_file = "/nonexistent/file.txt"

        # Test inspect function error handling
        inspect_request = InspectTechSupportFileRequest(file_path=nonexistent_file)
        inspect_response = inspect_tech_support_file(inspect_request)

        # Test get_content function error handling
        get_request = GetTechSupportFileContentRequest(file_path=nonexistent_file)
        get_response = get_tech_support_file_content(get_request)

        # Both should handle errors gracefully
        assert inspect_response.success is False
        assert get_response.success is False
        assert inspect_response.error_message is not None
        assert get_response.error_message is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
