"""Company writing preferences model for customizing proposal generation."""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime
import uuid

from app.db.base import BaseModel


class CompanyWritingPreferences(BaseModel):
    """
    Company writing preferences for customizing proposal generation and content guidelines.

    Stores writing style preferences, content guidelines, and proposal structure customizations.
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
        index=True
    )

    # WRITING STYLE SECTION
    # Tone level: 1 (Casual) to 5 (Very Formal)
    tone_level = Column(Integer, default=3, nullable=False, comment="1=Casual, 5=Very Formal")

    # Brand voice tags (stored as JSON array)
    # Examples: "Trustworthy", "Innovative", "Professional", "Friendly", "Technical"
    brand_voice_tags = Column(
        JSON,
        default=list,
        nullable=False,
        comment="Multi-select tags: Trustworthy, Innovative, Professional, Friendly, Technical, etc."
    )

    # Language complexity: simple, standard, technical
    language_complexity = Column(
        String(20),
        default="standard",
        nullable=False,
        comment="simple | standard | technical"
    )

    # Company jargon and terminology
    company_jargon = Column(
        Text,
        nullable=True,
        comment="Custom words/phrases the company uses (e.g., 'enterprise solutions' not 'products')"
    )

    # CONTENT GUIDELINES SECTION
    # Must include items (stored as JSON array)
    must_include = Column(
        JSON,
        default=list,
        nullable=False,
        comment="Checkboxes: mention compliance certs, highlight team exp, include case studies, etc."
    )

    # Do not include (text area)
    do_not_include = Column(
        Text,
        nullable=True,
        comment="Things to avoid: don't mention competitors, avoid pricing details, etc."
    )

    # Focus areas with weights (stored as JSON dict)
    # Example: {"quality": 8, "price": 5, "innovation": 9, "support": 7}
    focus_areas = Column(
        JSON,
        default=dict,
        nullable=False,
        comment="Weighted focus areas: quality, price, innovation, support (1-10 scale)"
    )

    # PROPOSAL STRUCTURE SECTION
    # Required sections (stored as JSON array)
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
            "closing_statement"
        ],
        nullable=False,
        comment="Default 8 sections, can be customized"
    )

    # Custom sections (stored as JSON array)
    # Example: [{"name": "Team Resumes", "description": "Detailed team member backgrounds"}]
    custom_sections = Column(
        JSON,
        default=list,
        nullable=False,
        comment="Custom sections specific to this company"
    )

    # Section order (stored as JSON array with section names in desired order)
    section_order = Column(
        JSON,
        nullable=True,
        comment="Reorder default sections, e.g., ['executive_summary', 'why_us', 'proposed_solution', ...]"
    )

    # Section length preferences (stored as JSON dict)
    # Example: {"why_us": 2.0} means make Why Us section 2x longer than default
    section_length_multipliers = Column(
        JSON,
        default=dict,
        nullable=False,
        comment="Length multipliers: {'why_us': 2.0, 'pricing_positioning': 1.5}"
    )

    # TIMESTAMPS
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # RELATIONSHIPS
    company = relationship(
        "Company",
        backref="writing_preferences",
        uselist=False,
        foreign_keys=[company_id]
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
