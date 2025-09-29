"""Utility functions for listing files in a directory."""

import fnmatch
import logging
import os
from pathlib import Path
from typing import List, Optional, Union

from sonic_nos_mcp.modules.tech_support.models.file_listing_models import FileInfo

logger = logging.getLogger(__name__)


def list_files(directory: Union[str, Path], pattern: Optional[str] = None) -> List[FileInfo]:
    """List all files in a directory recursively, optionally filtered by a glob pattern.

    All files and directories at all levels will be included in the results.
    If a pattern is provided, only files and directories matching that pattern will be included.

    Args:
        directory: Path to the directory to list files from
        pattern: Optional glob pattern to filter files and directories

    Returns:
        List[FileInfo]: List of file information objects
    """
    directory = Path(directory)
    logger.info(f"Listing files recursively in directory: {directory}")

    if not directory.exists():
        logger.error(f"Directory does not exist: {directory}")
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not directory.is_dir():
        logger.error(f"Path is not a directory: {directory}")
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    result = []

    if pattern:
        logger.info(f"Using pattern filter: {pattern}")

    try:
        for root, dirs, files in os.walk(directory):
            logger.debug(f"Processing directory: {root}")

            logger.debug(f"Processing {len(dirs)} directories in {root}")
            for dir_name in dirs:
                full_path = Path(root) / dir_name
                rel_path = full_path.relative_to(directory)

                if pattern and not fnmatch.fnmatch(str(rel_path), pattern):
                    logger.debug(f"Skipping directory (pattern mismatch): {rel_path}")
                    continue

                logger.debug(f"Adding directory: {rel_path}")
                result.append(
                    FileInfo(
                        path=str(rel_path),
                        is_directory=True,
                    )
                )

            logger.debug(f"Processing {len(files)} files in {root}")
            for file_name in files:
                full_path = Path(root) / file_name
                rel_path = full_path.relative_to(directory)

                if pattern:
                    logger.debug(f"Applying pattern filter for file: {rel_path}")
                    if "**/" in pattern:
                        logger.debug(f"Using special handling for **/ pattern: {pattern}")
                        pattern_suffix = pattern.split("**/", 1)[1]
                        if not (fnmatch.fnmatch(file_name, pattern_suffix) or fnmatch.fnmatch(str(rel_path), pattern)):
                            logger.debug(f"Skipping file (pattern mismatch): {rel_path}")
                            continue
                    elif not fnmatch.fnmatch(str(rel_path), pattern):
                        logger.debug(f"Skipping file (pattern mismatch): {rel_path}")
                        continue

                logger.debug(f"Adding file: {rel_path}")
                result.append(
                    FileInfo(
                        path=str(rel_path),
                        is_directory=False,
                    )
                )
    except PermissionError as e:
        logger.warning("Propagating permission error to caller")
        logger.error(f"Permission error accessing {directory}: {str(e)}")
        raise
    except Exception as e:
        logger.warning("Caught error during file listing, returning partial results")
        logger.error(f"Error listing files in {directory}: {str(e)}")

    logger.info(f"Found {len(result)} files/directories in {directory}")
    return result


def list_files_simple(directory: Union[str, Path], pattern: Optional[str] = None) -> List[str]:
    """List all files in a directory recursively as simple string paths.

    Args:
        directory: Path to the directory to list files from
        pattern: Optional glob pattern to filter files and directories

    Returns:
        List[str]: List of relative file paths
    """
    file_infos = list_files(directory, pattern)
    return [file_info.path for file_info in file_infos]
