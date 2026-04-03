"""AI prompt templates for analysis, proposal generation, and editing."""

from .analysis_prompts import get_analysis_prompt
from .proposal_prompts import (
    get_cover_letter_prompt,
    get_executive_summary_prompt,
    get_understanding_prompt,
    get_solution_prompt,
    get_why_us_prompt,
    get_pricing_prompt,
    get_risk_mitigation_prompt,
    get_closing_prompt,
)
from .edit_prompts import get_edit_prompt

__all__ = [
    "get_analysis_prompt",
    "get_cover_letter_prompt",
    "get_executive_summary_prompt",
    "get_understanding_prompt",
    "get_solution_prompt",
    "get_why_us_prompt",
    "get_pricing_prompt",
    "get_risk_mitigation_prompt",
    "get_closing_prompt",
    "get_edit_prompt",
]
