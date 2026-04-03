"""Proposal-related schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ProposalSectionUpdate(BaseModel):
    """Schema for updating a single proposal section."""
    section_name: str = Field(..., description="Section to update (e.g., 'executive_summary')")
    text: str = Field(..., description="Updated section text")

    class Config:
        json_schema_extra = {
            "example": {
                "section_name": "executive_summary",
                "text": "Updated executive summary content..."
            }
        }


class ProposalUpdate(BaseModel):
    """Schema for updating the entire proposal."""
    cover_letter: Optional[str] = None
    executive_summary: Optional[str] = None
    understanding_of_requirements: Optional[str] = None
    proposed_solution: Optional[str] = None
    why_us: Optional[str] = None
    pricing_positioning: Optional[str] = None
    risk_mitigation: Optional[str] = None
    closing_statement: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "executive_summary": "Updated summary",
                "proposed_solution": "Updated solution"
            }
        }


class ProposalResponse(BaseModel):
    """Schema for proposal response."""
    id: UUID
    project_id: UUID
    cover_letter: Optional[str]
    executive_summary: Optional[str]
    understanding_of_requirements: Optional[str]
    proposed_solution: Optional[str]
    why_us: Optional[str]
    pricing_positioning: Optional[str]
    risk_mitigation: Optional[str]
    closing_statement: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174003",
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "cover_letter": "Dear Procurement Manager...",
                "executive_summary": "We propose a comprehensive solution...",
                "understanding_of_requirements": "We understand the following requirements...",
                "proposed_solution": "Our approach includes...",
                "why_us": "Our company brings...",
                "pricing_positioning": "Our pricing strategy...",
                "risk_mitigation": "We mitigate risks by...",
                "closing_statement": "We appreciate the opportunity...",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        }
