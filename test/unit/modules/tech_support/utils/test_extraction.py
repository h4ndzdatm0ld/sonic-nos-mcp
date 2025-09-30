"""Unit tests for extraction utilities."""

import gzip
import logging
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sonic_nos_mcp.modules.tech_support.utils.extraction import (
    extract_file,
    extract_all_gz_files,
    delete_all_gz_files,
    remove_empty_directories,
    cleanup_extraction,
    is_archive_file,
)

logger = logging.getLogger(__name__)


class TestIsArchiveFile:
    """Test is_archive_file function."""

    def test_tar_gz_files(self):
        """Test .tar.gz file detection."""
        assert is_archive_file(Path("test.tar.gz")) is True
        assert is_archive_file(Path("file.TAR.GZ")) is True
        assert is_archive_file(Path("/path/to/archive.tar.gz")) is True

    def test_gz_files(self):
        """Test .gz file detection."""
        assert is_archive_file(Path("test.gz")) is True
        assert is_archive_file(Path("file.GZ")) is True
        assert is_archive_file(Path("log.gz")) is True

    def test_non_archive_files(self):
        """Test non-archive file detection."""
        assert is_archive_file(Path("test.txt")) is False
        assert is_archive_file(Path("file.json")) is False
        assert is_archive_file(Path("config.yaml")) is False
        assert is_archive_file(Path("")) is False


class TestExtractFile:
    """Test extract_file function."""

    @pytest.fixture
    def sample_tar_gz(self, temp_dir):
        """Create a sample tar.gz file."""
        archive_path = temp_dir / "sample.tar.gz"

        # Create some test files
        test_files_dir = temp_dir / "test_files"
        test_files_dir.mkdir()

        (test_files_dir / "file1.txt").write_text("Test file 1 content")
        (test_files_dir / "file2.json").write_text('{"test": "data"}')

        # Create tar.gz archive
        import tarfile

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(test_files_dir, arcname="test_files")

        return archive_path

    def test_extract_nonexistent_file(self):
        """Test extracting non-existent file."""
        result = extract_file("/nonexistent/file.tar.gz")
        assert result.success is False
        assert "File not found" in result.error_message

    def test_extract_tar_gz_file(self, sample_tar_gz, temp_dir):
        """Test extracting tar.gz file."""
        extract_dir = temp_dir / "extract"

        result = extract_file(sample_tar_gz, extract_dir)

        assert result.success is True
        assert result.extract_dir == extract_dir
        assert result.error_message is None

        # Verify files were extracted
        assert (extract_dir / "test_files" / "file1.txt").exists()
        assert (extract_dir / "test_files" / "file2.json").exists()

    def test_extract_single_gz_file(self, sample_gz_file, temp_dir):
        """Test extracting single .gz file."""
        extract_dir = temp_dir / "extract"

        result = extract_file(sample_gz_file, extract_dir)

        assert result.success is True
        assert result.extract_dir == extract_dir

        # Verify decompressed file exists
        extracted_file = extract_dir / "sample.txt"
        assert extracted_file.exists()
        assert extracted_file.read_text() == "This is test content for gz file compression testing"

    def test_extract_regular_file(self, temp_dir):
        """Test extracting regular (non-archive) file."""
        # Create regular file
        regular_file = temp_dir / "regular.txt"
        regular_file.write_text("Regular file content")

        extract_dir = temp_dir / "extract"
        result = extract_file(regular_file, extract_dir)

        assert result.success is True
        assert result.extract_dir == extract_dir

        # Verify file was copied
        copied_file = extract_dir / "regular.txt"
        assert copied_file.exists()
        assert copied_file.read_text() == "Regular file content"

    def test_extract_with_system_temp_dir(self, sample_gz_file):
        """Test extraction to system temp directory."""
        result = extract_file(sample_gz_file)

        try:
            assert result.success is True
            assert Path(result.extract_dir).exists()
            assert "sonic_techsupport_" in str(result.extract_dir)
        finally:
            # Clean up
            if Path(result.extract_dir).exists():
                shutil.rmtree(result.extract_dir)

    def test_extract_with_automatic_cleanup(self, temp_dir):
        """Test extraction with automatic archive and empty file cleanup."""
        # Create archive with nested .gz files
        main_dir = temp_dir / "main"
        main_dir.mkdir()

        # Create a nested .gz file
        gz_content = "Nested gz content"
        gz_file = main_dir / "nested.txt.gz"
        with gzip.open(gz_file, "wt") as f:
            f.write(gz_content)

        # Create tar.gz archive
        archive_path = temp_dir / "with_nested.tar.gz"
        import tarfile

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(main_dir, arcname="main")

        extract_dir = temp_dir / "extract"
        result = extract_file(archive_path, extract_dir)

        assert result.success is True

        # Verify nested .gz files were removed
        remaining_gz = list(extract_dir.rglob("*.gz"))
        # Filter out the original archive if it exists in extract dir
        remaining_gz = [f for f in remaining_gz if not f.name.endswith(archive_path.name)]
        assert len(remaining_gz) == 0

    @patch("tarfile.open")
    def test_extract_tar_gz_with_unsafe_paths(self, mock_tarfile, temp_dir):
        """Test extraction with unsafe archive paths."""
        # Mock tarfile with unsafe member
        mock_tar = Mock()
        unsafe_member = Mock()
        unsafe_member.name = "../unsafe_path"
        unsafe_member.isfile.return_value = True
        unsafe_member.isdir.return_value = False

        mock_tar.getmembers.return_value = [unsafe_member]
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        archive_path = temp_dir / "unsafe.tar.gz"
        archive_path.touch()

        result = extract_file(archive_path, temp_dir / "extract")

        assert result.success is False
        assert "Security issue" in result.error_message

    @patch("tarfile.open")
    def test_extract_tar_gz_extraction_error(self, mock_tarfile, temp_dir):
        """Test extraction with tarfile extraction error."""
        mock_tarfile.side_effect = Exception("Extraction failed")

        archive_path = temp_dir / "broken.tar.gz"
        archive_path.touch()

        result = extract_file(archive_path, temp_dir / "extract")

        assert result.success is False
        assert "Extraction failed" in result.error_message


