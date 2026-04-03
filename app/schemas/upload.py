"""File upload-related schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class FileUploadResponse(BaseModel):
    """Schema for file upload response."""
    id: UUID
    project_id: UUID
    original_filename: str
    file_size: int
    mime_type: str
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "original_filename": "rfp-2024.pdf",
                "file_size": 1524288,
                "mime_type": "application/pdf",
                "created_at": "2024-01-15T10:30:00"
            }
        }


class FileListResponse(BaseModel):
    """Schema for list of uploaded files."""
    files: list[FileUploadResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "files": [],
                "total": 0
            }
        }
