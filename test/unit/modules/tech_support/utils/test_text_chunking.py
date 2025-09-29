"""Unit tests for text chunking utilities."""

import gzip
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from sonic_nos_mcp.modules.tech_support.utils.text_chunking import (
    FileProcessor,
    chunk_file,
    chunk_file_smart,
    get_file_content_with_pattern,
    get_pattern_matches_first,
    get_default_chunk_size,
)
from sonic_nos_mcp.modules.tech_support.models.text_chunking_models import TextChunk


class TestGetDefaultChunkSize:
    """Test get_default_chunk_size function."""

    def test_default_chunk_size_no_env(self):
        """Test default chunk size when no environment variable set."""
        with patch.dict(os.environ, {}, clear=True):
            chunk_size = get_default_chunk_size()
            assert chunk_size == 10000  # Default value

    @patch.dict(os.environ, {"MCP_SONIC_TECH_SUPPORT_CHUNK_SIZE": "5000"})
    def test_default_chunk_size_from_env(self):
        """Test chunk size from environment variable."""
        chunk_size = get_default_chunk_size()
        assert chunk_size == 5000

    @patch.dict(os.environ, {"MCP_SONIC_TECH_SUPPORT_CHUNK_SIZE": "invalid"})
    def test_default_chunk_size_invalid_env(self):
        """Test default chunk size with invalid environment variable."""
        chunk_size = get_default_chunk_size()
        assert chunk_size == 10000  # Should fall back to default


