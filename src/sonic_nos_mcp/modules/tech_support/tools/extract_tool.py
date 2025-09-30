"""Tool for extracting SONiC tech-support files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from sonic_nos_mcp.modules.tech_support.models.extraction_models import (
    ExtractTechSupportRequest,
    ExtractTechSupportResponse,
)
from sonic_nos_mcp.modules.tech_support.utils.extraction import extract_file
from sonic_nos_mcp.modules.tech_support.utils.file_listing import list_files_simple

logger = logging.getLogger(__name__)


def extract_tech_support(
    request: ExtractTechSupportRequest,
) -> ExtractTechSupportResponse:
    """Extract a SONiC tech-support tarball (and nested archives) to a temp directory.

    This function:
      1. Uses pre-validated inputs from Pydantic model validators.
      2. Delegates archive processing to utils.extraction.extract_file(), which MUST:
         - Extract the top-level tarball (e.g., sonic_dump_<host>_<ts>.tar.gz).
         - Recursively inflate nested archives: *.gz, *.tar, *.tar.gz, *.tgz, *.zip.
         - Optionally remove source archives after extraction if remove_archives=True.
      3. Produces a file listing for downstream tools (LLM navigation, indexing).

    Args:
        request: Extraction request containing already-validated fields:
            - file_path: validated path to the tech-support tarball (normalized absolute path)
            - temp_dir: optional extraction root (validated if provided, created if missing)
            - remove_archives: optionally delete archives after extraction

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
        "remove_archives": bool(request.remove_archives),
    }
    logger.info("extract_tech_support: starting extraction", extra={"context": ctx})

    try:
        result = extract_file(
            request.file_path,
            request.temp_dir,
            remove_archives=request.remove_archives,
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("extract_tech_support: extract_file() raised an exception", extra={"context": ctx})
        return ExtractTechSupportResponse(
            extract_dir="",
            success=False,
            error_message=f"Extraction failed: {e}",
            files=[],
        )

    # Build response
    extract_dir_str = str(Path(result.extract_dir).resolve()) if getattr(result, "extract_dir", None) else ""
    if not getattr(result, "success", False):
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

    files: List[str] = []
    try:
        files = list_files_simple(extract_dir_str)
        logger.info(
            "extract_tech_support: extraction complete",
            extra={"context": {**ctx, "extract_dir": extract_dir_str, "file_count": len(files)}},
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(
            "extract_tech_support: list_files_simple() failed: %s",
            e,
            extra={"context": {**ctx, "extract_dir": extract_dir_str}},
        )

    return ExtractTechSupportResponse(
        extract_dir=extract_dir_str,
        success=True,
        error_message=None,
        files=files,
    )
