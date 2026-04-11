"""Pydantic models for LLM analysis output validation.

These models are the single source of truth for what the LLM must return
when analyzing a procurement document. They are used:

  - by ``AnalysisService`` to validate and coerce the LLM's JSON response
    (with retry-on-failure feeding the validation error back to the model)
  - by ``analysis_prompts.get_analysis_prompt`` to keep the prompt's JSON
    template in sync with the runtime schema (Phase 1 Step 5 will refactor
    the prompt to derive directly from these models)

The models are intentionally permissive at the parsing edges (string fit
scores, percent signs, dict-wrapped numbers) and strict at the type edges
(every field is typed, every list defaults to empty rather than None).
This means a slightly malformed but recoverable LLM response is coerced
into a valid object instead of triggering a retry.
"""

from typing import List, Optional, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Deadlines(BaseModel):
    """Key dates extracted from a procurement document.

    Phase 1 Step 5 will replace this 3-field schema with a richer model
    that captures Q&A deadlines, pre-bid conferences, addenda deadlines,
    BAFO, oral presentations, period of performance, etc.
    """

    model_config = ConfigDict(extra="ignore")

    proposal_submission: Optional[str] = "Not specified"
    decision_date: Optional[str] = "Not specified"
    contract_start: Optional[str] = "Not specified"


class BudgetClues(BaseModel):
    """Budget-related signals extracted from a procurement document."""

    model_config = ConfigDict(extra="ignore")

    estimated_budget: Optional[str] = "Not specified"
    pricing_model: Optional[str] = "Not specified"
    notes: Optional[str] = ""


class AnalysisExtraction(BaseModel):
    """The structured intelligence the LLM must produce for a bid package.

    This is the contract between the prompt and the database. The
    ``AnalysisResult`` ORM model stores each of these fields in its own
    column (typed columns for scalars, JSONB for the lists/dicts), so any
    new field added here also needs a column on ``AnalysisResult`` and an
    Alembic migration. Step 5 will do exactly that.
    """

    model_config = ConfigDict(extra="ignore")

    document_type: str = Field(
        default="UNKNOWN",
        description="Document classification (RFP, RFQ, RFI, SOW, etc.)",
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
        # Step 1: extract a numeric value from whatever shape the LLM returned.
        if v is None:
            return 0.0

        if isinstance(v, dict):
            # Some models wrap the score in {"score": 85} or {"value": 85}.
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

        # Step 2: apply the 0-1 normalization heuristic.
        # The prompt asks for 0-100, but LLMs sometimes confuse scales and
        # return 0.85 when they mean 85. We treat any value strictly between
        # 0 and 1 (exclusive on both ends) as 0-1 normalized and rescale.
        # Exactly 0 means "no fit" and exactly 1 means "1% fit", both kept as-is.
        if 0.0 < num < 1.0:
            num *= 100.0

        return num

    @field_validator(
        "scope_of_work",
        "mandatory_requirements",
        "evaluation_criteria",
        "risks",
        "usp_suggestions",
        mode="before",
    )
    @classmethod
    def _coerce_string_list(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            # LLM returned a single string instead of a list — wrap it
            return [v] if v.strip() else []
        if isinstance(v, list):
            # Filter out None and empty strings; coerce non-strings to str
            return [str(item).strip() for item in v if item is not None and str(item).strip()]
        # Last resort: stringify and wrap
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
