"""Document models for parsed content."""

from typing import Optional

from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    """
    Model for parsed document content.

    Contains the extracted text and metadata from a document file.
    """

    text: str = Field(..., description="Extracted text content")
    metadata: "DocumentMetadata" = Field(..., description="Document metadata")
    file_type: str = Field(..., description="Original file type (pdf, docx, txt, md)")


class DocumentMetadata(BaseModel):
    """Metadata extracted from a document."""

    page_count: Optional[int] = Field(None, description="Number of pages (for PDF)")
    word_count: Optional[int] = Field(None, description="Approximate word count")
    character_count: Optional[int] = Field(None, description="Character count")
    title: Optional[str] = Field(None, description="Document title")
    author: Optional[str] = Field(None, description="Document author")
    created_at: Optional[str] = Field(None, description="Document creation date")
    modified_at: Optional[str] = Field(None, description="Document modification date")
    language: Optional[str] = Field(None, description="Document language")
    encoding: Optional[str] = Field(None, description="Text encoding (for TXT files)")