class TestExtractAllGzFiles:
    """Test extract_all_gz_files function."""

    @pytest.fixture
    def temp_dir_with_gz_files(self):
        """Create temp directory with .gz files."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_gz_"))

        # Create nested .gz files
        (temp_path / "subdir").mkdir()

        # Create .gz files with content
        gz_files = [
            temp_path / "file1.txt.gz",
            temp_path / "subdir" / "file2.log.gz",
        ]

        for gz_file in gz_files:
            with gzip.open(gz_file, "wt") as f:
                f.write(f"Content for {gz_file.name}")

        # Create a .tar.gz file (should be skipped)
        tar_gz = temp_path / "archive.tar.gz"
        tar_gz.touch()

        yield temp_path

        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_extract_all_gz_files_success(self, temp_dir_with_gz_files):
        """Test successful extraction of all .gz files."""
        extracted_count = extract_all_gz_files(temp_dir_with_gz_files)

        assert extracted_count == 2  # Should extract 2 .gz files, skip .tar.gz

        # Verify extracted files exist
        assert (temp_dir_with_gz_files / "file1.txt").exists()
        assert (temp_dir_with_gz_files / "subdir" / "file2.log").exists()

        # Verify content is correct
        content1 = (temp_dir_with_gz_files / "file1.txt").read_text()
        assert "Content for file1.txt.gz" in content1

    def test_extract_all_gz_files_empty_directory(self):
        """Test extraction with no .gz files."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_empty_"))

        try:
            extracted_count = extract_all_gz_files(temp_path)
            assert extracted_count == 0
        finally:
            if temp_path.exists():
                shutil.rmtree(temp_path)

    @patch("gzip.open")
    def test_extract_gz_files_with_errors(self, mock_gzip_open, temp_dir_with_gz_files):
        """Test extraction with gzip errors."""
        mock_gzip_open.side_effect = Exception("Gzip error")

        # Should handle errors gracefully
        extracted_count = extract_all_gz_files(temp_dir_with_gz_files)
        assert extracted_count == 0  # No files should be extracted due to errors


