"""Project-related schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    title: str = Field(..., min_length=1, max_length=255, description="Project title")
    description: Optional[str] = Field(None, max_length=1000, description="Optional project description")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "RFP: Cloud Infrastructure Services",
                "description": "Analysis and proposal for enterprise cloud services RFP"
            }
        }


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ProjectStatus] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Project Title",
                "status": "analyzed"
            }
        }


class ProjectResponse(BaseModel):
    """Schema for project response."""
    id: UUID
    title: str
    description: Optional[str]
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "RFP: Cloud Infrastructure Services",
                "description": "Analysis and proposal for enterprise cloud services RFP",
                "status": "created",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        }


class ProjectListResponse(BaseModel):
    """Schema for list of projects."""
    projects: list[ProjectResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "projects": [],
                "total": 0
            }
        }
