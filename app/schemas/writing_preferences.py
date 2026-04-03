"""Pydantic schemas for CompanyWritingPreferences model."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class WritingPreferencesBase(BaseModel):
    """Base writing preferences schema with common fields."""

    # WRITING STYLE SECTION
    tone_level: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Tone level from 1 (Casual) to 5 (Very Formal)"
    )
    brand_voice_tags: List[str] = Field(
        default_factory=list,
        description="Brand voice tags: Trustworthy, Innovative, Professional, Friendly, Technical, etc."
    )
    language_complexity: str = Field(
        default="standard",
        description="Language complexity: simple, standard, or technical"
    )
    company_jargon: Optional[str] = Field(
        None,
        description="Custom words/phrases the company uses"
    )

    # CONTENT GUIDELINES SECTION
    must_include: List[str] = Field(
        default_factory=list,
        description="Items that must be included in proposals"
    )
    do_not_include: Optional[str] = Field(
        None,
        description="Things to avoid or exclude from proposals"
    )
    focus_areas: Dict[str, int] = Field(
        default_factory=dict,
        description="Weighted focus areas with 1-10 scale (e.g., {'quality': 8, 'price': 5})"
    )

    # PROPOSAL STRUCTURE SECTION
    required_sections: List[str] = Field(
        default_factory=lambda: [
            "cover_letter",
            "executive_summary",
            "understanding_of_requirements",
            "proposed_solution",
            "why_us",
            "pricing_positioning",
            "risk_mitigation",
            "closing_statement"
        ],
        description="Required sections in proposals"
    )
    custom_sections: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Custom sections specific to this company"
    )
    section_order: Optional[List[str]] = Field(
        None,
        description="Custom ordering of sections"
    )
    section_length_multipliers: Dict[str, float] = Field(
        default_factory=dict,
        description="Length multipliers for specific sections (e.g., {'why_us': 2.0})"
    )


class WritingPreferencesCreate(WritingPreferencesBase):
    """Schema for creating writing preferences."""
    pass


class WritingPreferencesUpdate(BaseModel):
    """Schema for updating writing preferences (all fields optional)."""

    tone_level: Optional[int] = Field(None, ge=1, le=5)
    brand_voice_tags: Optional[List[str]] = None
    language_complexity: Optional[str] = None
    company_jargon: Optional[str] = None
    must_include: Optional[List[str]] = None
    do_not_include: Optional[str] = None
    focus_areas: Optional[Dict[str, int]] = None
    required_sections: Optional[List[str]] = None
    custom_sections: Optional[List[Dict[str, str]]] = None
    section_order: Optional[List[str]] = None
    section_length_multipliers: Optional[Dict[str, float]] = None


class WritingPreferencesResponse(WritingPreferencesBase):
    """Schema for writing preferences response (includes id and timestamps)."""
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