class TestDeleteAllGzFiles:
    """Test delete_all_gz_files function."""

    @pytest.fixture
    def temp_dir_with_gz_files(self):
        """Create temp directory with .gz files."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_delete_gz_"))

        # Create .gz files
        (temp_path / "file1.gz").touch()
        (temp_path / "subdir").mkdir()
        (temp_path / "subdir" / "file2.gz").touch()

        # Create original archive (should be preserved)
        (temp_path / "original.tar.gz").touch()

        yield temp_path

        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_delete_all_gz_files_success(self, temp_dir_with_gz_files):
        """Test successful deletion of .gz files."""
        deleted_count = delete_all_gz_files(temp_dir_with_gz_files)

        assert deleted_count == 2  # Should delete 2 .gz files, preserve .tar.gz

        # Verify .gz files are deleted
        assert not (temp_dir_with_gz_files / "file1.gz").exists()
        assert not (temp_dir_with_gz_files / "subdir" / "file2.gz").exists()

        # Verify .tar.gz file is preserved
        assert (temp_dir_with_gz_files / "original.tar.gz").exists()

    def test_delete_gz_files_with_permission_error(self, temp_dir_with_gz_files):
        """Test deletion with permission errors."""
        with patch.object(Path, "unlink", side_effect=PermissionError("Permission denied")):
            deleted_count = delete_all_gz_files(temp_dir_with_gz_files)
            # Should continue despite errors but not delete any files due to permission issues
            assert deleted_count == 0  # No files deleted due to permission errors


class TestRemoveEmptyDirectories:
    """Test remove_empty_directories function."""

    @pytest.fixture
    def temp_dir_with_empty_dirs(self):
        """Create temp directory with empty subdirectories."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_empty_dirs_"))

        # Create empty directories
        (temp_path / "empty1").mkdir()
        (temp_path / "empty2").mkdir()
        (temp_path / "nested" / "empty3").mkdir(parents=True)

        # Create directory with file (should not be removed)
        non_empty = temp_path / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").write_text("content")

        yield temp_path

        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_remove_empty_directories_success(self, temp_dir_with_empty_dirs):
        """Test successful removal of empty directories."""
        removed_count = remove_empty_directories(temp_dir_with_empty_dirs)

        assert removed_count >= 1  # Should remove at least some empty dirs

        # Verify non-empty directory is preserved
        assert (temp_dir_with_empty_dirs / "non_empty").exists()
        assert (temp_dir_with_empty_dirs / "non_empty" / "file.txt").exists()

    def test_remove_empty_directories_nonexistent(self):
        """Test with non-existent directory."""
        result = remove_empty_directories("/nonexistent/path")
        assert result == 0

    def test_remove_empty_directories_not_dir(self, temp_dir_with_empty_dirs):
        """Test with file instead of directory."""
        file_path = temp_dir_with_empty_dirs / "not_dir.txt"
        file_path.write_text("content")

        result = remove_empty_directories(file_path)
        assert result == 0

    def test_remove_empty_directories_with_remove_root(self, temp_dir_with_empty_dirs):
        """Test with remove_root=True."""
        # Remove all contents first
        for item in temp_dir_with_empty_dirs.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        removed_count = remove_empty_directories(temp_dir_with_empty_dirs, remove_root=True)
        assert removed_count >= 0  # Should handle root removal

    @patch("os.rmdir")
    def test_remove_empty_directories_with_error(self, mock_rmdir, temp_dir_with_empty_dirs):
        """Test removal with OS errors."""
        mock_rmdir.side_effect = OSError("Permission denied")

        # Should handle errors gracefully
        removed_count = remove_empty_directories(temp_dir_with_empty_dirs)
        assert removed_count >= 0


class TestCleanupExtraction:
    """Test cleanup_extraction function."""

    def test_cleanup_existing_directory(self):
        """Test cleanup of existing directory."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_cleanup_"))

        # Create some files
        (temp_path / "file.txt").write_text("content")
        assert temp_path.exists()

        result = cleanup_extraction(temp_path)

        assert result is True
        assert not temp_path.exists()

    def test_cleanup_nonexistent_directory(self):
        """Test cleanup of non-existent directory."""
        result = cleanup_extraction("/nonexistent/directory")
        assert result is True  # Should succeed even if directory doesn't exist

    def test_cleanup_with_error(self):
        """Test cleanup with removal error."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_cleanup_error_"))

        with patch("shutil.rmtree", side_effect=OSError("Permission denied")):
            result = cleanup_extraction(temp_path)
            assert result is False

        # Clean up without the mock
        if temp_path.exists():
            shutil.rmtree(temp_path)