class TestFileProcessor:
    """Test FileProcessor class."""

    @pytest.fixture
    def sample_text_file(self):
        """Create a sample text file."""
        temp_file = Path(tempfile.mktemp(suffix=".txt"))
        content = "Line 1\nLine 2 with ERROR\nLine 3\nLine 4 with WARNING\nLine 5"
        temp_file.write_text(content)

        yield temp_file

        if temp_file.exists():
            temp_file.unlink()

    def test_file_processor_init(self, sample_text_file):
        """Test FileProcessor initialization."""
        processor = FileProcessor(sample_text_file, chunk_size=100)

        assert processor.file_path == sample_text_file
        assert processor.chunk_size == 100
        assert processor.content is None  # Lazy loaded

    def test_file_processor_init_default_chunk_size(self, sample_text_file):
        """Test FileProcessor with default chunk size."""
        with patch.dict(os.environ, {"MCP_SONIC_TECH_SUPPORT_CHUNK_SIZE": "2000"}):
            processor = FileProcessor(sample_text_file)
            assert processor.chunk_size == 2000

    def test_file_processor_read(self, sample_text_file):
        """Test FileProcessor read method."""
        processor = FileProcessor(sample_text_file)

        content = processor.read()
        expected = "Line 1\nLine 2 with ERROR\nLine 3\nLine 4 with WARNING\nLine 5"
        assert content == expected

        # Test caching - second read should return cached content
        content2 = processor.read()
        assert content2 == content

    def test_file_processor_read_nonexistent_file(self):
        """Test FileProcessor read with non-existent file."""
        processor = FileProcessor("/nonexistent/file.txt")

        with pytest.raises(FileNotFoundError):
            processor.read()

    def test_file_processor_read_io_error(self, sample_text_file):
        """Test FileProcessor read with IO error by testing compressed file detection."""
        # Test the ValueError path when compressed file is detected
        temp_compressed = Path(tempfile.mktemp(suffix=".txt.gz"))
        temp_compressed.write_text("compressed content")

        try:
            processor = FileProcessor(temp_compressed)
            with pytest.raises(ValueError, match="Compressed file detected"):
                processor.read()
        finally:
            if temp_compressed.exists():
                temp_compressed.unlink()

    def test_file_processor_get_chunk(self, sample_text_file):
        """Test FileProcessor get_chunk method."""
        processor = FileProcessor(sample_text_file, chunk_size=20)

        # Get first chunk
        chunk1 = processor.get_chunk(page=1)

        assert isinstance(chunk1, TextChunk)
        assert chunk1.page == 1
        assert chunk1.total_pages >= 1
        assert chunk1.file_path == str(sample_text_file)
        assert len(chunk1.content) > 0

    def test_file_processor_get_chunk_invalid_page(self, sample_text_file):
        """Test FileProcessor get_chunk with invalid page numbers."""
        processor = FileProcessor(sample_text_file, chunk_size=20)

        # Test page 0 (should default to 1)
        chunk = processor.get_chunk(page=0)
        assert chunk.page == 1

        # Test page beyond total (should default to last page)
        chunk = processor.get_chunk(page=999)
        assert chunk.page == chunk.total_pages

    def test_file_processor_get_chunk_with_continuation(self, sample_text_file):
        """Test FileProcessor chunks have continuation markers."""
        processor = FileProcessor(sample_text_file, chunk_size=15)

        chunk1 = processor.get_chunk(page=1)
        chunk2 = processor.get_chunk(page=2)

        # Second chunk should have continuation marker
        if chunk1.total_pages > 1:
            assert "[...continued from previous page...]" in chunk2.content

    def test_file_processor_find_matches(self, sample_text_file):
        """Test FileProcessor find_matches method."""
        processor = FileProcessor(sample_text_file, chunk_size=100)

        content, matches, page, total_pages = processor.find_matches("ERROR", page=1)

        assert len(matches) > 0
        assert "ERROR" in matches[0]
        assert page >= 1
        assert total_pages >= 1
        assert "ERROR" in content

    def test_file_processor_find_matches_no_matches(self, sample_text_file):
        """Test FileProcessor find_matches with no matches."""
        processor = FileProcessor(sample_text_file)

        content, matches, page, total_pages = processor.find_matches("NONEXISTENT", page=1)

        assert len(matches) == 0
        assert page == 1
        assert total_pages == 1
        assert "No matches found" in content

    def test_file_processor_find_matches_invalid_regex(self, sample_text_file):
        """Test FileProcessor find_matches with invalid regex."""
        processor = FileProcessor(sample_text_file)

        content, matches, page, total_pages = processor.find_matches("[invalid", page=1)

        assert len(matches) == 0
        assert page == 1
        assert total_pages == 1
        assert "Invalid regex pattern" in content

    def test_file_processor_find_matches_with_context(self, sample_text_file):
        """Test FileProcessor find_matches with context lines."""
        processor = FileProcessor(sample_text_file, chunk_size=1000)

        content, matches, page, total_pages = processor.find_matches("ERROR", page=1, context_lines=1)

        assert len(matches) > 0
        # Should include context lines around matches
        assert "Line 1" in content or "Line 3" in content  # Context around ERROR line

    def test_compile_pattern_and_find_matches(self, sample_text_file):
        """Test _compile_pattern_and_find_matches method."""
        processor = FileProcessor(sample_text_file)
        content = processor.read()

        regex, matches = processor._compile_pattern_and_find_matches(content, "ERROR")

        assert isinstance(regex, re.Pattern)
        assert len(matches) == 1
        assert matches[0] == "ERROR"

    def test_compile_pattern_invalid_regex(self, sample_text_file):
        """Test _compile_pattern_and_find_matches with invalid regex."""
        processor = FileProcessor(sample_text_file)
        content = processor.read()

        with pytest.raises(re.error):
            processor._compile_pattern_and_find_matches(content, "[invalid")

    def test_extract_matches_with_context(self, sample_text_file):
        """Test _extract_matches_with_context method."""
        processor = FileProcessor(sample_text_file)
        content = processor.read()
        lines = content.splitlines()
        regex = re.compile("ERROR")

        match_sections = processor._extract_matches_with_context(lines, regex, context_lines=1)

        assert len(match_sections) == 1
        assert "ERROR" in match_sections[0]
        assert "Lines " in match_sections[0]  # Should have line number header

    def test_extract_matches_with_context_overlapping(self):
        """Test _extract_matches_with_context with overlapping matches."""
        temp_file = Path(tempfile.mktemp(suffix=".txt"))
        content = "ERROR line 1\nERROR line 2\nERROR line 3"
        temp_file.write_text(content)

        try:
            processor = FileProcessor(temp_file)
            lines = content.splitlines()
            regex = re.compile("ERROR")

            match_sections = processor._extract_matches_with_context(lines, regex, context_lines=2)

            # Should handle overlapping context by merging or skipping
            assert len(match_sections) >= 1

        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_chunk_match_sections(self, sample_text_file):
        """Test _chunk_match_sections method."""
        processor = FileProcessor(sample_text_file, chunk_size=50)
        match_sections = ["Section 1: " + "A" * 30, "Section 2: " + "B" * 30]

        match_chunks = processor._chunk_match_sections(match_sections)

        assert len(match_chunks) >= 1
        assert isinstance(match_chunks, list)
        assert all(isinstance(chunk, str) for chunk in match_chunks)

    def test_chunk_match_sections_empty(self, sample_text_file):
        """Test _chunk_match_sections with empty sections."""
        processor = FileProcessor(sample_text_file)
        match_sections = []

        match_chunks = processor._chunk_match_sections(match_sections)

        assert match_chunks == []

    def test_format_match_results(self, sample_text_file):
        """Test _format_match_results method."""
        processor = FileProcessor(sample_text_file)
        match_chunks = ["Chunk 1 content"]
        pattern = "ERROR"
        page = 1
        all_matches = ["ERROR"]

        result = processor._format_match_results(match_chunks, pattern, page, all_matches)

        assert isinstance(result, str)
        assert "Found 1 total matches" in result
        assert "Matches for pattern 'ERROR'" in result
        assert "Chunk 1 content" in result

    def test_format_match_results_empty_chunks(self, sample_text_file):
        """Test _format_match_results with empty chunks."""
        processor = FileProcessor(sample_text_file)
        match_chunks = []
        pattern = "MISSING"

        result = processor._format_match_results(match_chunks, pattern, 1, [])

        assert "No matches found for pattern: MISSING" in result

    def test_format_match_results_multiple_pages(self, sample_text_file):
        """Test _format_match_results with pagination."""
        processor = FileProcessor(sample_text_file)
        match_chunks = ["Chunk 1", "Chunk 2"]
        pattern = "ERROR"
        page = 2
        all_matches = ["ERROR", "ERROR"]

        result = processor._format_match_results(match_chunks, pattern, page, all_matches)

        assert "Found 2 total matches" in result
        assert "Page 2 of 2" in result
        assert "(continued)" in result
        assert "Chunk 2" in result

    def test_validate_page_number(self, sample_text_file):
        """Test _validate_page_number method."""
        processor = FileProcessor(sample_text_file)

        # Test valid page
        assert processor._validate_page_number(1, 5) == 1
        assert processor._validate_page_number(3, 5) == 3

        # Test invalid pages
        assert processor._validate_page_number(0, 5) == 1  # Below minimum
        assert processor._validate_page_number(-1, 5) == 1  # Negative
        assert processor._validate_page_number(10, 5) == 5  # Above maximum


