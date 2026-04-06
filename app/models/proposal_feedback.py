"""
ProposalFeedback Model
Stores user feedback on generated proposals
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class ProposalFeedback(BaseModel):
    """
    Stores feedback from users on AI-generated proposals.
    This is the core of the feedback loop for AI learning.
    """
    __tablename__ = "proposal_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("proposal_generations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Feedback content
    rating = Column(String, nullable=False)  # "love", "okay", "not_right"
    feedback_text = Column(Text, nullable=True)

    # Feedback tags (user can select multiple)
    feedback_tags = Column(JSONB, nullable=True)

    # Action taken with feedback
    action_taken = Column(String, nullable=True)  # "saved", "regenerated", "ignored"
    regenerated_proposal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("proposal_generations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Metadata
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    proposal = relationship(
        "ProposalGeneration",
        foreign_keys=[proposal_id],
        back_populates="feedback",
    )
    regenerated_proposal = relationship(
        "ProposalGeneration",
        foreign_keys=[regenerated_proposal_id],
    )
    created_by_user = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_proposal_feedback", "proposal_id"),
        Index("idx_org_feedback", "organization_id", "created_at"),
        Index("idx_feedback_created_by", "created_by"),
    )

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "proposal_id": str(self.proposal_id),
            "rating": self.rating,
            "feedback_text": self.feedback_text,
            "feedback_tags": self.feedback_tags,
            "action_taken": self.action_taken,
            "regenerated_proposal_id": str(self.regenerated_proposal_id) if self.regenerated_proposal_id else None,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        