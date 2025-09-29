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
        and returns detailed iError:
    Error executing tool extract_tech_support_file: 'FileInfo' object has no attribute 'size'nformation about all files found. It can filter files based on
        a glob pattern to help locate specific files of interest.

        Common important files to look for:
        - "show_tech_support.log": Main tech support log with device information
        - "config_db.json": Device configuration database
        - "syslog": System logs
        - "docker_ps.log": Container status information
        - "interfaces/": Directory containing interface statistics

        Args:
            request: The listing request containing the directory path and optional pattern filter

        Returns:
            ListTechSupportFilesResponse: The listing response containing file information,
                success status, and any error messages
    """
    logger.info(f"Processing list files request for directory: {request.extract_dir}")

    if request.pattern:
        logger.info(f"Using pattern filter: {request.pattern}")

    try:
        files = list_files(request.extract_dir, request.pattern)
        logger.info(f"Found {len(files)} files/directories")

        file_infos = [
            FileInfo(
                path=file.path,
                is_directory=file.is_directory,
            )
            for file in files
        ]

        logger.debug(f"Processed {len(file_infos)} file info objects")

        return ListTechSupportFilesResponse(files=file_infos, success=True, error_message=None)
    except Exception as e:
        logger.exception(f"Failed to list files: {str(e)}")
        return ListTechSupportFilesResponse(files=[], success=False, error_message=f"Failed to list files: {str(e)}")
