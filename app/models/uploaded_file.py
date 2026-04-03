"""UploadedFile model representing uploaded procurement documents."""

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import BaseModel


class UploadedFile(BaseModel):
    """
    Model representing an uploaded procurement document.

    Stores:
    - File metadata (name, path, size, type)
    - Extracted text content
    - Reference to parent project
    """

    __tablename__ = "uploaded_files"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # File metadata
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True, index=True)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(255), nullable=False)  # e.g., "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    file_size = Column(Integer, nullable=False)  # In bytes

    # Extracted content
    extracted_text = Column(Text, nullable=True)

    # Relationship
    project = relationship("Project", back_populates="uploaded_files")

    def __repr__(self):
        return f"<UploadedFile(id={self.id}, filename={self.original_filename}, size={self.file_size})>"
