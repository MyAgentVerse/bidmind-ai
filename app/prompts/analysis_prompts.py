"""Prompts for analyzing procurement documents."""

import json
from typing import Optional


def get_analysis_prompt(
    document_text: str,
    company_context: Optional[str] = None
) -> str:
    """
    Generate prompt for analyzing a procurement document.

    Returns a prompt that instructs Claude to extract structured intelligence
    from a procurement document (RFP, RFQ, RFI, etc.) with optional company context.

    Args:
        document_text: The extracted text from the procurement document
        company_context: Optional company profile information to personalize analysis

    Returns:
        Complete prompt for document analysis
    """

    company_section = ""
    if company_context:
        company_section = f"""
COMPANY PROFILE (use this to personalize fit assessment):
{company_context}

When scoring FIT, consider:
- How well the opportunity aligns with the company's industry focus
- Whether required capabilities match the company's strengths
- If past experience is relevant to this opportunity
- How competitive the company is for this specific opportunity
"""

    prompt = f"""You are an expert procurement analyst specializing in government and commercial bidding processes.

Analyze the following procurement document and extract key intelligence that will help in crafting a winning proposal.
{company_section}

DOCUMENT:
---
{document_text}
---

Extract and return the following information as a valid JSON object:

{{
    "document_type": "string (e.g., RFP, RFQ, RFI, SOW, PROPOSAL INSTRUCTIONS)",
    "opportunity_summary": "string (2-3 sentence high-level summary of what's being sought)",
    "scope_of_work": [
        "string (individual scope item 1)",
        "string (individual scope item 2)"
    ],
    "mandatory_requirements": [
        "string (requirement that MUST be met to qualify)",
        "string (another mandatory requirement)"
    ],
    "deadlines": {{
        "proposal_submission": "date or 'Not specified'",
        "decision_date": "date or 'Not specified'",
        "contract_start": "date or 'Not specified'"
    }},
    "evaluation_criteria": [
        "string (criterion 1 and approximate weighting if mentioned)",
        "string (criterion 2 and approximate weighting if mentioned)"
    ],
    "budget_clues": {{
        "estimated_budget": "string (amount or range if mentioned)",
        "pricing_model": "string (fixed price, T&M, cost-plus, etc.)",
        "notes": "string (any other budget-related details)"
    }},
    "risks": [
        "string (identified risk or constraint 1)",
        "string (identified risk or constraint 2)"
    ],
    "fit_score": number (0-100, assessment of opportunity fit{' for this company' if company_context else ' for a typical vendor'}),
    "usp_suggestions": [
        "string (suggested unique selling proposition 1)",
        "string (suggested unique selling proposition 2)"
    ],
    "pricing_strategy_summary": "string (high-level guidance on pricing approach)"
}}

IMPORTANT:
- Extract ONLY information present in the document
- Be specific - reference actual requirements, dates, and numbers from the document
- If information is not provided, use null or appropriate default
- For fit_score, consider: clarity of requirements, specificity, apparent complexity{', and company match' if company_context else ''}
- For pricing_strategy_summary, provide strategic guidance based on evaluation criteria and budget clues
- Ensure the JSON is valid and parseable

Return ONLY valid JSON, no additional text."""

    return prompt
