"""Shared test fixtures for all tests."""

import gzip
import logging
import tempfile
import shutil
from pathlib import Path
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_debug_logging():
    """Configure debug logging for integration testing."""
    # Configure debug logging for sonic_nos_mcp modules
    sonic_logger = logging.getLogger("sonic_nos_mcp")
    sonic_logger.setLevel(logging.DEBUG)

    # Create console handler if one doesn't exist
    if not sonic_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        sonic_logger.addHandler(handler)

    # Prevent propagation to avoid duplicate logs
    sonic_logger.propagate = False


@pytest.fixture(scope="session")
def real_tech_support_file():
    """Path to the real tech support file for all tests."""
    test_data_dir = Path(__file__).parent / "data" / "techsupport"
    tech_support_files = list(test_data_dir.glob("*.tar.gz"))

    if not tech_support_files:
        pytest.skip("No real tech support file found in test/data/techsupport")

    return tech_support_files[0]


@pytest.fixture
def temp_dir():
    """Create a temporary directory that is automatically cleaned up."""
    temp_path = Path(tempfile.mkdtemp(prefix="test_sonic_"))
    yield temp_path
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file for testing."""
    content = "Line 1\nLine 2 with ERROR\nLine 3\nLine 4 with WARNING\nLine 5"
    test_file = temp_dir / "sample.txt"
    test_file.write_text(content)
    return test_file


@pytest.fixture
def sample_log_file(temp_dir):
    """Create a sample log file with structured content."""
    content = """2024-01-01 10:00:00 INFO Starting service
2024-01-01 10:01:00 ERROR Connection failed
2024-01-01 10:02:00 WARN Retrying connection
2024-01-01 10:03:00 INFO Service started successfully
2024-01-01 10:04:00 ERROR Another error occurred"""
    log_file = temp_dir / "sample.log"
    log_file.write_text(content)
    return log_file


@pytest.fixture
def sample_directory_structure(temp_dir):
    """Create a sample directory structure for file listing tests."""
    # Create files and directories
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.json").write_text('{"key": "value"}')

    (temp_dir / "subdir1").mkdir()
    (temp_dir / "subdir1" / "file3.log").write_text("log content")

    (temp_dir / "subdir2").mkdir()
    (temp_dir / "subdir2" / "file4.conf").write_text("config content")
    (temp_dir / "subdir2" / "nested").mkdir()
    (temp_dir / "subdir2" / "nested" / "file5.txt").write_text("nested content")

    return temp_dir


@pytest.fixture
def sample_gz_file(temp_dir):
    """Create a sample .gz file for compression tests."""
    content = "This is test content for gz file compression testing"
    gz_file = temp_dir / "sample.txt.gz"
    with gzip.open(gz_file, "wt") as f:
        f.write(content)
    return gz_file


@pytest.fixture
def temp_dir_with_gz_files(temp_dir):
    """Create temp directory with .gz files for extraction tests."""
    # Create nested .gz files
    (temp_dir / "subdir").mkdir()

    # Create .gz files with content
    gz_files = [
        temp_dir / "file1.txt.gz",
        temp_dir / "subdir" / "file2.log.gz",
    ]

    for gz_file in gz_files:
        with gzip.open(gz_file, "wt") as f:
            f.write(f"Content for {gz_file.name}")

    # Create a .tar.gz file (should be skipped by gz extraction)
    (temp_dir / "archive.tar.gz").touch()

    return temp_dir


@pytest.fixture
def large_content_file(temp_dir):
    """Create a large file for chunking tests."""
    content = "A" * 100 + "B" * 100 + "C" * 100  # 300 characters
    large_file = temp_dir / "large.txt"
    large_file.write_text(content)
    return large_file
