"""Pydantic models for file listing operations."""

from typing import List, Optional

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Information about a file."""

    path: str = Field(..., description="Full path to the file.")

    is_directory: bool = Field(..., description="Whether the file is a directory.")


class ListTechSupportFilesRequest(BaseModel):
    """Request to list files in a tech support directory."""

    extract_dir: str = Field(
        ...,
        description="Path to the directory containing extracted tech support files.",
    )

    pattern: Optional[str] = Field(None, description="Optional glob pattern to filter files.")


class ListTechSupportFilesResponse(BaseModel):
    """Response from listing files in a tech support directory."""

    files: List[FileInfo] = Field(..., description="List of file information objects.")

    success: bool = Field(..., description="Whether the listing was successful.")

    error_message: Optional[str] = Field(None, description="Error message if listing failed.")
