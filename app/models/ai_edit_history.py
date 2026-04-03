"""AIEditHistory model tracking AI-assisted edits to proposal sections."""

from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import BaseModel


class AIEditHistory(BaseModel):
    """
    Model tracking history of AI-assisted edits to proposal sections.

    Allows users to see what changes were made and potentially revert them.
    """

    __tablename__ = "ai_edit_history"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Edit details
    section_name = Column(String(100), nullable=False)  # e.g., "executive_summary"
    instruction = Column(Text, nullable=False)  # The user's edit instruction
    original_text = Column(Text, nullable=False)  # Original section text
    edited_text = Column(Text, nullable=False)  # Result after AI edit

    # Relationship
    project = relationship("Project", back_populates="ai_edit_history")

    def __repr__(self):
        return f"<AIEditHistory(id={self.id}, section={self.section_name}, project={self.project_id})>"
