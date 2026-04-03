"""Project model representing a bidding opportunity project."""

from sqlalchemy import Column, String, Enum, DateTime
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
    status = Column(
        Enum(ProjectStatus),
        default=ProjectStatus.CREATED,
        nullable=False,
        index=True
    )

    # Relationships
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
