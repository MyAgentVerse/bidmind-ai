"""Usage tracking for subscription tier enforcement."""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import BaseModel


class UsageRecord(BaseModel):
    """
    Tracks monthly usage per organization for enforcing tier limits.

    Keyed by (organization_id, usage_type, period_start) so each month
    gets a fresh row — no cron needed for resets.
    """

    __tablename__ = "usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usage_type = Column(String(50), nullable=False)  # proposal_generated, project_created
    period_start = Column(DateTime, nullable=False)  # 1st of the month UTC
    count = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "usage_type", "period_start",
            name="uq_usage_org_type_period",
        ),
    )

    def __repr__(self):
        return f"<UsageRecord(org={self.organization_id}, type={self.usage_type}, count={self.count})>"
