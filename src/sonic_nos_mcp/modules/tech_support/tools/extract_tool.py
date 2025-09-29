"""Tool for extracting SONiC tech-support files."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

from sonic_nos_mcp.modules.tech_support.models.extraction_models import (
    ExtractTechSupportRequest,
    ExtractTechSupportResponse,
)
from sonic_nos_mcp.modules.tech_support.utils.extraction import extract_file
from sonic_nos_mcp.modules.tech_support.utils.file_listing import list_files_simple

logger = logging.getLogger(__name__)


def _safe_abspath(path_str: str | os.PathLike[str]) -> str:
    """Return an absolute, normalized path string."""
    return str(Path(path_str).expanduser().resolve())


def _validate_inputs(request: ExtractTechSupportRequest) -> None:
    """Validate request inputs and raise ValueError with clear messages if invalid.

    Args:
        request: Extraction request object.

    Raises:
        ValueError: If file_path does not exist/is not a file, or temp_dir invalid.
    """
    file_path = Path(request.file_path).expanduser()
    if not file_path.exists():
        raise ValueError(f"Tech-support archive does not exist: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"Expected a file for 'file_path', got: {file_path}")

    if request.temp_dir is not None:
        temp_dir = Path(request.temp_dir).expanduser()
        if temp_dir.exists() and not temp_dir.is_dir():
            raise ValueError(f"Provided temp_dir exists but is not a directory: {temp_dir}")


def extract_tech_support(
    request: ExtractTechSupportRequest,
) -> ExtractTechSupportResponse:
    """Extract a SONiC tech-support tarball (and nested archives) to a temp directory.

    This function:
      1. Validates inputs.
      2. Delegates archive processing to utils.extraction.extract_file(), which MUST:
         - Extract the top-level tarball (e.g., sonic_dump_<host>_<ts>.tar.gz).
         - Recursively inflate nested archives: *.gz, *.tar, *.tar.gz, *.tgz, *.zip.
         - Optionally remove source archives after extraction if remove_archives=True.
      3. Produces a file listing for downstream tools (LLM navigation, indexing).

    Args:
        request: Extraction request containing:
            - file_path: path to the tech-support tarball
            - temp_dir: optional extraction root (created if missing)
            - remove_archives: optionally delete archives after extraction

    Returns:
        ExtractTechSupportResponse: with fields
            - extract_dir: absolute directory path where files now live
            - success: True/False
            - error_message: optional error string
            - files: recursive list (relative paths) of items under extract_dir
    """
    # Structured context for logs
    ctx = {
        "file_path": _safe_abspath(request.file_path),
        "temp_dir": _safe_abspath(request.temp_dir) if request.temp_dir else None,
        "remove_archives": bool(request.remove_archives),
    }
    logger.info("extract_tech_support: starting extraction", extra={"context": ctx})

    try:
        _validate_inputs(request)
    except Exception as e:  # pylint: disable=broad-except
        logger.error("extract_tech_support: input validation failed: %s", e, extra={"context": ctx})
        return ExtractTechSupportResponse(
            extract_dir="",
            success=False,
            error_message=str(e),
            files=[],
        )

    # Call lower-level extractor
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
    extract_dir_str = _safe_abspath(result.extract_dir) if getattr(result, "extract_dir", None) else ""
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

    # List files (resilient)
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
