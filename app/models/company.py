"""Company model representing an organization-owned company profile."""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.base import BaseModel


class Company(BaseModel):
    """
    Company profile tied to exactly one organization.

    This is tenant-safe:
    - one organization owns one company profile
    - company profile is never global
    """

    __tablename__ = "companies"

    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_companies_organization_id"),
    )

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Organization ownership (tenant boundary)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )

    # Company info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # USP and capabilities
    unique_selling_proposition = Column(
        Text,
        nullable=True,
        comment="What makes this company unique and different from competitors",
    )
    key_capabilities = Column(
        Text,
        nullable=True,
        comment="Core strengths, services, and what company can deliver",
    )
    experience = Column(
        Text,
        nullable=True,
        comment="Years of experience, past successes, relevant projects",
    )
    industry_focus = Column(
        Text,
        nullable=True,
        comment="Industries and sectors the company specializes in",
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship(
        "Organization",
        back_populates="company_profile",
        foreign_keys=[organization_id],
    )

    projects = relationship(
        "Project",
        back_populates="company",
        foreign_keys="Project.company_id",
    )

    writing_preferences = relationship(
        "CompanyWritingPreferences",
        back_populates="company",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Company(id={self.id}, organization_id={self.organization_id}, name={self.name})>"
        