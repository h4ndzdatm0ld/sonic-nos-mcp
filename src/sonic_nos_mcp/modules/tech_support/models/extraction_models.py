"""Pydantic models for extraction operations."""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ExtractionResult(BaseModel):
    """Result of an extraction operation."""

    extract_dir: Path = Field(..., description="Path to the directory containing extracted files.")

    success: bool = Field(..., description="Whether the extraction was successful.")

    error_message: Optional[str] = Field(None, description="Error message if extraction failed.")

    nested_archives: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Dictionary mapping nested archive paths to their extracted directories.",
    )


class ExtractTechSupportRequest(BaseModel):
    """Request to extract a tech support file."""

    file_path: str = Field(..., description="Path to the tech support file to extract.")

    temp_dir: Optional[str] = Field(
        None,
        description="Optional path to temporary directory. If not provided, a system temp directory will be used.",
    )

    remove_archives: bool = Field(
        True,
        description="Whether to remove archive files after extraction.",
    )

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate that file_path exists and is a file.

        Args:
            v: The file path string to validate.

        Returns:
            str: Normalized absolute path if valid.

        Raises:
            ValueError: If file doesn't exist or is not a file.
        """
        path = Path(v).expanduser()
        if not path.exists():
            raise ValueError(f"Tech-support archive does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"Expected a file for 'file_path', got: {path}")
        return str(path.resolve())

    @field_validator("temp_dir")
    @classmethod
    def validate_temp_dir(cls, v: Optional[str]) -> Optional[str]:
        """Validate that temp_dir is a valid directory if provided.

        Args:
            v: The temp directory path string to validate, or None.

        Returns:
            Optional[str]: Normalized absolute path if valid, or None.

        Raises:
            ValueError: If temp_dir exists but is not a directory.
        """
        if v is None:
            return v
        path = Path(v).expanduser()
        if path.exists() and not path.is_dir():
            raise ValueError(f"Provided temp_dir exists but is not a directory: {path}")
        return str(path.resolve()) if path.exists() else str(path)


class ExtractTechSupportResponse(BaseModel):
    """Response from extracting a tech support file."""

    extract_dir: str = Field(..., description="Path to the directory containing extracted files.")

    success: bool = Field(..., description="Whether the extraction was successful.")

    error_message: Optional[str] = Field(None, description="Error message if extraction failed.")

    files: List[str] = Field(
        default_factory=list,
        description="List of relative file paths found in the extracted directory.",
    )