class TestChunkFile:
    """Test chunk_file and related functions."""

    @pytest.fixture
    def sample_file(self):
        """Create sample file for chunking tests."""
        temp_file = Path(tempfile.mktemp(suffix=".txt"))
        content = "A" * 100 + "B" * 100 + "C" * 100  # 300 characters
        temp_file.write_text(content)

        yield temp_file

        if temp_file.exists():
            temp_file.unlink()

    def test_chunk_file_basic(self, sample_file):
        """Test basic file chunking."""
        chunk = chunk_file(sample_file, chunk_size=100, page=1)

        assert isinstance(chunk, TextChunk)
        assert chunk.page == 1
        assert chunk.total_pages == 3  # 300 chars / 100 chunk_size
        assert len(chunk.content) == 100
        assert chunk.content == "A" * 100

    def test_chunk_file_multiple_pages(self, sample_file):
        """Test chunking multiple pages."""
        chunk1 = chunk_file(sample_file, chunk_size=100, page=1)
        chunk2 = chunk_file(sample_file, chunk_size=100, page=2)
        chunk3 = chunk_file(sample_file, chunk_size=100, page=3)

        assert chunk1.content == "A" * 100
        assert "B" * 100 in chunk2.content  # Should contain B content + continuation marker
        assert "C" * 100 in chunk3.content  # Should contain C content + continuation marker

    def test_chunk_file_nonexistent(self):
        """Test chunking non-existent file."""
        with pytest.raises(FileNotFoundError):
            chunk_file("/nonexistent/file.txt")

    def test_chunk_file_smart_compatibility(self, sample_file):
        """Test chunk_file_smart backward compatibility."""
        chunk1 = chunk_file(sample_file, chunk_size=100, page=1)
        chunk2 = chunk_file_smart(sample_file, chunk_size=100, page=1)

        # Should return identical results
        assert chunk1.content == chunk2.content
        assert chunk1.page == chunk2.page
        assert chunk1.total_pages == chunk2.total_pages


