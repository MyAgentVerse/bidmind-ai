"""Prompts for analyzing procurement documents.

Phase 1 Step C expands the requested JSON schema from 11 fields to ~25 so
the LLM extracts the artifacts a real proposal team needs:

  - Compliance matrix (every requirement with type, source, evidence)
  - Eligibility / qualifications (go/no-go gates)
  - Submission instructions (page limits, format, where to submit)
  - Pricing format (CLINs, line items, basis)
  - Key personnel requirements
  - NAICS, set-aside, contract type, period & place of performance
  - Contracting officer info
  - Required forms, insurance, clauses by reference, wage determinations,
    protest procedures, funding source
  - Expanded deadlines (Q&A, pre-bid conference, addenda, BAFO, etc.)

The schema returned by the prompt MUST mirror the runtime
``AnalysisExtraction`` Pydantic model in
``app/schemas/analysis_extraction.py`` — that's the validator the response
will be checked against. Add a field there first, then update this prompt
to ask for it.
"""

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
- Whether the company meets the eligibility_requirements you extract
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

When you extract requirements, populate the ``source_file`` field on each
compliance_matrix entry with the filename it came from. For deadlines and
budget clues that appear in multiple files, use the value from the most
recent file and note any conflict.
"""

    prompt = f"""You are an expert procurement / capture analyst specializing in government and commercial bidding processes. Your job is to extract every piece of structured intelligence a proposal team needs to (1) decide whether to bid and (2) write a winning, compliant response.

Analyze the following procurement {"bid package" if is_multi_file else "document"} and produce a JSON object that conforms EXACTLY to the schema below.
{company_section}{multi_file_section}
DOCUMENT{"S" if is_multi_file else ""}:
---
{document_text}
---

Return a JSON object with the following structure. Use null or sensible defaults for fields you cannot determine from the text. Do NOT invent information.

