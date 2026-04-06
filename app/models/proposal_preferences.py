"""
ProposalPreferences Model
Stores organization-level proposal writing preferences and guidelines
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class ProposalPreferences(Base):
    """
    Organization-level proposal preferences.
    Stores all the settings from the Lovable Writing Preferences UI.
    """
    __tablename__ = "proposal_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)

    # === WRITING STYLE ===
    tone_level = Column(Integer, default=3)  # 1-5 slider for formality
    brand_voice_tags = Column(JSONB)  # ["trustworthy", "professional", "innovative", ...]
    language_complexity = Column(String)  # "simple", "standard", "technical"
    company_jargon = Column(Text)  # e.g., "CloudSync, Agile-First Delivery, Zero-Trust Architecture"

    # === CONTENT GUIDELINES ===
    must_include = Column(JSONB)  # ["compliance_certifications", "team_experience", ...]
    do_not_include = Column(Text)  # "Don't mention competitors, avoid technical jargon in executive summary"
    focus_areas = Column(JSONB)  # {
                                 #   "quality": 7,
                                 #   "price": 4,
                                 #   "innovation": 8,
                                 #   "support": 5,
                                 #   "timeline": 5,
                                 #   "risk_management": 5
                                 # }

    # === PROPOSAL STRUCTURE ===
    section_lengths = Column(JSONB)  # {
                                      #   "cover_letter": 1.0,
                                      #   "executive_summary": 1.0,
                                      #   "understanding_requirements": 1.0,
                                      #   "proposed_solution": 1.0,
                                      #   "why_us": 1.0,
                                      #   "pricing_positioning": 1.0,
                                      #   "risk_mitigation": 1.0,
                                      #   "closing_statement": 1.0
                                      # }
    custom_sections = Column(JSONB)  # [{name: "Case Studies", description: "..."}, ...]
    section_order = Column(JSONB)  # ["cover_letter", "executive_summary", ...]

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    organization = relationship("Organization")
    updated_by_user = relationship("User")

    # Indexes
    __table_args__ = (
        Index('idx_org_preferences', 'organization_id'),
    )

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "tone_level": self.tone_level,
            "brand_voice_tags": self.brand_voice_tags,
            "language_complexity": self.language_complexity,
            "company_jargon": self.company_jargon,
            "must_include": self.must_include,
            "do_not_include": self.do_not_include,
            "focus_areas": self.focus_areas,
            "section_lengths": self.section_lengths,
            "custom_sections": self.custom_sections,
            "section_order": self.section_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
