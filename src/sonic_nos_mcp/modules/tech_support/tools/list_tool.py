"""Tool for listing files in a SONIC tech support directory."""

import logging

from sonic_nos_mcp.modules.tech_support.models.file_listing_models import (
    FileInfo,
    ListTechSupportFilesRequest,
    ListTechSupportFilesResponse,
)
from sonic_nos_mcp.modules.tech_support.utils.file_listing import list_files

logger = logging.getLogger(__name__)


def list_tech_support_files(
    request: ListTechSupportFilesRequest,
) -> ListTechSupportFilesResponse:
    """List all files in a tech support directory.

    This function scans the specified directory (typically an extracted tech support archive)
    and returns detailed information about all files found including their sizes. It can filter
    files based on a glob pattern to help locate specific files of interest.

    Only actual files are returned - directories are skipped.

    Common important files to look for:
    - "show_tech_support.log": Main tech support log with device information
    - "config_db.json": Device configuration database
    - "syslog": System logs
    - "docker_ps.log": Container status information
    - Various files in subdirectories like dump/, log/, proc/, etc.

    Args:
        request: The listing request containing the directory path and optional pattern filter

    Returns:
        ListTechSupportFilesResponse: The listing response containing file information with paths,
            sizes, success status, and any error messages
    """
    logger.info(f"Processing list files request for directory: {request.extract_dir}")

    if request.pattern:
        logger.info(f"Using pattern filter: {request.pattern}")

    try:
        files = list_files(request.extract_dir, request.pattern)
        logger.info(f"Found {len(files)} files")

        file_infos = [
            FileInfo(
                path=file.path,
                size=file.size,
            )
            for file in files
        ]

        logger.debug(f"Processed {len(file_infos)} file info objects")

        return ListTechSupportFilesResponse(files=file_infos, success=True, error_message=None)
    except Exception as e:
        logger.exception(f"Failed to list files: {str(e)}")
        return ListTechSupportFilesResponse(files=[], success=False, error_message=f"Failed to list files: {str(e)}")