class TestGetFileContentWithPattern:
    """Test get_file_content_with_pattern function."""

    @pytest.fixture
    def sample_log_file(self):
        """Create sample log file with patterns."""
        temp_file = Path(tempfile.mktemp(suffix=".log"))
        content = """2024-01-01 10:00:00 INFO Starting service
2024-01-01 10:01:00 ERROR Connection failed
2024-01-01 10:02:00 WARN Retrying connection
2024-01-01 10:03:00 INFO Service started successfully
2024-01-01 10:04:00 ERROR Another error occurred"""
        temp_file.write_text(content)

        yield temp_file

        if temp_file.exists():
            temp_file.unlink()

    def test_get_file_content_without_pattern(self, sample_log_file):
        """Test getting file content without pattern (simple chunking)."""
        content, matches, page, total_pages = get_file_content_with_pattern(
            sample_log_file, pattern=None, chunk_size=100, page=1
        )

        assert len(content) > 0
        assert matches == []  # No pattern means no matches
        assert page == 1
        assert total_pages >= 1
        assert "2024-01-01" in content

    def test_get_file_content_with_pattern(self, sample_log_file):
        """Test getting file content with regex pattern matching functionality."""
        content, matches, page, total_pages = get_file_content_with_pattern(
            sample_log_file, pattern=r"ERROR", chunk_size=500, page=1
        )

        assert len(matches) == 2, f"Should find 2 ERROR entries, got {len(matches)}"
        assert page >= 1
        assert total_pages >= 1
        assert "ERROR" in content

        # Verify matches contain the pattern (not the full message text)
        assert all("ERROR" == match for match in matches), f"All matches should be 'ERROR', got: {matches}"

    def test_get_file_content_with_complex_pattern(self, sample_log_file):
        """Test getting file content with complex regex."""
        content, matches, page, total_pages = get_file_content_with_pattern(
            sample_log_file, pattern=r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", page=1
        )

        assert len(matches) == 5  # Should find all 5 timestamps
        assert "2024-01-01 10:00:00" in matches

    def test_get_pattern_matches_first_compatibility(self, sample_log_file):
        """Test get_pattern_matches_first backward compatibility."""
        content1, matches1, page1, total_pages1 = get_file_content_with_pattern(
            sample_log_file, pattern="ERROR", page=1
        )
        content2, matches2, page2, total_pages2 = get_pattern_matches_first(
            sample_log_file, pattern="ERROR", page=1, context_lines=2
        )

        # Should return similar results (matches should be the same)
        assert matches1 == matches2
        assert page1 == page2
        assert total_pages1 == total_pages2


