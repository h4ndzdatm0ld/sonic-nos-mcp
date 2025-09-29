"""Pydantic models for text chunking operations."""

from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class TextChunk(BaseModel):
    """A chunk of text from a file."""

    content: str = Field(..., description="The content of the chunk.")

    page: int = Field(..., description="The page number (1-based).")

    total_pages: int = Field(..., description="The total number of pages.")

    file_path: str = Field(..., description="The path to the file.")


class InspectTechSupportFileRequest(BaseModel):
    """Request to inspect a file in a tech support directory."""

    file_path: str = Field(..., description="Path to the file to inspect.")

    chunk_size: Optional[int] = Field(
        None,
        description="Optional chunk size in characters. Overrides the environment variable.",
    )

    page: int = Field(1, description="Optional page number to retrieve (starting from 1).")


class InspectTechSupportFileResponse(BaseModel):
    """Response from inspecting a file in a tech support directory."""

    content: str = Field(..., description="The content of the file chunk.")

    page: int = Field(..., description="The page number (1-based).")

    total_pages: int = Field(..., description="The total number of pages.")

    file_path: str = Field(..., description="The path to the file.")

    success: bool = Field(..., description="Whether the inspection was successful.")

    error_message: Optional[str] = Field(None, description="Error message if inspection failed.")


class GetTechSupportFileContentRequest(BaseModel):
    """Request to get content from a tech support file."""

    file_path: str = Field(..., description="Path to the file to read.")

    pattern: Optional[str] = Field(
        None,
        description="Optional regex pattern to extract specific content from the file.",
    )

    chunk_size: Optional[str] = Field(
        None,
        description="Optional chunk size in characters. Overrides the environment variable.",
    )

    page: int = Field(1, description="Optional page number to retrieve (starting from 1).")


class GetTechSupportFileContentResponse(BaseModel):
    """Response from getting content from a tech support file."""

    content: str = Field(..., description="The content of the file.")

    matches: List[str] = Field(
        default_factory=list,
        description="List of regex matches if a pattern was provided.",
    )

    page: int = Field(..., description="The page number (1-based).")

    total_pages: int = Field(..., description="The total number of pages.")

    file_path: str = Field(..., description="The path to the file.")

    success: bool = Field(..., description="Whether the operation was successful.")

    error_message: Optional[str] = Field(None, description="Error message if the operation failed.")
