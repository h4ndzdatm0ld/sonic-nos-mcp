"""Unit tests for inspect_tool."""

import pytest
from unittest.mock import Mock, patch

from sonic_nos_mcp.modules.tech_support.tools.inspect_tool import (
    read_tech_support_file_content,
)
from sonic_nos_mcp.modules.tech_support.models.text_chunking_models import (
    GetTechSupportFileContentRequest,
    GetTechSupportFileContentResponse,
    InspectTechSupportFileRequest,
    InspectTechSupportFileResponse,
)


class TestReadTechSupportFileContent:
    """Test read_tech_support_file_content function."""

    def test_read_tech_support_file_content_simple_chunking(self, sample_text_file):
        """Test simple file content chunking without pattern."""
        request = GetTechSupportFileContentRequest(
            file_path=str(sample_text_file), pattern=None, chunk_size="50", page=1  # String as per model
        )

        response = read_tech_support_file_content(request)

        assert isinstance(response, GetTechSupportFileContentResponse)
        assert response.success is True
        assert response.error_message is None
        assert response.page == 1
        assert response.total_pages >= 1
        assert response.file_path == str(sample_text_file)
        assert len(response.content) > 0
        assert response.matches == []

    def test_read_tech_support_file_content_with_pattern(self, sample_text_file):
        """Test file content with pattern matching."""
        request = GetTechSupportFileContentRequest(
            file_path=str(sample_text_file), pattern="ERROR", chunk_size="200", page=1  # String as per model
        )

        response = read_tech_support_file_content(request)

        assert response.success is True
        assert response.error_message is None
        assert response.page >= 1
        assert response.total_pages >= 1
        assert len(response.matches) > 0
        assert "ERROR" in response.matches[0]
        assert "ERROR" in response.content

    def test_read_tech_support_file_content_nonexistent_file(self):
        """Test with non-existent file."""
        request = GetTechSupportFileContentRequest(file_path="/nonexistent/file.txt", page=1)

        response = read_tech_support_file_content(request)

        assert response.success is False
        assert "Error reading file content" in response.content
        assert response.matches == []
        assert response.page == 1
        assert response.total_pages == 1
        assert "Failed to read file content" in response.error_message

    @patch("sonic_nos_mcp.modules.tech_support.tools.inspect_tool.FileProcessor")
    def test_read_tech_support_file_content_processor_exception(self, mock_processor_class, sample_text_file):
        """Test when FileProcessor raises exception during construction."""
        mock_processor_class.side_effect = Exception("FileProcessor construction failed")

        request = GetTechSupportFileContentRequest(file_path=str(sample_text_file), page=1)

        response = read_tech_support_file_content(request)

        assert response.success is False
        assert "Error reading file content" in response.content
        assert response.matches == []
        assert "Failed to read file content" in response.error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