class TestFileProcessorErrorCases:
    """Test FileProcessor error handling."""

    def test_file_processor_with_invalid_chunk_size_env(self):
        """Test FileProcessor with invalid chunk size environment variable."""
        with patch.dict(os.environ, {"MCP_SONIC_TECH_SUPPORT_CHUNK_SIZE": "invalid"}):
            temp_file = Path(tempfile.mktemp(suffix=".txt"))
            temp_file.write_text("content")

            try:
                processor = FileProcessor(temp_file)
                # Should use default chunk size despite invalid env var
                assert processor.chunk_size == 10000
            finally:
                if temp_file.exists():
                    temp_file.unlink()

    def test_file_processor_find_matches_with_io_error(self):
        """Test find_matches with IO error."""
        processor = FileProcessor("/nonexistent/file.txt")

        # Should handle the error gracefully
        content, matches, page, total_pages = processor.find_matches("test", page=1)

        assert "Error processing file" in content
        assert matches == []
        assert page == 1
        assert total_pages == 1

    def test_file_processor_get_chunk_with_io_error(self):
        """Test get_chunk with IO error."""
        processor = FileProcessor("/nonexistent/file.txt")

        with pytest.raises(FileNotFoundError):
            processor.get_chunk(page=1)

    def test_file_processor_read_with_permission_error(self):
        """Test FileProcessor read method with permission error."""
        # Create a file and remove read permissions to simulate permission error
        temp_file = Path(tempfile.mktemp(suffix=".txt"))
        temp_file.write_text("test content")
        temp_file.chmod(0o000)  # Remove all permissions

        try:
            processor = FileProcessor(temp_file)
            with pytest.raises((IOError, PermissionError)):
                processor.read()
        finally:
            temp_file.chmod(0o644)  # Restore permissions for cleanup
            if temp_file.exists():
                temp_file.unlink()


class TestTextChunkingIntegration:
    """Test integration between text chunking functions."""

    @pytest.fixture
    def large_test_file(self):
        """Create a large test file for chunking."""
        temp_file = Path(tempfile.mktemp(suffix=".txt"))

        # Create content with repeated patterns
        lines = []
        for i in range(100):
            if i % 10 == 0:
                lines.append(f"Line {i}: ERROR - Something went wrong")
            elif i % 15 == 0:
                lines.append(f"Line {i}: WARN - Warning message")
            else:
                lines.append(f"Line {i}: INFO - Normal operation")

        content = "\n".join(lines)
        temp_file.write_text(content)

        yield temp_file

        if temp_file.exists():
            temp_file.unlink()

    def test_large_file_chunking_consistency(self, large_test_file):
        """Test consistent chunking across different methods."""
        chunk_size = 500

        # Test via FileProcessor
        processor = FileProcessor(large_test_file, chunk_size=chunk_size)
        chunk_via_processor = processor.get_chunk(page=1)

        # Test via convenience function
        chunk_via_function = chunk_file(large_test_file, chunk_size=chunk_size, page=1)

        # Should return identical results
        assert chunk_via_processor.content == chunk_via_function.content
        assert chunk_via_processor.page == chunk_via_function.page
        assert chunk_via_processor.total_pages == chunk_via_function.total_pages

    def test_pattern_matching_pagination(self, large_test_file):
        """Test pattern matching with pagination."""
        processor = FileProcessor(large_test_file, chunk_size=300)

        # Find ERROR patterns
        content1, matches1, page1, total_pages1 = processor.find_matches("ERROR", page=1)

        assert len(matches1) > 0
        assert page1 == 1

        # If there are multiple pages, test subsequent pages
        if total_pages1 > 1:
            content2, matches2, page2, total_pages2 = processor.find_matches("ERROR", page=2)

            assert page2 == 2
            assert total_pages2 == total_pages1  # Should be consistent
            # matches2 should be the same as matches1 (all matches found regardless of page)
            assert matches2 == matches1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
