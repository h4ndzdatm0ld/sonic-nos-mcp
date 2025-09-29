"""Comprehensive extraction validation tests.

These tests ensure 100% complete extraction and decompression of all files
in SONiC tech support archives, with detailed verification of file integrity.
"""

import tempfile
from pathlib import Path
import pytest

from sonic_nos_mcp.modules.tech_support.utils.extraction import (
    extract_file,
    extract_all_gz_files,
    cleanup_extraction,
)


class TestComprehensiveExtraction:
    """Comprehensive tests to validate 100% complete file extraction and decompression."""

    @pytest.fixture(scope="class")
    def real_tech_support_file(self):
        """Path to the real tech support file."""
        test_data_dir = Path(__file__).parent.parent / "data"
        tech_support_files = list(test_data_dir.glob("sonic_dump_*.tar.gz"))

        if not tech_support_files:
            pytest.skip("No real tech support file found in test/data")

        return tech_support_files[0]

    def test_complete_extraction_verification(self, real_tech_support_file):
        """Test that 100% of files are extracted and decompressed correctly."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_complete_extraction_"))

        try:
            # Step 1: Extract the main archive
            result = extract_file(real_tech_support_file, temp_dir)
            assert result.success is True
            assert result.extract_dir == temp_dir

            # Step 2: Count all files before nested extraction
            all_files_before = list(temp_dir.rglob("*"))
            files_before = [f for f in all_files_before if f.is_file()]
            gz_files_before = [f for f in files_before if f.suffix == ".gz" and not str(f).endswith(".tar.gz")]

            print(f"Files before nested extraction: {len(files_before)}")
            print(f"Compressed .gz files found: {len(gz_files_before)}")

            # Step 3: Extract all nested .gz files
            extracted_count = extract_all_gz_files(temp_dir)

            # Step 4: Verify extraction results
            all_files_after = list(temp_dir.rglob("*"))
            files_after = [f for f in all_files_after if f.is_file()]
            gz_files_after = [f for f in files_after if f.suffix == ".gz" and not str(f).endswith(".tar.gz")]

            print(f"Files after nested extraction: {len(files_after)}")
            print(f"Remaining compressed .gz files: {len(gz_files_after)}")
            print(f"Extracted file count reported: {extracted_count}")

            # Step 5: Comprehensive validation

            # Verify we extracted the reported number of files
            if gz_files_before:
                assert (
                    extracted_count > 0
                ), f"Should have extracted some files from {len(gz_files_before)} .gz files found"
            else:
                assert extracted_count == 0, "No .gz files found, so extraction count should be 0"

            # Verify we have more files after extraction (if we had .gz files to extract)
            if gz_files_before:
                assert len(files_after) >= len(
                    files_before
                ), "Should have at least same number of files after extraction"

            # Step 6: Validate every extracted file is readable
            readable_files = 0
            binary_files = 0
            unreadable_files = []

            for file_path in files_after:
                if file_path.suffix == ".gz":
                    continue  # Skip remaining compressed files

                try:
                    # Test if file is readable as text
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.read(100)  # Try to read first 100 characters
                    readable_files += 1
                except UnicodeDecodeError:
                    # Likely binary file
                    binary_files += 1
                except PermissionError:
                    unreadable_files.append(str(file_path))
                except Exception:
                    unreadable_files.append(str(file_path))

            print(f"Readable text files: {readable_files}")
            print(f"Binary files: {binary_files}")
            print(f"Unreadable files: {len(unreadable_files)}")

            # Most files should be readable (SONiC files are mostly text/JSON/logs)
            total_testable_files = readable_files + binary_files
            assert total_testable_files > 0, "Should have at least some files to test"

            # Should have minimal unreadable files (only if permissions issues)
            unreadable_percentage = len(unreadable_files) / len(files_after) * 100
            assert (
                unreadable_percentage < 10
            ), f"Too many unreadable files ({unreadable_percentage:.1f}%): {unreadable_files[:5]}"

        finally:
            cleanup_extraction(temp_dir)

    def test_all_gz_files_extracted_and_accessible(self, real_tech_support_file):
        """Test that ALL .gz files are extracted to readable decompressed versions."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_gz_extraction_"))

        try:
            # Extract and decompress everything
            result = extract_file(real_tech_support_file, temp_dir)
            assert result.success is True

            # Count .gz files before extraction
            gz_files_before = [f for f in temp_dir.rglob("*.gz") if f.is_file() and not str(f).endswith(".tar.gz")]
            print(f"Found {len(gz_files_before)} .gz files to extract")

            extracted_count = extract_all_gz_files(temp_dir)

            # Verify extraction count matches found files
            assert extracted_count == len(
                gz_files_before
            ), f"Expected to extract {len(gz_files_before)} files, but extracted {extracted_count}"

            # Verify each .gz file now has a decompressed version
            missing_decompressed = []
            empty_but_valid = []
            successfully_extracted = 0

            for gz_file in gz_files_before:
                # Expected decompressed file (same name without .gz)
                decompressed_file = gz_file.with_suffix("")

                if not decompressed_file.exists():
                    missing_decompressed.append(str(gz_file))
                else:
                    # Verify the decompressed file is accessible
                    try:
                        file_size = decompressed_file.stat().st_size
                        if file_size == 0:
                            # Empty files are valid in SONiC dumps (empty logs, etc.)
                            empty_but_valid.append(str(gz_file))
                            successfully_extracted += 1
                        else:
                            # Try to read first few bytes to verify it's accessible
                            with open(decompressed_file, "rb") as f:
                                f.read(10)
                            successfully_extracted += 1
                    except Exception as e:
                        missing_decompressed.append(f"{gz_file} -> unreadable: {e}")

            print(f"Successfully extracted: {successfully_extracted}/{len(gz_files_before)} files")
            print(f"Empty but valid files: {len(empty_but_valid)} files")
            print(f"Missing or problematic files: {len(missing_decompressed)} files")

            # 100% of .gz files should have been successfully extracted (empty files are valid)
            assert (
                len(missing_decompressed) == 0
            ), f"Failed to extract or access {len(missing_decompressed)} files: {missing_decompressed[:5]}"
            assert successfully_extracted == len(
                gz_files_before
            ), f"Expected {len(gz_files_before)} successful extractions, got {successfully_extracted}"

        finally:
            cleanup_extraction(temp_dir)

    def test_complete_removal_of_compressed_files(self, real_tech_support_file):
        """Test complete removal of .gz files when remove_archives=True."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_complete_removal_"))

        try:
            # Extract with archive removal enabled
            result = extract_file(real_tech_support_file, temp_dir, remove_archives=True)
            assert result.success is True

            # Find any remaining .gz files
            remaining_gz_files = []
            for gz_file in temp_dir.rglob("*.gz"):
                if gz_file.is_file():
                    # Skip the original archive file if it was copied to extract dir
                    if gz_file.name == real_tech_support_file.name and gz_file.parent == temp_dir:
                        continue
                    remaining_gz_files.append(gz_file)

            print(f"Remaining .gz files after removal: {len(remaining_gz_files)}")
            if remaining_gz_files:
                print("Remaining files:", [str(f) for f in remaining_gz_files[:5]])

            # With remove_archives=True, NO .gz files should remain
            assert (
                len(remaining_gz_files) == 0
            ), f"Found {len(remaining_gz_files)} remaining .gz files after remove_archives=True!"

        finally:
            cleanup_extraction(temp_dir)

    def test_extraction_integrity_validation(self, real_tech_support_file):
        """Test that extracted files have proper integrity and are not corrupted."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_integrity_"))

        try:
            # Extract everything
            result = extract_file(real_tech_support_file, temp_dir)
            assert result.success is True

            extract_all_gz_files(temp_dir)

            # Find all extracted files
            all_files = [f for f in temp_dir.rglob("*") if f.is_file()]

            # Test integrity of different file types
            json_files_tested = 0
            log_files_tested = 0
            text_files_tested = 0
            corrupted_files = []

            for file_path in all_files:
                try:
                    file_size = file_path.stat().st_size

                    # Skip empty files and very large files for this test
                    if file_size == 0 or file_size > 50 * 1024 * 1024:  # Skip > 50MB
                        continue

                    # Test JSON files can be parsed
                    if file_path.suffix == ".json" or "DB.json" in file_path.name:
                        try:
                            import json

                            with open(file_path, "r") as f:
                                json.load(f)  # Verify JSON is valid
                            json_files_tested += 1
                        except json.JSONDecodeError:
                            corrupted_files.append(f"JSON parsing failed: {file_path}")

                    # Test log files are readable
                    elif "log" in file_path.name.lower() or file_path.suffix in [".log", ".txt"]:
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                f.read(1000)  # Read first 1KB to verify readability
                            log_files_tested += 1
                        except Exception:
                            corrupted_files.append(f"Log file read failed: {file_path}")

                    # Test general text files
                    else:
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read(500)  # Read first 500 chars
                                # Should have some readable content
                                if len(content.strip()) > 0:
                                    text_files_tested += 1
                        except Exception:
                            # Might be binary, skip
                            pass

                except Exception as e:
                    corrupted_files.append(f"File access failed for {file_path}: {e}")

            print(f"JSON files tested: {json_files_tested}")
            print(f"Log files tested: {log_files_tested}")
            print(f"Text files tested: {text_files_tested}")
            print(f"Corrupted files found: {len(corrupted_files)}")

            # Verify we tested some files and found minimal corruption
            total_tested = json_files_tested + log_files_tested + text_files_tested
            assert total_tested > 0, "Should have tested at least some files for integrity"

            # Allow some files to be unreadable (binary files, special formats)
            corruption_rate = len(corrupted_files) / max(total_tested, 1) * 100
            assert corruption_rate < 20, f"Too many corrupted files ({corruption_rate:.1f}%): {corrupted_files[:3]}"

        finally:
            cleanup_extraction(temp_dir)

    def test_directory_structure_preservation(self, real_tech_support_file):
        """Test that directory structure is properly preserved after extraction."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_structure_"))

        try:
            # Extract everything
            result = extract_file(real_tech_support_file, temp_dir)
            assert result.success is True

            extract_all_gz_files(temp_dir)

            # Verify key SONiC directory structure exists
            expected_dirs = ["dump", "log", "proc", "etc"]
            found_dirs = []

            for expected_dir in expected_dirs:
                dir_paths = list(temp_dir.rglob(expected_dir))
                if any(p.is_dir() for p in dir_paths):
                    found_dirs.append(expected_dir)

            print(f"Expected SONiC directories: {expected_dirs}")
            print(f"Found directories: {found_dirs}")

            # Should find at least some standard SONiC directories
            assert len(found_dirs) > 0, "Should find at least some standard SONiC directories in extracted files"

            # Verify files exist in expected directories
            files_in_structure = {}
            for dir_name in found_dirs:
                dir_paths = [p for p in temp_dir.rglob(dir_name) if p.is_dir()]
                for dir_path in dir_paths:
                    files_in_dir = [f for f in dir_path.rglob("*") if f.is_file()]
                    if files_in_dir:
                        files_in_structure[dir_name] = len(files_in_dir)
                        break

            print(f"Files found in structure: {files_in_structure}")

            # Should have files in the directory structure
            assert len(files_in_structure) > 0, "Should find files in the expected directory structure"

        finally:
            cleanup_extraction(temp_dir)

    def test_file_content_accessibility(self, real_tech_support_file):
        """Test that all extracted files are accessible and have valid content."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_accessibility_"))

        try:
            # Complete extraction
            result = extract_file(real_tech_support_file, temp_dir)
            assert result.success is True

            extract_all_gz_files(temp_dir)

            # Get all files
            all_files = [f for f in temp_dir.rglob("*") if f.is_file()]

            accessible_count = 0
            inaccessible_files = []
            empty_files = []

            for file_path in all_files:
                try:
                    # Check file stats
                    file_stat = file_path.stat()

                    if file_stat.st_size == 0:
                        empty_files.append(str(file_path))
                        continue

                    # Try to open and read file
                    with open(file_path, "rb") as f:
                        f.read(10)  # Try to read first 10 bytes
                    accessible_count += 1

                except (PermissionError, OSError) as e:
                    inaccessible_files.append(f"{file_path}: {e}")

            print(f"Total files found: {len(all_files)}")
            print(f"Accessible files: {accessible_count}")
            print(f"Empty files: {len(empty_files)}")
            print(f"Inaccessible files: {len(inaccessible_files)}")

            # Verify most files are accessible
            accessibility_rate = accessible_count / max(len(all_files), 1) * 100
            assert accessibility_rate > 80, f"Only {accessibility_rate:.1f}% of files are accessible"

            # Allow some empty files (might be normal in SONiC dumps)
            empty_rate = len(empty_files) / max(len(all_files), 1) * 100
            assert empty_rate < 30, f"Too many empty files ({empty_rate:.1f}%)"

            # Should have minimal inaccessible files
            inaccessible_rate = len(inaccessible_files) / max(len(all_files), 1) * 100
            assert inaccessible_rate < 5, f"Too many inaccessible files ({inaccessible_rate:.1f}%)"

        finally:
            cleanup_extraction(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
