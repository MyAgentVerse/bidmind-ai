"""Prompts for analyzing procurement documents."""

import json


def get_analysis_prompt(document_text: str) -> str:
    """
    Generate prompt for analyzing a procurement document.

    Returns a prompt that instructs Claude to extract structured intelligence
    from a procurement document (RFP, RFQ, RFI, etc.).

    Args:
        document_text: The extracted text from the procurement document

    Returns:
        Complete prompt for document analysis
    """

    prompt = f"""You are an expert procurement analyst specializing in government and commercial bidding processes.

Analyze the following procurement document and extract key intelligence that will help in crafting a winning proposal.

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
    "fit_score": number (0-100, your assessment of how well a typical vendor might fit this opportunity),
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
- For fit_score, consider: clarity of requirements, specificity, apparent complexity
- For pricing_strategy_summary, provide strategic guidance based on evaluation criteria and budget clues
- Ensure the JSON is valid and parseable

Return ONLY valid JSON, no additional text."""

    return prompt
