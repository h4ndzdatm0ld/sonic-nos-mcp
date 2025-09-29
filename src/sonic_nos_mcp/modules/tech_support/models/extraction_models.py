"""Pydantic models for extraction operations."""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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


class ExtractTechSupportResponse(BaseModel):
    """Response from extracting a tech support file."""

    extract_dir: str = Field(..., description="Path to the directory containing extracted files.")

    success: bool = Field(..., description="Whether the extraction was successful.")

    error_message: Optional[str] = Field(None, description="Error message if extraction failed.")

    files: List[str] = Field(
        default_factory=list,
        description="List of relative file paths found in the extracted directory.",
    )
