"""Tool for extracting SONiC tech-support files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from sonic_nos_mcp.modules.tech_support.models.extraction_models import (
    ExtractTechSupportRequest,
    ExtractTechSupportResponse,
)
from sonic_nos_mcp.modules.tech_support.models.file_listing_models import FileInfo
from sonic_nos_mcp.modules.tech_support.utils.extraction import extract_file
from sonic_nos_mcp.modules.tech_support.utils.file_listing import list_files

logger = logging.getLogger(__name__)


def extract_tech_support(
    request: ExtractTechSupportRequest,
) -> ExtractTechSupportResponse:
    """Extract a SONiC tech-support tarball (and nested archives) to a temp directory.

    This function:
      1. Uses pre-validated inputs from Pydantic model validators.
      2. Delegates archive processing to utils.extraction.extract_file(), which automatically:
         - Extract the top-level tarball (e.g., sonic_dump_<host>_<ts>.tar.gz).
         - Recursively inflate nested archives: *.gz, *.tar, *.tar.gz, *.tgz, *.zip.
         - Always remove source archives after extraction.
         - Remove empty files (0 bytes) to clean up useless files.
         - Clean up empty directories.
      3. Produces a file listing for downstream tools (LLM navigation, indexing).

    Args:
        request: Extraction request containing already-validated fields:
            - file_path: validated path to the tech-support tarball (normalized absolute path)
            - temp_dir: optional extraction root (validated if provided, created if missing)

    Returns:
        ExtractTechSupportResponse: with fields
            - extract_dir: absolute directory path where files now live
            - success: True/False
            - error_message: optional error string
            - files: recursive list (relative paths) of items under extract_dir

    Note:
        Input validation is handled automatically by Pydantic field validators in the
        ExtractTechSupportRequest model, which validates file existence and path normalization.
    """
    ctx: Dict[str, Any] = {
        "file_path": request.file_path,
        "temp_dir": request.temp_dir,
    }
    logger.info("extract_tech_support: starting extraction", extra={"context": ctx})

    try:
        result = extract_file(
            request.file_path,
            request.temp_dir,
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("extract_tech_support: extract_file() raised an exception", extra={"context": ctx})
        return ExtractTechSupportResponse(
            extract_dir="",
            success=False,
            error_message=f"Extraction failed: {e}",
            files=[],
        )

    extract_dir_str = str(Path(result.extract_dir).resolve()) if result.extract_dir else ""
    if not result.success:
        logger.error(
            "extract_tech_support: extraction reported failure",
            extra={"context": {**ctx, "extract_dir": extract_dir_str, "error": result.error_message}},
        )
        return ExtractTechSupportResponse(
            extract_dir=extract_dir_str,
            success=False,
            error_message=result.error_message or "Unknown extraction error",
            files=[],
        )

    files: List[FileInfo] = []
    try:
        files = list_files(extract_dir_str)
        logger.info(
            "extract_tech_support: extraction complete",
            extra={"context": {**ctx, "extract_dir": extract_dir_str, "file_count": len(files)}},
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(
            "extract_tech_support: list_files() failed: %s",
            e,
            extra={"context": {**ctx, "extract_dir": extract_dir_str}},
        )

    return ExtractTechSupportResponse(
        extract_dir=extract_dir_str,
        success=True,
        error_message=None,
        files=files,
    )
