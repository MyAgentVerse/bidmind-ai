"""Pydantic models for LLM analysis output validation.

These models are the single source of truth for what the LLM must return
when analyzing a procurement document. They are used:

  - by ``AnalysisService`` to validate and coerce the LLM's JSON response
    (with retry-on-failure feeding the validation error back to the model)
  - by ``analysis_prompts.get_analysis_prompt`` to keep the prompt's JSON
    template in sync with the runtime schema
  - by ``app/schemas/analysis.py`` to derive the API response schema

Phase 1 Step C expands the schema from 11 fields to ~30, adding the
artifacts a real proposal team needs:

  - Eligibility / qualifications
  - Compliance matrix (each requirement with type, source, evidence)
  - Submission instructions (page limits, format, where to submit)
  - Required forms & attachments
  - Pricing format details
  - Past performance requirements
  - Key personnel requirements
  - Insurance & bonding requirements
  - Period & place of performance, contract type
  - NAICS codes, set-aside status
  - Contracting officer / buyer info
  - Federal/state clauses incorporated by reference
  - Wage determinations, protest procedures, funding source
  - Expanded Deadlines (Q&A, pre-bid conference, addenda, oral
    presentations, BAFO, award date) instead of the original 3 dates

The models are intentionally permissive at the parsing edges (string fit
scores, percent signs, dict-wrapped numbers, single string instead of
list, None instead of empty list) and strict at the type edges. This means
a slightly malformed but recoverable LLM response is coerced into a valid
object instead of triggering a retry.
"""

from typing import List, Optional, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------


class Deadlines(BaseModel):
    """Key dates extracted from a procurement document.

    Real RFPs have 8-12 distinct dates; the original 3-bucket schema lost
    most of them. This model captures the dates that actually drive a
    proposal team's calendar.
    """

    model_config = ConfigDict(extra="ignore")

    proposal_submission: Optional[str] = "Not specified"
    questions_due: Optional[str] = "Not specified"
    pre_bid_conference: Optional[str] = "Not specified"
    addenda_deadline: Optional[str] = "Not specified"
    oral_presentations: Optional[str] = "Not specified"
    bafo_deadline: Optional[str] = "Not specified"
    decision_date: Optional[str] = "Not specified"
    award_date: Optional[str] = "Not specified"
    contract_start: Optional[str] = "Not specified"


class BudgetClues(BaseModel):
    """Budget-related signals extracted from a procurement document."""

    model_config = ConfigDict(extra="ignore")

    estimated_budget: Optional[str] = "Not specified"
    pricing_model: Optional[str] = "Not specified"
    notes: Optional[str] = ""


