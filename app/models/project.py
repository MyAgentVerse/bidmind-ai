"""Project model representing a bidding opportunity project."""

from sqlalchemy import Column, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.db.base import BaseModel


class ProjectStatus(str, enum.Enum):
    """Project workflow status."""
    CREATED = "created"
    FILE_UPLOADED = "file_uploaded"
    ANALYZED = "analyzed"
    PROPOSAL_GENERATED = "proposal_generated"


class Project(BaseModel):
    """
    Project model representing a single bidding opportunity.

    A project contains:
    - Uploaded procurement document
    - Analysis results
    - Generated proposal draft
    - Edit history
    """

    __tablename__ = "projects"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Fields
    title = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    # values_callable tells SQLAlchemy to use the .value attributes
    # (lowercase: "created", "file_uploaded", etc.) for matching against
    # the Postgres native enum, instead of the default .name attributes
    # (UPPERCASE: "CREATED", "FILE_UPLOADED", etc.). The Postgres enum
    # was originally created with lowercase values, so without this fix,
    # every Project ORM query crashes with:
    #   "'created' is not among the defined enum values"
    status = Column(
        Enum(
            ProjectStatus,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ProjectStatus.CREATED,
        nullable=False,
        index=True
    )

    # Foreign keys
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)

    # Relationships
    company = relationship(
        "Company",
        back_populates="projects",
        foreign_keys=[company_id]
    )
    organization = relationship(
        "Organization",
        back_populates="projects",
        foreign_keys=[organization_id]
    )
    uploaded_files = relationship(
        "UploadedFile",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    analysis_result = relationship(
        "AnalysisResult",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    proposal_draft = relationship(
        "ProposalDraft",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    ai_edit_history = relationship(
        "AIEditHistory",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(id={self.id}, title={self.title}, status={self.status})>"
