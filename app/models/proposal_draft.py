"""ProposalDraft model storing generated proposal sections."""

from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import BaseModel


class ProposalDraft(BaseModel):
    """
    Model storing the generated proposal draft with all sections.

    Contains all sections of the proposal that can be edited by users:
    - Cover Letter
    - Executive Summary
    - Understanding of Requirements
    - Proposed Solution
    - Why Us
    - Pricing Positioning
    - Risk Mitigation
    - Closing Statement
    """

    __tablename__ = "proposal_drafts"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True, index=True)

    # Proposal sections
    cover_letter = Column(Text, nullable=True)
    executive_summary = Column(Text, nullable=True)
    understanding_of_requirements = Column(Text, nullable=True)
    proposed_solution = Column(Text, nullable=True)
    why_us = Column(Text, nullable=True)
    pricing_positioning = Column(Text, nullable=True)
    risk_mitigation = Column(Text, nullable=True)
    closing_statement = Column(Text, nullable=True)

    # Relationship
    project = relationship("Project", back_populates="proposal_draft")

    # Section order for frontend rendering
    SECTION_ORDER = [
        "cover_letter",
        "executive_summary",
        "understanding_of_requirements",
        "proposed_solution",
        "why_us",
        "pricing_positioning",
        "risk_mitigation",
        "closing_statement",
    ]

    SECTION_TITLES = {
        "cover_letter": "Cover Letter",
        "executive_summary": "Executive Summary",
        "understanding_of_requirements": "Understanding of Requirements",
        "proposed_solution": "Proposed Solution / Approach",
        "why_us": "Why Us",
        "pricing_positioning": "Pricing Positioning",
        "risk_mitigation": "Risk Mitigation",
        "closing_statement": "Closing Statement",
    }

    def to_dict(self):
        """Convert proposal to dictionary with ordered sections."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sections": {
                section: getattr(self, section)
                for section in self.SECTION_ORDER
            }
        }

    def __repr__(self):
        return f"<ProposalDraft(id={self.id}, project_id={self.project_id})>"
