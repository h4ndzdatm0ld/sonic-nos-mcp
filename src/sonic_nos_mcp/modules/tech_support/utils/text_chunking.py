"""Utility functions for handling text file chunking and pattern matching."""

import os
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union

from sonic_nos_mcp.modules.tech_support.models.text_chunking_models import TextChunk

logger = logging.getLogger(__name__)


@dataclass
class FileProcessor:
    """Handles file operations including reading, chunking, and pattern matching.

    Simple dataclass-based file processor with environment variable controlled chunk sizing.
    """

    file_path: Union[str, Path]
    chunk_size: Optional[int] = None

    def __post_init__(self):
        """Initialize after dataclass creation."""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        if self.chunk_size is None:
            self.chunk_size = self._get_default_chunk_size()
        self.content: Optional[str] = None  # Lazy-loaded content
        logger.debug(f"Initialized FileProcessor for {self.file_path} with chunk size {self.chunk_size}")

    def _get_default_chunk_size(self) -> int:
        """Get default chunk size from environment variable or use default.

        Returns:
            int: The default chunk size in characters
        """
        env_var = "MCP_SONIC_TECH_SUPPORT_CHUNK_SIZE"
        default_size = 10000

        try:
            chunk_size = int(os.environ.get(env_var, str(default_size)))
            logger.debug(f"Using chunk size from environment: {chunk_size}")
            return chunk_size
        except ValueError as e:
            logger.warning(f"Invalid chunk size in environment variable {env_var}: {e}. Using default: {default_size}")
            return default_size

    def read(self) -> str:
        """Read the entire file content.

        Returns:
            str: The entire file content as a string

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there is an error reading the file
            ValueError: If the file is compressed (indicates extraction bug)
        """
        if self.content is None:
            logger.info(f"Reading file: {self.file_path}")

            if not self.file_path.exists():
                logger.error(f"File not found: {self.file_path}")
                raise FileNotFoundError(f"File not found: {self.file_path}")

            if str(self.file_path).lower().endswith((".gz", ".bz2", ".xz")):
                logger.error(f"Compressed file detected - extraction incomplete: {self.file_path}")
                raise ValueError(
                    f"Compressed file detected: {self.file_path}. This indicates incomplete extraction - all files should be decompressed during extraction."
                )

            try:
                logger.debug(f"Opening file with standard open: {self.file_path}")
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.content = f.read()
                logger.debug(f"Successfully read {len(self.content)} characters from {self.file_path}")
            except Exception as e:
                logger.exception(f"Error reading file {self.file_path}: {str(e)}")
                raise IOError(f"Error reading file {self.file_path}: {str(e)}")

        return self.content

    def get_chunk(self, page: int = 1) -> TextChunk:
        """Get a specific chunk of content.

        Args:
            page: Page number to retrieve (1-based)

        Returns:
            TextChunk: The requested chunk of text

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there is an error reading the file
        """
        logger.info(f"Getting chunk from file: {self.file_path}, page: {page}")

        try:
            logger.debug("Getting file content")
            content = self.read()

            logger.debug("Calculating total pages")
            total_pages = max(1, (len(content) + self.chunk_size - 1) // self.chunk_size)
            logger.debug(f"Total content size: {len(content)}, total pages: {total_pages}")

            logger.debug("Validating page number")
            if page < 1:
                logger.warning(f"Invalid page number {page}, using page 1")
                page = 1
            elif page > total_pages:
                logger.warning(f"Page number {page} exceeds total pages {total_pages}, using last page")
                page = total_pages

            logger.debug("Extracting the chunk")
            start_pos = (page - 1) * self.chunk_size
            end_pos = min(start_pos + self.chunk_size, len(content))
            chunk_content = content[start_pos:end_pos]
            logger.debug(f"Extracted chunk from positions {start_pos} to {end_pos}, length: {len(chunk_content)}")

            logger.debug("Adding continuation marker if needed")
            if page > 1:
                logger.debug("Adding continuation note for non-first page")
                chunk_content = f"[...continued from previous page...]\n\n{chunk_content}"

            return TextChunk(
                content=chunk_content,
                page=page,
                total_pages=total_pages,
                file_path=str(self.file_path),
            )

        except Exception as e:
            logger.exception(f"Error getting chunk from file: {str(e)}")
            raise

    def find_matches(self, pattern: str, page: int = 1, context_lines: int = 2) -> Tuple[str, List[str], int, int]:
        """Find pattern matches in the entire file with context lines.

        This performs pattern matching on the entire file content first,
        then chunks the results for pagination.

        Args:
            pattern: Regex pattern to match
            page: Page number for results (1-based)
            context_lines: Number of lines to include before and after each match

        Returns:
            Tuple containing:
            - Formatted content with matches and context
            - List of raw regex matches
            - Current page number
            - Total number of pages
        """
        logger.info(f"Finding matches in file: {self.file_path}, pattern: {pattern}, page: {page}")

        try:
            content = self.read()
            regex, all_matches = self._compile_pattern_and_find_matches(content, pattern)

            if not all_matches:
                logger.info(f"No matches found for pattern: {pattern}")
                return (f"No matches found for pattern: {pattern}", [], 1, 1)

            match_sections = self._extract_matches_with_context(content.splitlines(), regex, context_lines)

            if not match_sections:
                logger.info(f"No match sections created for pattern: {pattern}")
                return (f"No matches found for pattern: {pattern}", [], 1, 1)

            match_chunks = self._chunk_match_sections(match_sections)
            final_content = self._format_match_results(match_chunks, pattern, page, all_matches)

            total_pages = len(match_chunks) or 1
            page = self._validate_page_number(page, total_pages)

            logger.info(f"Returning matched content for page {page} of {total_pages}")
            return (final_content, all_matches, page, total_pages)

        except re.error as e:
            logger.error(f"Invalid regex pattern: {str(e)}")
            return (f"Error: Invalid regex pattern: {str(e)}", [], 1, 1)
        except Exception as e:
            logger.exception(f"Error processing file with pattern: {str(e)}")
            return (f"Error processing file with pattern: {str(e)}", [], 1, 1)

    def _compile_pattern_and_find_matches(self, content: str, pattern: str) -> Tuple[re.Pattern, List[str]]:
        """Compile regex pattern and find all matches in content."""
        logger.debug(f"Compiling regex pattern: {pattern}")
        regex = re.compile(pattern)
        all_matches = regex.findall(content)
        logger.info(f"Found {len(all_matches)} total matches for pattern: {pattern}")
        return regex, all_matches

    def _extract_matches_with_context(self, lines: List[str], regex: re.Pattern, context_lines: int) -> List[str]:
        """Extract matching lines with context around each match."""
        logger.debug("Extracting matches with context lines")
        included_lines: set[int] = set()
        match_sections = []

        for i, line in enumerate(lines):
            if regex.search(line):
                logger.debug(f"Found match at line {i+1}")
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)

                if any(idx in included_lines for idx in range(start, end)):
                    logger.debug(f"Skipping overlapping match at line {i}")
                    continue

                section_lines = lines[start:end]
                section_text = "\n".join(section_lines)
                section_with_header = f"Lines {start+1}-{end}:\n{section_text}"

                match_sections.append(section_with_header)
                included_lines.update(range(start, end))

        logger.debug(f"Created {len(match_sections)} match sections with context")
        return match_sections

    def _chunk_match_sections(self, match_sections: List[str]) -> List[str]:
        """Chunk match sections for pagination based on chunk size."""
        logger.debug("Chunking match sections for pagination")
        match_chunks = []
        current_chunk = ""
        separator = "\n\n" + "-" * 40 + "\n\n"

        for section in match_sections:
            section_with_sep = separator + section if current_chunk else section
            if len(current_chunk) + len(section_with_sep) > self.chunk_size and current_chunk:
                logger.debug("Starting new chunk as current would exceed chunk size")
                match_chunks.append(current_chunk)
                current_chunk = section
            else:
                current_chunk += section_with_sep

        if current_chunk:
            logger.debug("Adding final chunk")
            match_chunks.append(current_chunk)

        logger.debug(f"Created {len(match_chunks)} pages of match chunks")
        return match_chunks

    def _format_match_results(self, match_chunks: List[str], pattern: str, page: int, all_matches: List[str]) -> str:
        """Format final match results with headers and pagination info."""
        if not match_chunks:
            return f"No matches found for pattern: {pattern}"

        total_pages = len(match_chunks)
        chunk_content = match_chunks[page - 1]
        header = f"Matches for pattern '{pattern}' - Page {page} of {total_pages}"
        if page > 1:
            header += " (continued)"

        summary = f"Found {len(all_matches)} total matches in {total_pages} pages."
        return f"{summary}\n\n{header}\n\n{chunk_content}"

    def _validate_page_number(self, page: int, total_pages: int) -> int:
        """Validate and correct page number if needed."""
        if page < 1:
            logger.warning(f"Invalid page {page}, using page 1")
            return 1
        elif page > total_pages:
            logger.warning(f"Page {page} exceeds total pages {total_pages}, using last page")
            return total_pages
        return page


