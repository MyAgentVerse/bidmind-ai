"""
ProposalLearnings Model
Aggregated feedback analytics - what has the AI learned from feedback?
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import BaseModel


class ProposalLearnings(BaseModel):
    """
    Aggregated feedback analytics for each organization.
    Stores what the AI has learned from accumulated feedback.
    Updated whenever new feedback is received.
    """
    __tablename__ = "proposal_learnings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Total stats
    total_proposals_generated = Column(Integer, default=0)
    total_feedback_entries = Column(Integer, default=0)
    total_regenerations = Column(Integer, default=0)

    # Feedback ratings distribution
    love_count = Column(Integer, default=0)
    okay_count = Column(Integer, default=0)
    not_right_count = Column(Integer, default=0)

    # Common feedback issues (trending)
    # Example: {
    #   "pricing_high": 5,
    #   "timeline_aggressive": 3,
    #   "tone_formal": 2,
    #   "missing_case_studies": 1
    # }
    common_issues = Column(JSONB, nullable=True)

    # Learned preferences from feedback
    # Example: {
    #   "pricing_model": "value-based",
    #   "preferred_budget_min": 40000,
    #   "preferred_budget_max": 60000,
    #   "avg_timeline_weeks": 16,
    #   "tone_preference": "professional",
    #   "emphasis": ["compliance", "security", "support"],
    #   "avoid_mentioning": ["cost-plus", "aggressive timelines"]
    # }
    learned_preferences = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_feedback_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization")

    # Indexes
    __table_args__ = (
        Index('idx_org_learnings', 'organization_id'),
    )

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "total_proposals_generated": self.total_proposals_generated,
            "total_feedback_entries": self.total_feedback_entries,
            "total_regenerations": self.total_regenerations,
            "love_count": self.love_count,
            "okay_count": self.okay_count,
            "not_right_count": self.not_right_count,
            "common_issues": self.common_issues,
            "learned_preferences": self.learned_preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "last_feedback_at": self.last_feedback_at.isoformat() if self.last_feedback_at else None,
        }

    def get_avg_rating(self):
        """Calculate average rating (love=3, okay=2, not_right=1)"""
        total = self.love_count + self.okay_count + self.not_right_count
        if total == 0:
            return 0
        score = (self.love_count * 3) + (self.okay_count * 2) + (self.not_right_count * 1)
        return round(score / total, 2)

    def get_satisfaction_percentage(self):
        """Get percentage of positive feedback (love + okay)"""
        total = self.love_count + self.okay_count + self.not_right_count
        if total == 0:
            return 0
        return round(((self.love_count + self.okay_count) / total) * 100, 1)
