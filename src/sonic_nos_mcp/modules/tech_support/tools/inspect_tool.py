"""Tool for inspecting files in a SONIC tech support directory."""

import logging

from sonic_nos_mcp.modules.tech_support.models.text_chunking_models import (
    GetTechSupportFileContentRequest,
    GetTechSupportFileContentResponse,
)
from sonic_nos_mcp.modules.tech_support.utils.text_chunking import FileProcessor

logger = logging.getLogger(__name__)


def read_tech_support_file_content(
    request: GetTechSupportFileContentRequest,
) -> GetTechSupportFileContentResponse:
    """Read content from tech support files with chunking and pattern matching.

    Simple environment variable controlled chunking with pattern matching support.
    Chunk size controlled by MCP_SONIC_TECH_SUPPORT_CHUNK_SIZE environment variable.

    When pattern is None: Returns simple chunks of the file
    When pattern is provided: Applies regex pattern matching with chunked results

    Args:
        request: The request containing file path, optional regex pattern, chunk size, and page

    Returns:
        GetTechSupportFileContentResponse: The response with file content
    """
    operation_type = "pattern matching" if request.pattern else "simple chunking"
    logger.info(f"Processing file content request ({operation_type}) for: {request.file_path}, page: {request.page}")

    try:
        chunk_size_int = int(request.chunk_size) if request.chunk_size else None
        logger.debug(f"Using chunk size: {chunk_size_int or 'default'}")

        processor = FileProcessor(request.file_path, chunk_size_int)
        logger.debug(f"Created FileProcessor for {request.file_path}")

        if request.pattern:
            logger.debug(f"Applying pattern matching with pattern: {request.pattern}")
            content, matches, page, total_pages = processor.find_matches(request.pattern, request.page)
            logger.info(
                f"Successfully got pattern-matched content: {request.file_path}, page {page} of {total_pages}, found {len(matches)} matches"
            )
        else:
            logger.debug(f"Performing simple chunking for page: {request.page}")
            chunk = processor.get_chunk(request.page)
            content = chunk.content
            matches = []
            page = chunk.page
            total_pages = chunk.total_pages
            logger.info(f"Successfully got chunked content: {request.file_path}, page {page} of {total_pages}")

        return GetTechSupportFileContentResponse(
            content=content,
            matches=matches,
            page=page,
            total_pages=total_pages,
            file_path=request.file_path,
            success=True,
            error_message=None,
        )
    except Exception as e:
        logger.exception(f"Failed to read file content ({operation_type}): {str(e)}")
        return GetTechSupportFileContentResponse(
            content=f"Error reading file content: {str(e)}",
            matches=[],
            page=1,
            total_pages=1,
            file_path=request.file_path,
            success=False,
            error_message=f"Failed to read file content: {str(e)}",
        )
