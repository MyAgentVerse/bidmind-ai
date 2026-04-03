"""AnalysisResult model storing AI-extracted intelligence from documents."""

from sqlalchemy import Column, String, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base import BaseModel


class AnalysisResult(BaseModel):
    """
    Model storing AI-extracted analysis of a procurement document.

    Contains structured intelligence extracted from the uploaded document:
    - Document type classification
    - Requirements extraction
    - Risk analysis
    - Deadline identification
    - Evaluation criteria
    - Budget clues
    - Strategic positioning suggestions
    """

    __tablename__ = "analysis_results"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Extracted fields
    document_type = Column(String(100), nullable=True)  # e.g., "RFP", "RFQ", "RFI"
    opportunity_summary = Column(Text, nullable=True)

    # JSON fields for structured data
    scope_of_work = Column(JSONB, nullable=True)  # List of work items
    mandatory_requirements = Column(JSONB, nullable=True)  # List of must-haves
    deadlines = Column(JSONB, nullable=True)  # Important dates
    evaluation_criteria = Column(JSONB, nullable=True)  # How vendor will be scored
    budget_clues = Column(JSONB, nullable=True)  # Budget-related information
    risks = Column(JSONB, nullable=True)  # Identified risks

    # Scoring and suggestions
    fit_score = Column(Float, nullable=True)  # 0-100 estimated fit
    usp_suggestions = Column(JSONB, nullable=True)  # List of unique selling propositions
    pricing_strategy_summary = Column(Text, nullable=True)  # Strategic pricing guidance

    # Raw AI response for debugging/auditing
    raw_ai_json = Column(JSONB, nullable=True)

    # Relationship
    project = relationship("Project", back_populates="analysis_result")

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, document_type={self.document_type}, fit_score={self.fit_score})>"