class ContractingOfficer(BaseModel):
    """Buyer / contracting officer contact info, when present in the document."""

    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    title: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class ComplianceRequirement(BaseModel):
    """A single row in the compliance matrix.

    The compliance matrix is the most important new artifact in Step C.
    Every requirement extracted from the bid package becomes one of these,
    so the proposal team can later answer 'did we address requirement #14?'
    and 'where did this requirement come from?'.
    """

    model_config = ConfigDict(extra="ignore")

    requirement_id: Optional[str] = None  # e.g., "REQ-01" or "L.4.2.1"
    requirement_text: str
    requirement_type: Optional[str] = "must"  # must / should / may / informational
    category: Optional[str] = None  # e.g., "technical", "management", "pricing", "past_performance"
    source_file: Optional[str] = None  # which uploaded file this came from
    source_section: Optional[str] = None  # e.g., "Section L.4.2"
    source_page: Optional[int] = None  # PDF page number if known
    evidence_required: Optional[str] = None  # what proof the buyer wants
    notes: Optional[str] = None

    @field_validator("requirement_type", mode="before")
    @classmethod
    def _coerce_type(cls, v: Any) -> Optional[str]:
        if v is None:
            return "must"
        s = str(v).strip().lower()
        # Normalize common variants
        if s in ("shall", "must", "required", "mandatory"):
            return "must"
        if s in ("should", "recommended", "preferred"):
            return "should"
        if s in ("may", "optional"):
            return "may"
        if s in ("informational", "info", "fyi"):
            return "informational"
        return s or "must"

    @field_validator("source_page", mode="before")
    @classmethod
    def _coerce_page(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


class SubmissionInstructions(BaseModel):
    """How the proposal must be packaged and submitted."""

    model_config = ConfigDict(extra="ignore")

    delivery_method: Optional[str] = None  # e.g., "Electronic via SAM.gov", "Email"
    delivery_address: Optional[str] = None
    file_format: Optional[str] = None  # e.g., "PDF only"
    page_limit: Optional[str] = None  # e.g., "50 pages excluding appendices"
    font_requirements: Optional[str] = None  # e.g., "Times New Roman 12pt"
    margin_requirements: Optional[str] = None
    naming_convention: Optional[str] = None
    number_of_copies: Optional[str] = None
    required_sections: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class PricingFormat(BaseModel):
    """How the buyer wants pricing structured in the response."""

    model_config = ConfigDict(extra="ignore")

    pricing_template: Optional[str] = None  # e.g., "Attachment B - Pricing Worksheet"
    line_item_structure: Optional[str] = None  # e.g., "CLINs", "labor categories", "deliverables"
    pricing_basis: Optional[str] = None  # e.g., "FFP", "T&M", "CPFF", "IDIQ"
    discount_requirements: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class KeyPersonnelRequirement(BaseModel):
    """A required role on the proposed team."""

    model_config = ConfigDict(extra="ignore")

    role: str
    required_certifications: List[str] = Field(default_factory=list)
    required_clearance: Optional[str] = None  # e.g., "Secret", "Top Secret/SCI"
    minimum_experience_years: Optional[int] = None
    education_requirements: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("required_certifications", mode="before")
    @classmethod
    def _coerce_certs(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(c).strip() for c in v if c and str(c).strip()]
        return []

    @field_validator("minimum_experience_years", mode="before")
    @classmethod
    def _coerce_years(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return None
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None


class PastPerformanceRequirements(BaseModel):
    """What the buyer wants to see in the past-performance section."""

    model_config = ConfigDict(extra="ignore")

    minimum_references: Optional[int] = None
    recency_window_years: Optional[int] = None  # e.g., "within the last 5 years"
    minimum_contract_value: Optional[str] = None
    similar_scope_required: Optional[bool] = None
    similar_size_required: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("minimum_references", "recency_window_years", mode="before")
    @classmethod
    def _coerce_int(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return None
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None


class InsuranceRequirements(BaseModel):
    """Insurance, bonding, and liability requirements."""

    model_config = ConfigDict(extra="ignore")

    general_liability: Optional[str] = None  # e.g., "$1M per occurrence"
    professional_liability: Optional[str] = None
    workers_comp: Optional[str] = None
    cyber_liability: Optional[str] = None
    payment_bond: Optional[str] = None  # e.g., "100% of contract value"
    performance_bond: Optional[str] = None
    bid_bond: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Top-level extraction model
# ---------------------------------------------------------------------------


class AnalysisExtraction(BaseModel):
    """The structured intelligence the LLM must produce for a bid package.

    This is the contract between the prompt and the database. The
    ``AnalysisResult`` ORM model stores most of these fields in their own
    columns; less-queryable fields are stored in the existing JSONB
    ``raw_ai_json`` column.
    """

    model_config = ConfigDict(extra="ignore")

    # ---- Core (Phase 1 Step B fields) ---------------------------------
    document_type: str = Field(
        default="UNKNOWN",
        description="Document classification (RFP, RFQ, RFI, SOW, IFB, etc.)",
    )
    opportunity_summary: str = Field(
        default="",
        description="2-3 sentence high-level summary of what is being sought",
    )
    scope_of_work: List[str] = Field(default_factory=list)
    mandatory_requirements: List[str] = Field(default_factory=list)
    deadlines: Deadlines = Field(default_factory=Deadlines)
    evaluation_criteria: List[str] = Field(default_factory=list)
    budget_clues: BudgetClues = Field(default_factory=BudgetClues)
    risks: List[str] = Field(default_factory=list)
    fit_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="0-100 estimated fit assessment",
    )
    usp_suggestions: List[str] = Field(default_factory=list)
    pricing_strategy_summary: str = ""

    # ---- New in Step C (queryable / get their own DB column) ----------
    eligibility_requirements: List[str] = Field(
        default_factory=list,
        description="Hard go/no-go gates: certifications, citizenship, set-asides, etc.",
    )
    compliance_matrix: List[ComplianceRequirement] = Field(
        default_factory=list,
        description="Every extracted requirement with type, source, and evidence needed.",
    )
    submission_instructions: SubmissionInstructions = Field(
        default_factory=SubmissionInstructions
    )
    pricing_format: PricingFormat = Field(default_factory=PricingFormat)
    key_personnel_requirements: List[KeyPersonnelRequirement] = Field(
        default_factory=list
    )
    naics_codes: List[str] = Field(default_factory=list)
    set_aside_status: Optional[str] = None  # e.g., "8(a)", "SDVOSB", "WOSB", "HUBZone", "Full and Open"
    contract_type: Optional[str] = None  # e.g., "FFP", "T&M", "IDIQ", "CPFF"
    period_of_performance: Optional[str] = None
    place_of_performance: Optional[str] = None
    estimated_value: Optional[str] = None
    contracting_officer: ContractingOfficer = Field(default_factory=ContractingOfficer)

    # ---- New in Step C (stored in raw_ai_json, no DB column) ----------
    required_forms: List[str] = Field(
        default_factory=list,
        description="SF-33, reps & certs, lobbying certification, etc.",
    )
    past_performance_requirements: PastPerformanceRequirements = Field(
        default_factory=PastPerformanceRequirements
    )
    insurance_requirements: InsuranceRequirements = Field(
        default_factory=InsuranceRequirements
    )
    clauses_by_reference: List[str] = Field(
        default_factory=list,
        description="FAR, DFARS, agency-specific clauses incorporated by reference.",
    )
    wage_determinations: Optional[str] = None  # Davis-Bacon, SCA, etc.
    protest_procedures: Optional[str] = None
    funding_source: Optional[str] = None  # appropriated, grant, federal pass-through, etc.

    # ---- Coercers for sloppy LLM output ---------------------------------
    #
    # The LLM occasionally returns:
    #   - "85" or "85%" or "0.85" instead of 85
    #   - {"score": 85} instead of 85
    #   - null where we expect a list
    #   - a single string where we expect a list of strings
    # These validators catch the common cases so we don't waste a retry on
    # something we can fix locally.

    @field_validator("fit_score", mode="before")
    @classmethod
    def _coerce_fit_score(cls, v: Any) -> float:
        if v is None:
            return 0.0

        if isinstance(v, dict):
            for key in ("score", "value", "fit_score", "rating"):
                if key in v:
                    return cls._coerce_fit_score(v[key])
            return 0.0

        if isinstance(v, bool):
            # bool is a subclass of int — guard against accidental truthiness.
            return 100.0 if v else 0.0

        if isinstance(v, (int, float)):
            num = float(v)
        elif isinstance(v, str):
            cleaned = v.strip().rstrip("%").strip()
            try:
                num = float(cleaned)
            except ValueError:
                return 0.0
        else:
            return 0.0

        # 0-1 normalization heuristic. Strict bounds: exactly 0 means "no
        # fit" and exactly 1 means "1% fit", both kept as-is.
        if 0.0 < num < 1.0:
            num *= 100.0

        return num

    @field_validator(
        "scope_of_work",
        "mandatory_requirements",
        "evaluation_criteria",
        "risks",
        "usp_suggestions",
        "eligibility_requirements",
        "naics_codes",
        "required_forms",
        "clauses_by_reference",
        mode="before",
    )
    @classmethod
    def _coerce_string_list(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [
                str(item).strip()
                for item in v
                if item is not None and str(item).strip()
            ]
        return [str(v)]

    @field_validator("deadlines", mode="before")
    @classmethod
    def _coerce_deadlines(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v

    @field_validator("budget_clues", mode="before")
    @classmethod
    def _coerce_budget_clues(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v

    @field_validator("contracting_officer", mode="before")
    @classmethod
    def _coerce_contracting_officer(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v

    @field_validator("submission_instructions", mode="before")
    @classmethod
    def _coerce_submission_instructions(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v

    @field_validator("pricing_format", mode="before")
    @classmethod
    def _coerce_pricing_format(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v

    @field_validator("past_performance_requirements", mode="before")
    @classmethod
    def _coerce_past_performance(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v

    @field_validator("insurance_requirements", mode="before")
    @classmethod
    def _coerce_insurance(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v

    @field_validator("compliance_matrix", mode="before")
    @classmethod
    def _coerce_compliance_matrix(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, list):
            # Drop entries that aren't dicts or that lack a requirement_text
            cleaned = []
            for item in v:
                if isinstance(item, dict):
                    cleaned.append(item)
                elif isinstance(item, str) and item.strip():
                    # Lift a bare string into a minimal requirement
                    cleaned.append({"requirement_text": item.strip()})
            return cleaned
        return []

    @field_validator("key_personnel_requirements", mode="before")
    @classmethod
    def _coerce_key_personnel(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, list):
            cleaned = []
            for item in v:
                if isinstance(item, dict):
                    cleaned.append(item)
                elif isinstance(item, str) and item.strip():
                    cleaned.append({"role": item.strip()})
            return cleaned
        return []
