"""AnalysisResult model storing AI-extracted intelligence from documents."""

from sqlalchemy import Column, String, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base import BaseModel


class AnalysisResult(BaseModel):
    """
    Model storing AI-extracted analysis of a procurement document or
    multi-file bid package.

    Phase 1 Step C expanded this from 11 fields to ~25, adding the
    artifacts a real proposal team needs:

      - Compliance matrix (every requirement with type, source, evidence)
      - Eligibility / qualifications (go/no-go gates)
      - Submission instructions (page limits, format, where to submit)
      - Pricing format (CLINs, line items, basis)
      - Key personnel requirements
      - NAICS codes, set-aside status, contract type
      - Period & place of performance, estimated value
      - Contracting officer / buyer info

    Less-queryable fields (insurance, required forms, clauses by reference,
    wage determinations, protest procedures, funding source, past
    performance requirements) are stored inside ``raw_ai_json`` to keep
    the table width manageable. They can still be read from the API.
    """

    __tablename__ = "analysis_results"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # ---- Core fields (from Phase 1 Step B) -----------------------------
    document_type = Column(String(100), nullable=True)  # e.g., "RFP", "RFQ", "RFI"
    opportunity_summary = Column(Text, nullable=True)
    scope_of_work = Column(JSONB, nullable=True)
    mandatory_requirements = Column(JSONB, nullable=True)
    deadlines = Column(JSONB, nullable=True)
    evaluation_criteria = Column(JSONB, nullable=True)
    budget_clues = Column(JSONB, nullable=True)
    risks = Column(JSONB, nullable=True)
    fit_score = Column(Float, nullable=True)
    usp_suggestions = Column(JSONB, nullable=True)
    pricing_strategy_summary = Column(Text, nullable=True)

    # ---- New in Step C (queryable / get their own column) -------------
    eligibility_requirements = Column(JSONB, nullable=True)
    compliance_matrix = Column(JSONB, nullable=True)  # The killer feature
    submission_instructions = Column(JSONB, nullable=True)
    pricing_format = Column(JSONB, nullable=True)
    key_personnel_requirements = Column(JSONB, nullable=True)
    naics_codes = Column(JSONB, nullable=True)  # List of strings
    set_aside_status = Column(String(100), nullable=True, index=True)
    contract_type = Column(String(100), nullable=True, index=True)
    period_of_performance = Column(String(255), nullable=True)
    place_of_performance = Column(String(255), nullable=True)
    estimated_value = Column(String(100), nullable=True)
    contracting_officer = Column(JSONB, nullable=True)

    # Raw AI response for debugging/auditing.
    # Step C also uses this to store the less-queryable extracted fields:
    #   _source_files, required_forms, past_performance_requirements,
    #   insurance_requirements, clauses_by_reference, wage_determinations,
    #   protest_procedures, funding_source
    raw_ai_json = Column(JSONB, nullable=True)

    # Relationship
    project = relationship("Project", back_populates="analysis_result")

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, document_type={self.document_type}, fit_score={self.fit_score})>"
