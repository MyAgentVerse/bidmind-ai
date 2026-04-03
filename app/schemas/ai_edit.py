"""AI editing-related schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class AIEditRequest(BaseModel):
    """Schema for requesting AI-assisted edit of a proposal section."""
    section_name: str = Field(..., description="Section to edit (e.g., 'executive_summary')")
    current_text: str = Field(..., description="Current section text to edit")
    instruction: str = Field(..., min_length=1, description="Edit instruction (e.g., 'Make this more concise', 'Strengthen this')")

    class Config:
        json_schema_extra = {
            "example": {
                "section_name": "executive_summary",
                "current_text": "We propose a solution...",
                "instruction": "Make this more persuasive and add specific benefits"
            }
        }


class AIEditResponse(BaseModel):
    """Schema for AI edit result."""
    section_name: str
    original_text: str
    instruction: str
    edited_text: str
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "section_name": "executive_summary",
                "original_text": "We propose a solution...",
                "instruction": "Make this more persuasive",
                "edited_text": "We propose a comprehensive solution that...",
                "created_at": "2024-01-15T10:30:00"
            }
        }
