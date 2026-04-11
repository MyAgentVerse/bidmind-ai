"""Analysis-related schemas."""

from pydantic import BaseModel, Field
from typing import Optional, Any, List, ClassVar, Tuple
from datetime import datetime
from uuid import UUID


class AnalysisResponse(BaseModel):
    """Schema for analysis result response.

    Phase 1 Step C added the new fields below the original 11 — they all
    default to None so old analysis records (created before the migration
    ran) still serialize cleanly.
    """

    id: UUID
    project_id: UUID

    # ---- Core fields (Phase 1 Step B) ---------------------------------
    document_type: Optional[str] = None
    opportunity_summary: Optional[str] = None
    scope_of_work: Optional[Any] = None
    mandatory_requirements: Optional[Any] = None
    deadlines: Optional[Any] = None
    evaluation_criteria: Optional[Any] = None
    budget_clues: Optional[Any] = None
    risks: Optional[Any] = None
    fit_score: Optional[float] = None
    usp_suggestions: Optional[Any] = None
    pricing_strategy_summary: Optional[str] = None

    # ---- New in Step C (dedicated columns) ----------------------------
    eligibility_requirements: Optional[Any] = None
    compliance_matrix: Optional[Any] = None
    submission_instructions: Optional[Any] = None
    pricing_format: Optional[Any] = None
    key_personnel_requirements: Optional[Any] = None
    naics_codes: Optional[Any] = None
    set_aside_status: Optional[str] = None
    contract_type: Optional[str] = None
    period_of_performance: Optional[str] = None
    place_of_performance: Optional[str] = None
    estimated_value: Optional[str] = None
    contracting_officer: Optional[Any] = None

    # ---- New in Step C (lifted from raw_ai_json for the response) -----
    required_forms: Optional[Any] = None
    past_performance_requirements: Optional[Any] = None
    insurance_requirements: Optional[Any] = None
    clauses_by_reference: Optional[Any] = None
    wage_determinations: Optional[str] = None
    protest_procedures: Optional[str] = None
    funding_source: Optional[str] = None

    # ---- Provenance ---------------------------------------------------
    source_files: Optional[List[str]] = Field(
        default=None,
        description="Filenames included in this multi-document analysis.",
    )

    created_at: datetime
    updated_at: datetime

    # Fields that live inside raw_ai_json rather than in their own column.
    # `from_analysis_result` lifts them up so the API response is flat.
    # ClassVar so Pydantic v2 doesn't treat the leading-underscore name as
    # a private attribute (which would make it non-iterable on the class).
    _LIFTED_FROM_RAW_AI_JSON: ClassVar[Tuple[str, ...]] = (
        "required_forms",
        "past_performance_requirements",
        "insurance_requirements",
        "clauses_by_reference",
        "wage_determinations",
        "protest_procedures",
        "funding_source",
    )

    @classmethod
    def from_analysis_result(cls, analysis_result) -> "AnalysisResponse":
        """Build a response from an ``AnalysisResult`` ORM object.

        Step C added many new fields. The queryable ones (compliance_matrix,
        eligibility_requirements, naics_codes, set_aside_status, etc.) have
        their own ORM columns and serialize via the normal ``from_orm`` path.

        The less-queryable ones (required_forms, insurance_requirements,
        wage_determinations, etc.) are stored inside the existing JSONB
        ``raw_ai_json`` column to keep the table width manageable. This
        helper lifts them out of ``raw_ai_json`` so the API response is
        flat instead of forcing the frontend to dig into a nested blob.

        It also exposes the multi-document provenance: the Step 2 file
        list is stored under the ``_source_files`` key inside
        ``raw_ai_json``; we surface it as ``source_files``.
        """
        base = cls.from_orm(analysis_result).model_dump()
        raw = getattr(analysis_result, "raw_ai_json", None) or {}

        if isinstance(raw, dict):
            for field in cls._LIFTED_FROM_RAW_AI_JSON:
                if base.get(field) is None:
                    base[field] = raw.get(field)

            if not base.get("source_files") and "_source_files" in raw:
                base["source_files"] = raw["_source_files"]

        return cls(**base)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_type": "RFP",
                "opportunity_summary": "Enterprise-wide cloud infrastructure modernization",
                "scope_of_work": ["Infrastructure setup", "Migration support"],
                "mandatory_requirements": ["ISO 27001 certified", "24/7 support"],
                "deadlines": {
                    "proposal_submission": "2026-05-21",
                    "questions_due": "2026-05-01",
                    "pre_bid_conference": "2026-04-25",
                    "addenda_deadline": "2026-05-10",
                    "decision_date": "2026-06-15",
                    "award_date": "2026-07-01",
                    "contract_start": "2026-08-01",
                },
                "evaluation_criteria": ["Technical 60%", "Past Performance 20%", "Price 20%"],
                "budget_clues": {
                    "estimated_budget": "$5M-$10M",
                    "pricing_model": "FFP",
                    "notes": "Phased payments tied to milestones",
                },
                "risks": ["Tight timeline", "Complex legacy system"],
                "fit_score": 85.5,
                "usp_suggestions": ["Proven migration experience", "Cost optimization"],
                "pricing_strategy_summary": "Value-based pricing with performance guarantees",
                "eligibility_requirements": [
                    "Active SAM.gov registration",
                    "SOC 2 Type II",
                    "FedRAMP Moderate authorized",
                ],
                "compliance_matrix": [
                    {
                        "requirement_id": "L.4.2.1",
                        "requirement_text": "Vendor must provide 24/7 on-call support",
                        "requirement_type": "must",
                        "category": "technical",
                        "source_file": "main_rfp.pdf",
                        "source_section": "Section L.4.2",
                        "source_page": 23,
                        "evidence_required": "Sample SLA + on-call rotation diagram",
                    }
                ],
                "submission_instructions": {
                    "delivery_method": "Electronic via SAM.gov",
                    "file_format": "PDF only",
                    "page_limit": "50 pages excluding appendices",
                    "font_requirements": "Times New Roman 12pt",
                    "required_sections": [
                        "Technical Volume",
                        "Past Performance Volume",
                        "Cost Volume",
                    ],
                },
                "pricing_format": {
                    "pricing_template": "Attachment B - Pricing Worksheet",
                    "line_item_structure": "CLINs",
                    "pricing_basis": "FFP",
                    "payment_terms": "Net 30 from acceptance",
                },
                "key_personnel_requirements": [
                    {
                        "role": "Program Manager",
                        "required_certifications": ["PMP"],
                        "required_clearance": "Secret",
                        "minimum_experience_years": 10,
                    }
                ],
                "naics_codes": ["541512", "541519"],
                "set_aside_status": "SDVOSB",
                "contract_type": "FFP",
                "period_of_performance": "5 years base + 5 option years",
                "place_of_performance": "Washington, DC",
                "estimated_value": "$5M-$10M",
                "contracting_officer": {
                    "name": "Jane Doe",
                    "email": "jane.doe@agency.gov",
                    "phone": "202-555-0100",
                },
                "source_files": ["main_rfp.pdf", "addendum_1.pdf", "pricing_template.xlsx"],
                "created_at": "2026-04-11T10:30:00",
                "updated_at": "2026-04-11T10:30:00",
            }
        }
