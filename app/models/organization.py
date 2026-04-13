"""Organization model for multi-tenant SaaS."""

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.base import BaseModel


class Organization(BaseModel):
    """
    Organization model for multi-tenant architecture.

    Represents a company/workspace with multiple users and projects.
    """

    __tablename__ = "organizations"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Organization info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Subscription
    subscription_tier = Column(String(20), default="none", nullable=False)  # none, starter, pro
    subscription_status = Column(String(20), default="inactive", nullable=False)  # inactive, active, cancelled, past_due
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    stripe_subscription_id = Column(String(255), nullable=True)  # null for starter (one-time)
    subscription_started_at = Column(DateTime, nullable=True)
    subscription_ends_at = Column(DateTime, nullable=True)  # grace period for cancelled pro

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship(
        "UserOrganization",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    projects = relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    company_profile = relationship(
        "Company",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name})>"
        