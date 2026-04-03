"""Company model representing a bidding company profile."""

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.base import BaseModel


class Company(BaseModel):
    """
    Company model storing company profile information used for personalized proposals.

    Stores:
    - Company name and description
    - Unique Selling Proposition (USP)
    - Key capabilities and strengths
    - Industry focus and experience
    - Used by AI to generate fit scores and personalized proposals
    """

    __tablename__ = "companies"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Company info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)  # Brief company overview

    # USP and capabilities
    unique_selling_proposition = Column(
        Text,
        nullable=True,
        comment="What makes this company unique and different from competitors"
    )
    key_capabilities = Column(
        Text,
        nullable=True,
        comment="Core strengths, services, and what company can deliver"
    )
    experience = Column(
        Text,
        nullable=True,
        comment="Years of experience, past successes, relevant projects"
    )
    industry_focus = Column(
        Text,
        nullable=True,
        comment="Industries and sectors the company specializes in"
    )

    # Relationships
    projects = relationship(
        "Project",
        back_populates="company"
    )

    def __repr__(self):
        return f"<Company(id={self.id}, name={self.name})>"
