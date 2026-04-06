"""Company writing preferences model for customizing proposal generation."""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.base import BaseModel


class CompanyWritingPreferences(BaseModel):
    """
    Company writing preferences for customizing proposal generation and content guidelines.

    One-to-one relationship with Company model.
    """

    __tablename__ = "company_writing_preferences"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key to company
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # WRITING STYLE SECTION
    tone_level = Column(Integer, default=3, nullable=False, comment="1=Casual, 5=Very Formal")

    brand_voice_tags = Column(
        JSON,
        default=list,
        nullable=False,
        comment="Multi-select tags: Trustworthy, Innovative, Professional, Friendly, Technical, etc.",
    )

    language_complexity = Column(
        String(20),
        default="standard",
        nullable=False,
        comment="simple | standard | technical",
    )

    company_jargon = Column(
        Text,
        nullable=True,
        comment="Custom words/phrases the company uses",
    )

    # CONTENT GUIDELINES SECTION
    must_include = Column(
        JSON,
        default=list,
        nullable=False,
        comment="Items that must be included in proposals",
    )

    do_not_include = Column(
        Text,
        nullable=True,
        comment="Things to avoid or exclude from proposals",
    )

    focus_areas = Column(
        JSON,
        default=dict,
        nullable=False,
        comment="Weighted focus areas with 1-10 scale",
    )

    # PROPOSAL STRUCTURE SECTION
    required_sections = Column(
        JSON,
        default=lambda: [
            "cover_letter",
            "executive_summary",
            "understanding_of_requirements",
            "proposed_solution",
            "why_us",
            "pricing_positioning",
            "risk_mitigation",
            "closing_statement",
        ],
        nullable=False,
        comment="Required sections in proposals",
    )

    custom_sections = Column(
        JSON,
        default=list,
        nullable=False,
        comment="Custom sections specific to this company",
    )

    section_order = Column(
        JSON,
        nullable=True,
        comment="Custom ordering of sections",
    )

    section_length_multipliers = Column(
        JSON,
        default=dict,
        nullable=False,
        comment="Length multipliers for specific sections",
    )

    # TIMESTAMPS
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # RELATIONSHIPS
    company = relationship(
        "Company",
        back_populates="writing_preferences",
        uselist=False,
        foreign_keys=[company_id],
    )

    def __repr__(self):
        return f"<CompanyWritingPreferences(id={self.id}, company_id={self.company_id})>"

    def to_dict(self) -> dict:
        """Convert preferences to dictionary for use in prompts."""
        return {
            "tone_level": self.tone_level,
            "brand_voice_tags": self.brand_voice_tags,
            "language_complexity": self.language_complexity,
            "company_jargon": self.company_jargon,
            "must_include": self.must_include,
            "do_not_include": self.do_not_include,
            "focus_areas": self.focus_areas,
            "required_sections": self.required_sections,
            "custom_sections": self.custom_sections,
            "section_order": self.section_order,
            "section_length_multipliers": self.section_length_multipliers,
        }
        