def get_default_chunk_size() -> int:
    """Get the default chunk size from environment variable or use default."""
    env_var = "MCP_SONIC_TECH_SUPPORT_CHUNK_SIZE"
    default_size = 10000
    try:
        return int(os.environ.get(env_var, str(default_size)))
    except ValueError:
        return default_size


def chunk_file(file_path: Union[str, Path], chunk_size: Optional[int] = None, page: int = 1) -> TextChunk:
    """Read a file and return a specific chunk.

    Args:
        file_path: Path to the file to read
        chunk_size: Size of each chunk in characters. If None, use the default.
        page: Page number to retrieve (1-based)

    Returns:
        TextChunk: The requested chunk of text

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    processor = FileProcessor(file_path, chunk_size)
    return processor.get_chunk(page)


def chunk_file_smart(file_path: Union[str, Path], chunk_size: Optional[int] = None, page: int = 1) -> TextChunk:
    """Read a file and return a specific chunk.

    This function is maintained for backwards compatibility and now just calls chunk_file.

    Args:
        file_path: Path to the file to read
        chunk_size: Size of each chunk in characters. If None, use the default.
        page: Page number to retrieve (1-based)

    Returns:
        TextChunk: The requested chunk of text
    """
    return chunk_file(file_path, chunk_size, page)


def get_file_content_with_pattern(
    file_path: Union[str, Path],
    pattern: Optional[str] = None,
    chunk_size: Optional[int] = None,
    page: int = 1,
) -> Tuple[str, List[str], int, int]:
    """Read a file and extract content matching a regex pattern.

    If pattern is provided, regex is applied to the entire file content before chunking.
    If no pattern is provided, returns the file content chunked into pages.

    Args:
        file_path: Path to the file to read
        pattern: Optional regex pattern to extract specific content
        chunk_size: Size of each chunk in characters. If None, use the default.
        page: Page number to retrieve (1-based)

    Returns:
        Tuple[str, List[str], int, int]: The file content, a list of regex matches, page number, and total pages
    """
    processor = FileProcessor(file_path, chunk_size)

    if pattern:
        return processor.find_matches(pattern, page)
    else:
        chunk = processor.get_chunk(page)
        return chunk.content, [], chunk.page, chunk.total_pages


def get_pattern_matches_first(
    file_path: Union[str, Path], pattern: str, chunk_size: Optional[int] = None, page: int = 1, context_lines: int = 2
) -> Tuple[str, List[str], int, int]:
    """Read a file, apply pattern matching first, then chunk the results.

    This is a legacy function maintained for backward compatibility.
    New code should use get_file_content_with_pattern instead.

    Args:
        file_path: Path to the file to read
        pattern: Regex pattern to match
        chunk_size: Size of each chunk in characters. If None, use the default.
        page: Page number to retrieve (1-based)
        context_lines: Number of context lines to include around each match

    Returns:
        Tuple[str, List[str], int, int]: The chunked match content, list of regex matches,
                                         page number, and total pages
    """
    processor = FileProcessor(file_path, chunk_size)
    return processor.find_matches(pattern, page, context_lines)