class TestExtractFileErrorCases:
    """Test extract_file error cases and edge conditions."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp_path = Path(tempfile.mkdtemp(prefix="test_extract_errors_"))
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)

    @patch("tarfile.open")
    def test_tar_extraction_with_member_error(self, mock_tarfile, temp_dir):
        """Test tar extraction with member extraction error."""
        # Create mock tar file with member that fails to extract
        mock_tar = Mock()
        mock_member = Mock()
        mock_member.name = "test_member"
        mock_member.isfile.return_value = True
        mock_member.isdir.return_value = False
        mock_member.mode = 0o644

        # First call for validation, second for extraction
        mock_tar.getmembers.return_value = [mock_member]
        mock_tar.extract.side_effect = Exception("Member extraction failed")
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        archive_path = temp_dir / "test.tar.gz"
        archive_path.touch()

        # Should continue despite member extraction errors
        result = extract_file(archive_path, temp_dir / "extract")
        assert result.success is True  # Overall extraction succeeds despite member errors

    @patch("gzip.open")
    def test_gz_extraction_with_gzip_error(self, mock_gzip_open, temp_dir):
        """Test .gz extraction with gzip error."""
        mock_gzip_open.side_effect = Exception("Gzip decompression failed")

        gz_file = temp_dir / "broken.gz"
        gz_file.touch()

        result = extract_file(gz_file, temp_dir / "extract")

        assert result.success is False
        assert "Extraction failed" in result.error_message

    @patch("shutil.copy2")
    def test_regular_file_copy_error(self, mock_copy, temp_dir):
        """Test regular file copy with error."""
        mock_copy.side_effect = Exception("Copy failed")

        regular_file = temp_dir / "regular.txt"
        regular_file.write_text("content")

        result = extract_file(regular_file, temp_dir / "extract")

        assert result.success is False
        assert "Extraction failed" in result.error_message


class TestRemoveEmptyFiles:
    """Test cases for remove_empty_files function."""

    def test_remove_empty_files_basic(self, temp_dir):
        """Test basic empty file removal."""
        logger.debug(f"Creating test files in directory: {temp_dir}")
        empty_file1 = temp_dir / "empty1.txt"
        empty_file2 = temp_dir / "empty2.log"
        non_empty_file = temp_dir / "content.txt"

        logger.debug("Creating empty files for testing")
        empty_file1.touch()
        empty_file2.touch()

        logger.debug("Creating non-empty file for testing")
        non_empty_file.write_text("This file has content")

        assert empty_file1.stat().st_size == 0
        assert empty_file2.stat().st_size == 0
        assert non_empty_file.stat().st_size > 0

        logger.debug("Running remove_empty_files function")
        from sonic_nos_mcp.modules.tech_support.utils.extraction import remove_empty_files

        removed_count = remove_empty_files(temp_dir)

        logger.debug(f"Removed {removed_count} empty files")
        assert removed_count == 2

        logger.debug("Verifying empty files were removed and non-empty file remains")
        assert not empty_file1.exists()
        assert not empty_file2.exists()
        assert non_empty_file.exists()
        assert non_empty_file.read_text() == "This file has content"

    def test_remove_empty_files_nested_directories(self, temp_dir):
        """Test empty file removal in nested directory structure."""
        from sonic_nos_mcp.modules.tech_support.utils.extraction import remove_empty_files

        logger.debug("Creating nested directory structure")
        subdir1 = temp_dir / "dir1" / "subdir1"
        subdir2 = temp_dir / "dir2"
        subdir1.mkdir(parents=True)
        subdir2.mkdir()

        logger.debug("Creating empty files in nested directories")
        empty_root = temp_dir / "empty_root.txt"
        empty_sub1 = subdir1 / "empty_nested.log"
        empty_sub2 = subdir2 / "empty_dir2.json"
        non_empty_root = temp_dir / "content_root.txt"

        empty_root.touch()
        empty_sub1.touch()
        empty_sub2.touch()
        non_empty_root.write_text("Root content")

        logger.debug("Running remove_empty_files on nested structure")
        removed_count = remove_empty_files(temp_dir)

        assert removed_count == 3
        assert not empty_root.exists()
        assert not empty_sub1.exists()
        assert not empty_sub2.exists()
        assert non_empty_root.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
