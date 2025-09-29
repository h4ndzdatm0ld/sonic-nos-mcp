"""Utility functions for extracting tech support files."""

import gzip
import logging
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Optional, Union

from sonic_nos_mcp.modules.tech_support.models.extraction_models import ExtractionResult

logger = logging.getLogger(__name__)


def is_archive_file(file_path: Path) -> bool:
    """Check if a file is a .gz archive.

    Args:
        file_path: Path to the file to check

    Returns:
        bool: Whether the file is a .gz archive
    """
    return file_path.suffix.lower() == ".gz" or str(file_path).lower().endswith(".tar.gz")


def extract_file(
    file_path: Union[str, Path],
    temp_dir: Optional[Union[str, Path]] = None,
    remove_archives: bool = False,
) -> ExtractionResult:
    """Extract a tech support file to a temporary directory.

    Args:
        file_path: Path to the tech support file to extract
        temp_dir: Optional path to temporary directory. If not provided, a system temp directory will be used.
        remove_archives: Whether to remove archive files after extraction

    Returns:
        ExtractionResult: Result of the extraction operation
    """
    file_path = Path(file_path)
    logger.info(f"Extracting file: {file_path}")

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return ExtractionResult(
            extract_dir=Path(""),
            success=False,
            error_message=f"File not found: {file_path}",
        )

    logger.debug("Setting up extraction directory")
    if temp_dir is None:
        extract_dir = Path(tempfile.mkdtemp(prefix="sonic_techsupport_"))
        logger.info(f"Created temporary directory: {extract_dir}")
    else:
        extract_dir = Path(temp_dir)
        logger.info(f"Using provided directory: {extract_dir}")
        os.makedirs(extract_dir, exist_ok=True)

    try:
        logger.debug("Determining archive type")
        if str(file_path).lower().endswith(".tar.gz"):
            logger.info(f"Extracting tar.gz file: {file_path}")
            with tarfile.open(file_path, "r:gz") as tar_ref:
                logger.debug("Validating archive paths for security issues")
                for member in tar_ref.getmembers():
                    if member.name.startswith("/") or ".." in member.name:
                        logger.error(f"Security issue: Archive contains unsafe paths: {member.name}")
                        return ExtractionResult(
                            extract_dir=extract_dir,
                            success=False,
                            error_message=f"Security issue: Archive contains unsafe paths: {member.name}",
                        )
                logger.debug("Performing custom extraction with safe permissions")
                for member in tar_ref.getmembers():
                    logger.debug(f"Processing archive member: {member.name}")
                    if not (member.isfile() or member.isdir()):
                        continue

                    try:
                        logger.debug(f"Setting safe permissions for: {member.name}")
                        original_mode = member.mode
                        member.mode = 0o644 if member.isfile() else 0o755

                        tar_ref.extract(member, path=extract_dir, filter="data")

                        logger.debug(f"Successfully extracted: {member.name}")
                        member.mode = original_mode

                    except Exception as e:
                        logger.warning(f"Error extracting {member.name}: {str(e)}")
        elif file_path.suffix.lower() == ".gz":
            logger.debug("Processing single gzip file")
            output_file = extract_dir / file_path.with_suffix("").name
            logger.info(f"Extracting .gz file: {file_path} to {output_file}")
            with gzip.open(file_path, "rb") as f_in:
                with open(output_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            logger.debug(f"Setting safe permissions for extracted file: {output_file}")
            output_file.chmod(0o644)
        else:
            logger.debug("Processing non-archive file (simple copy)")
            logger.info(f"Copying single file: {file_path}")
            dest_file = extract_dir / file_path.name
            shutil.copy2(file_path, dest_file)
            logger.info(f"Copied file to {dest_file}")
    except Exception as e:
        logger.exception(f"Extraction failed: {str(e)}")
        return ExtractionResult(
            extract_dir=extract_dir,
            success=False,
            error_message=f"Extraction failed: {str(e)}",
        )

    logger.info(f"Initial extraction completed successfully to {extract_dir}")

    logger.debug("Processing any nested gzip files recursively")
    extract_all_gz_files(extract_dir)

    logger.debug(f"Remove archives flag set to: {remove_archives}")
    if remove_archives:
        delete_all_gz_files(extract_dir)

        logger.debug("Cleaning up empty directories after archive removal")
        removed_dirs = remove_empty_directories(extract_dir)
        if removed_dirs > 0:
            logger.info(f"Removed {removed_dirs} empty directories")

    return ExtractionResult(
        extract_dir=extract_dir,
        success=True,
        error_message=None,
        nested_archives={},
    )


def extract_all_gz_files(extract_dir: Path) -> int:
    """
    Recursively unzips all .gz files found in the directory and subdirectories.
    The .gz file will be extracted next to the original file with the same name (no .gz extension).

    Args:
        extract_dir: The root directory to start searching from.

    Returns:
        int: Number of files extracted
    """
    extract_dir = Path(extract_dir)
    gz_files = list(extract_dir.rglob("*.gz"))
    extracted_count = 0

    for gz_file in gz_files:
        logger.debug(f"Processing: {gz_file}")
        if str(gz_file).lower().endswith(".tar.gz"):
            continue

        output_file = gz_file.with_suffix("")  # Remove .gz extension

        logger.info(f"Unzipping {gz_file} to {output_file}")
        try:
            logger.debug("Creating temporary file to ensure atomic extraction")
            temp_output_file = output_file.with_suffix(".tmp")

            with gzip.open(gz_file, "rb") as f_in:
                with open(temp_output_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            logger.debug("Extraction successful, finalizing file")
            temp_output_file.rename(output_file)

            logger.debug(f"Setting safe permissions for extracted file: {output_file}")
            output_file.chmod(0o644)

            extracted_count += 1
        except Exception as e:
            logger.warning(f"Error extracting {gz_file}: {str(e)}")
            logger.debug("Cleaning up temporary files after failed extraction")
            temp_output_file = output_file.with_suffix(".tmp")
            if temp_output_file.exists():
                temp_output_file.unlink()

    logger.info(f"Extracted {extracted_count} .gz files recursively")
    return extracted_count


def delete_all_gz_files(extract_dir: Path) -> int:
    """
    Recursively deletes all .gz files in the directory and subdirectories.

    Args:
        extract_dir: The root directory to start deleting from.

    Returns:
        int: Number of files deleted
    """
    extract_dir = Path(extract_dir)
    logger.debug("Searching for .gz files to delete")
    gz_files = list(extract_dir.rglob("*.gz"))
    deleted_count = 0

    for gz_file in gz_files:
        logger.debug(f"Evaluating file for deletion: {gz_file}")
        if gz_file.name.endswith(".tar.gz") and gz_file.parent == extract_dir:
            logger.info(f"Skipping original archive file: {gz_file}")
            continue

        try:
            logger.info(f"Deleting {gz_file}")
            gz_file.unlink()
            deleted_count += 1
        except Exception as e:
            logger.warning(f"Error deleting {gz_file}: {str(e)}")

    logger.info(f"Deleted {deleted_count} .gz files")
    return deleted_count


def remove_empty_directories(directory: Union[str, Path], remove_root: bool = False) -> int:
    """Remove empty directories recursively.

    Args:
        directory: Path to the directory to clean up
        remove_root: Whether to remove the root directory if it's empty

    Returns:
        int: Number of directories removed
    """
    directory = Path(directory)
    if not directory.exists() or not directory.is_dir():
        return 0

    removed_count = 0

    logger.debug("Walking directory tree bottom-up to find empty directories")
    for root, dirs, files in os.walk(directory, topdown=False):
        root_path = Path(root)

        logger.debug(f"Evaluating directory for removal: {root_path}")
        if not remove_root and root_path == directory:
            continue

        if not files and not any(os.path.isdir(os.path.join(root, d)) for d in dirs):
            try:
                logger.info(f"Removing empty directory: {root_path}")
                os.rmdir(root_path)
                removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove empty directory {root_path}: {str(e)}")

    return removed_count


def cleanup_extraction(extract_dir: Union[str, Path]) -> bool:
    """Clean up an extraction directory.

    Args:
        extract_dir: Path to the extraction directory to clean up

    Returns:
        bool: Whether the cleanup was successful
    """
    extract_dir = Path(extract_dir)
    logger.info(f"Cleaning up extraction directory: {extract_dir}")

    try:
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
            logger.info(f"Successfully removed directory: {extract_dir}")
        else:
            logger.warning(f"Directory does not exist: {extract_dir}")
        return True
    except Exception as e:
        logger.exception(f"Failed to clean up directory {extract_dir}: {str(e)}")
        return False
