"""Prompts for analyzing procurement documents."""

from typing import List, Optional


def get_analysis_prompt(
    document_text: str,
    company_context: Optional[str] = None,
    source_files: Optional[List[str]] = None,
) -> str:
    """
    Generate prompt for analyzing a procurement document or bid package.

    Returns a prompt that instructs the LLM to extract structured intelligence
    from a procurement document (RFP, RFQ, RFI, etc.) or — when ``source_files``
    contains more than one filename — from a multi-document bid package
    combined by :meth:`AnalysisService.combine_files_for_analysis`.

    Args:
        document_text: Combined text from one or more procurement documents.
            For multi-document packages this contains delimiter markers like
            ``===== DOCUMENT N of M: filename.pdf =====``.
        company_context: Optional company profile to personalize the fit
            assessment.
        source_files: Optional list of filenames included in this analysis.
            When the list has more than one entry, the prompt switches to
            multi-document mode and asks the model to attribute extracted
            requirements back to their source file.

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

    multi_file_section = ""
    is_multi_file = source_files is not None and len(source_files) > 1
    if is_multi_file:
        files_list = "\n".join(f"  {idx}. {fn}" for idx, fn in enumerate(source_files, start=1))
        multi_file_section = f"""
MULTI-DOCUMENT BID PACKAGE:
This bid package contains {len(source_files)} documents that must be analyzed
together as a single opportunity:
{files_list}

The combined text below wraps each file with delimiter markers:
    ===== DOCUMENT N of M: filename =====
    [content]
    ===== END OF filename =====

Treat the FIRST document as the primary RFP/solicitation. Subsequent
documents are typically addenda, attachments, Q&A responses, scope of work,
pricing templates, or technical specifications. Later documents may MODIFY
or ADD requirements from earlier ones — when in doubt, the most recent
addendum wins.

When you extract requirements, scope items, deadlines, or risks, attribute
each one to its source file by appending "(source: <filename>)" to the
extracted string. For deadlines and budget clues that appear in multiple
files, use the value from the most recent file and note any conflict in the
relevant field.
"""

    prompt = f"""You are an expert procurement analyst specializing in government and commercial bidding processes.

Analyze the following procurement {"bid package" if is_multi_file else "document"} and extract key intelligence that will help in crafting a winning proposal.
{company_section}{multi_file_section}
DOCUMENT{"S" if is_multi_file else ""}:
---
{document_text}
---

Extract and return the following information as a valid JSON object:

{{
    "document_type": "string (e.g., RFP, RFQ, RFI, SOW, PROPOSAL INSTRUCTIONS)",
    "opportunity_summary": "string (2-3 sentence high-level summary of what's being sought)",
    "scope_of_work": [
        "string (individual scope item 1{', with source attribution' if is_multi_file else ''})",
        "string (individual scope item 2)"
    ],
    "mandatory_requirements": [
        "string (requirement that MUST be met to qualify{', with source attribution' if is_multi_file else ''})",
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
- Extract ONLY information present in the {"documents" if is_multi_file else "document"}
- Be specific - reference actual requirements, dates, and numbers from the {"documents" if is_multi_file else "document"}
- If information is not provided, use null or appropriate default
- For fit_score, consider: clarity of requirements, specificity, apparent complexity{', and company match' if company_context else ''}
- For pricing_strategy_summary, provide strategic guidance based on evaluation criteria and budget clues
- Ensure the JSON is valid and parseable
{('- For each scope item, mandatory requirement, and risk, append "(source: <filename>)" so the user knows which file it came from' + chr(10)) if is_multi_file else ''}
Return ONLY valid JSON, no additional text."""

    return prompt
