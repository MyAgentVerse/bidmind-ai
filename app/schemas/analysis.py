"""Analysis-related schemas."""

from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime
from uuid import UUID


class AnalysisResponse(BaseModel):
    """Schema for analysis result response."""
    id: UUID
    project_id: UUID
    document_type: Optional[str]
    opportunity_summary: Optional[str]
    scope_of_work: Optional[Any]
    mandatory_requirements: Optional[Any]
    deadlines: Optional[Any]
    evaluation_criteria: Optional[Any]
    budget_clues: Optional[Any]
    risks: Optional[Any]
    fit_score: Optional[float]
    usp_suggestions: Optional[Any]
    pricing_strategy_summary: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_type": "RFP",
                "opportunity_summary": "Enterprise-wide cloud infrastructure modernization",
                "scope_of_work": ["Infrastructure setup", "Migration support"],
                "mandatory_requirements": ["ISO 27001 certified", "24/7 support"],
                "deadlines": {"proposal_due": "2024-02-15", "decision_date": "2024-03-01"},
                "evaluation_criteria": ["Technical capability", "Cost", "Experience"],
                "budget_clues": {"estimated_range": "$500K - $1M annually"},
                "risks": ["Tight timeline", "Complex legacy system"],
                "fit_score": 85.5,
                "usp_suggestions": ["Proven migration experience", "Cost optimization"],
                "pricing_strategy_summary": "Value-based pricing with performance guarantees",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        }