{{
    "document_type": "RFP|RFQ|RFI|SOW|IFB|BAA|RFI|SOLICITATION|PROPOSAL_INSTRUCTIONS|UNKNOWN",
    "opportunity_summary": "2-3 sentence high-level summary of what is being sought",

    "scope_of_work": [
        "Individual scope item 1{', with (source: filename) suffix' if is_multi_file else ''}",
        "Individual scope item 2"
    ],

    "mandatory_requirements": [
        "Must-have requirement 1{', with (source: filename) suffix' if is_multi_file else ''}",
        "Must-have requirement 2"
    ],

    "deadlines": {{
        "proposal_submission": "YYYY-MM-DD or descriptive string or 'Not specified'",
        "questions_due": "YYYY-MM-DD or 'Not specified'",
        "pre_bid_conference": "YYYY-MM-DD HH:MM or 'Not specified'",
        "addenda_deadline": "YYYY-MM-DD or 'Not specified'",
        "oral_presentations": "YYYY-MM-DD or 'Not specified'",
        "bafo_deadline": "YYYY-MM-DD or 'Not specified'",
        "decision_date": "YYYY-MM-DD or 'Not specified'",
        "award_date": "YYYY-MM-DD or 'Not specified'",
        "contract_start": "YYYY-MM-DD or 'Not specified'"
    }},

    "evaluation_criteria": [
        "Criterion + weighting if mentioned, e.g., 'Technical approach (40%)'",
        "Past performance (30%)"
    ],

    "budget_clues": {{
        "estimated_budget": "Amount or range, e.g., '$1M-$2M' or 'Not specified'",
        "pricing_model": "FFP|T&M|CPFF|IDIQ|BPA|FFP-LOE|Cost-Plus|Other|Not specified",
        "notes": "Any other budget-relevant detail"
    }},

    "risks": [
        "Identified risk or constraint 1",
        "Identified risk or constraint 2"
    ],

    "fit_score": 0-100 number representing overall opportunity fit{' for the company above' if company_context else ' for a typical vendor'},

    "usp_suggestions": [
        "Suggested unique selling proposition 1",
        "Suggested unique selling proposition 2"
    ],

    "pricing_strategy_summary": "1-2 paragraph strategic guidance on how to price this opportunity",

    "eligibility_requirements": [
        "Hard go/no-go gate 1 (e.g., 'Active SAM.gov registration required')",
        "SOC 2 Type II certification required",
        "Minimum $5M in annual revenue"
    ],

    "compliance_matrix": [
        {{
            "requirement_id": "L.4.2.1 or similar identifier from the doc, or null",
            "requirement_text": "Exact text of the requirement",
            "requirement_type": "must|should|may|informational",
            "category": "technical|management|past_performance|pricing|administrative|security|other",
            "source_file": {'"filename if multi-file, else null"' if is_multi_file else 'null'},
            "source_section": "Section reference like 'L.4.2' if available, else null",
            "source_page": "PDF page number if known (integer), else null",
            "evidence_required": "What proof the buyer wants (e.g., 'Sample SLA + on-call rotation diagram')",
            "notes": "Optional additional context"
        }}
    ],

    "submission_instructions": {{
        "delivery_method": "Electronic via SAM.gov | Email | Hand delivery | etc.",
        "delivery_address": "Where to submit",
        "file_format": "PDF only | DOCX | etc.",
        "page_limit": "e.g., '50 pages excluding appendices' or null",
        "font_requirements": "e.g., 'Times New Roman 12pt' or null",
        "margin_requirements": "e.g., '1 inch all sides' or null",
        "naming_convention": "Required filename format if specified",
        "number_of_copies": "How many copies / files",
        "required_sections": ["Technical Volume", "Past Performance Volume", "Cost Volume"],
        "notes": "Other submission rules"
    }},

    "pricing_format": {{
        "pricing_template": "e.g., 'Attachment B - Pricing Worksheet' or null",
        "line_item_structure": "CLINs | labor categories | deliverables | etc.",
        "pricing_basis": "FFP | T&M | CPFF | IDIQ | etc.",
        "discount_requirements": "e.g., 'Volume discounts required for >$1M'",
        "payment_terms": "e.g., 'Net 30 from acceptance'",
        "notes": "Other pricing instructions"
    }},

    "key_personnel_requirements": [
        {{
            "role": "Program Manager",
            "required_certifications": ["PMP", "ITIL"],
            "required_clearance": "Secret | Top Secret | TS/SCI | Public Trust | null",
            "minimum_experience_years": 10,
            "education_requirements": "e.g., 'BS in Computer Science or related'",
            "notes": "Other constraints"
        }}
    ],

    "naics_codes": ["541512", "541519"],

    "set_aside_status": "8(a) | SDVOSB | WOSB | EDWOSB | HUBZone | Small Business | Full and Open | Sole Source | null",

    "contract_type": "FFP | FFP-LOE | T&M | CPFF | CPIF | IDIQ | BPA | Other | null",

    "period_of_performance": "e.g., '5 years base + 5 option years' or null",

    "place_of_performance": "Geographic location or 'Remote' or null",

    "estimated_value": "$X-$Y or null",

    "contracting_officer": {{
        "name": "...",
        "title": "...",
        "organization": "...",
        "email": "...",
        "phone": "...",
        "address": "..."
    }},

    "required_forms": [
        "SF-33",
        "Reps and Certifications",
        "Lobbying Certification",
        "Conflict of Interest Disclosure"
    ],

    "past_performance_requirements": {{
        "minimum_references": 3,
        "recency_window_years": 5,
        "minimum_contract_value": "$1M",
        "similar_scope_required": true,
        "similar_size_required": true,
        "notes": "Other constraints"
    }},

    "insurance_requirements": {{
        "general_liability": "$1M per occurrence / $2M aggregate",
        "professional_liability": "$2M per claim",
        "workers_comp": "Statutory",
        "cyber_liability": "$5M per claim",
        "payment_bond": null,
        "performance_bond": null,
        "bid_bond": null,
        "notes": null
    }},

    "clauses_by_reference": [
        "FAR 52.204-7 System for Award Management",
        "FAR 52.219-14 Limitations on Subcontracting"
    ],

    "wage_determinations": "Davis-Bacon | SCA | None | null",

    "protest_procedures": "Brief description of protest procedure if mentioned",

    "funding_source": "Appropriated | Grant | Federal pass-through | Other | null"
}}

EXTRACTION RULES:
- Extract ONLY information present in the {"documents" if is_multi_file else "document"}. Do NOT invent values.
- For fields you cannot determine, use null (for objects/strings/numbers) or [] (for lists), NOT made-up placeholder values.
- For the compliance_matrix, aim for one entry per distinct mandatory or evaluated requirement. A 50-page RFP typically yields 30-100 entries.
- Categorize each compliance_matrix item: "technical" / "management" / "past_performance" / "pricing" / "administrative" / "security" / "other".
- For requirement_type, use "must" for shall/must/required, "should" for recommended/preferred, "may" for optional, "informational" for FYI.
- For fit_score, consider: clarity of requirements, specificity, apparent complexity{', and company match against eligibility_requirements + key capabilities' if company_context else ''}.
- For pricing_strategy_summary, give strategic guidance derived from evaluation_criteria + budget_clues + competition signals.
{('- For each requirement, scope item, and risk, append "(source: <filename>)" so the user knows which file it came from.' + chr(10)) if is_multi_file else ''}
Return ONLY valid JSON matching the schema above. No prose, no markdown fences, no commentary."""

    return prompt
