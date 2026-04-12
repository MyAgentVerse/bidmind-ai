"""Prompts for generating grounded proposal sections.

Phase 2 of the BidMind AI deep-analysis upgrade.

Every prompt function now receives:

  - ``analysis_data`` — the full 30-field extraction (Step C)
  - ``retrieved_context`` — relevant RFP chunks + compliance entries
    from ``ChunkRetriever`` (with page citations)
  - ``prior_sections`` — the text of previously generated sections
    (for narrative coherence across the 8-section proposal)
  - ``company`` — optional company profile dict

The prompts are designed to produce grounded, citation-rich text.
The LLM is instructed to reference specific RFP content using
``(Page N)`` or ``(Section: ...)`` citations, and to explicitly
address each compliance requirement that appears in its context.
"""

from typing import Optional, Dict, Any, List

# Import is deferred so this module can be imported before
# chunk_retriever is available (e.g., during tests).
# At call time, retrieved_context is always a RetrievedContext instance.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_analysis_summary(analysis_data: dict) -> str:
    """Render the analysis fields into a concise summary block."""
    parts: List[str] = []

    summary = analysis_data.get("opportunity_summary", "")
    if summary:
        parts.append(f"Opportunity: {summary}")

    doc_type = analysis_data.get("document_type", "")
    if doc_type:
        parts.append(f"Document Type: {doc_type}")

    fit = analysis_data.get("fit_score")
    if fit is not None:
        parts.append(f"Fit Score: {fit}/100")

    scope = analysis_data.get("scope_of_work", [])
    if scope:
        items = "\n  - ".join(scope[:8])
        parts.append(f"Scope of Work:\n  - {items}")

    reqs = analysis_data.get("mandatory_requirements", [])
    if reqs:
        items = "\n  - ".join(reqs[:8])
        parts.append(f"Mandatory Requirements:\n  - {items}")

    criteria = analysis_data.get("evaluation_criteria", [])
    if criteria:
        items = "\n  - ".join(criteria[:6])
        parts.append(f"Evaluation Criteria:\n  - {items}")

    risks = analysis_data.get("risks", [])
    if risks:
        items = "\n  - ".join(risks[:6])
        parts.append(f"Identified Risks:\n  - {items}")

    deadlines = analysis_data.get("deadlines", {})
    if isinstance(deadlines, dict):
        dl_parts = [
            f"  {k}: {v}" for k, v in deadlines.items()
            if v and v != "Not specified"
        ]
        if dl_parts:
            parts.append("Key Deadlines:\n" + "\n".join(dl_parts))

    budget = analysis_data.get("budget_clues", {})
    if isinstance(budget, dict) and budget.get("estimated_budget", "Not specified") != "Not specified":
        parts.append(f"Budget: {budget.get('estimated_budget', 'Not specified')} ({budget.get('pricing_model', 'TBD')})")

    return "\n\n".join(parts)


def _build_prior_sections_block(prior_sections: Dict[str, str]) -> str:
    """Render previously generated sections for coherence context."""
    if not prior_sections:
        return ""

    parts: List[str] = []
    for name, text in prior_sections.items():
        label = name.replace("_", " ").title()
        parts.append(f"--- Previously Generated: {label} ---\n{text}")
    return "\n\n".join(parts)


def _build_company_block(company: Optional[Dict[str, Any]]) -> str:
    """Render the company profile for prompt context."""
    if not company:
        return ""

    parts: List[str] = []
    name = company.get("name", "Our Company")
    parts.append(f"Company: {name}")

    for field, label in [
        ("usp", "Unique Selling Proposition"),
        ("capabilities", "Key Capabilities"),
        ("experience", "Experience"),
        ("industry_focus", "Industry Focus"),
        ("description", "Description"),
    ]:
        val = company.get(field)
        if val:
            parts.append(f"{label}: {val}")

    return "\n".join(parts)


def _build_learnings_block(learnings: Optional[Dict[str, Any]]) -> str:
    """Render learned preferences from past proposal feedback."""
    if not learnings:
        return ""

    parts: List[str] = []

    prefs = learnings.get("learned_preferences", {})
    if prefs:
        if prefs.get("tone_preference"):
            parts.append(f"Preferred tone: {prefs['tone_preference']}")
        if prefs.get("emphasis_areas"):
            parts.append(f"Emphasize: {', '.join(prefs['emphasis_areas'])}")
        if prefs.get("avoid_areas"):
            parts.append(f"Avoid: {', '.join(prefs['avoid_areas'])}")
        if prefs.get("pricing_guidance"):
            parts.append(f"Pricing approach: {prefs['pricing_guidance']}")
        if prefs.get("length_preference"):
            parts.append(f"Length preference: {prefs['length_preference']}")
        if prefs.get("winning_patterns"):
            parts.append(f"Winning patterns: {', '.join(prefs['winning_patterns'][:3])}")

    issues = learnings.get("common_issues", {})
    if issues:
        top_issues = sorted(issues.items(), key=lambda x: x[1], reverse=True)[:5]
        issue_strs = [f"{k} ({v}x)" for k, v in top_issues]
        parts.append(f"Common complaints to avoid: {', '.join(issue_strs)}")

    sat = learnings.get("satisfaction_rate")
    total = learnings.get("total_proposals")
    if sat is not None and total:
        parts.append(f"Track record: {total} proposals, {sat}% satisfaction rate")

    if not parts:
        return ""

    return "\n".join(parts)


def _section_prompt(
    section_label: str,
    instructions: str,
    analysis_data: dict,
    retrieved_context: Any,  # RetrievedContext
    prior_sections: Dict[str, str],
    company: Optional[Dict[str, Any]] = None,
    learnings: Optional[Dict[str, Any]] = None,
    length_guidance: str = "400-600 words",
) -> str:
    """Build a complete grounded prompt for any proposal section.

    This is the template all 8 section prompts share. It assembles:
      1. Role statement
      2. Retrieved RFP chunks (with page citations)
      3. Compliance requirements
      4. Analysis summary
      5. Prior sections (for coherence)
      6. Company profile
      7. Section-specific instructions
      8. Citation and formatting rules
    """
    chunks_text = ""
    compliance_text = ""
    if retrieved_context is not None:
        chunks_text = retrieved_context.format_chunks_for_prompt()
        compliance_text = retrieved_context.format_compliance_for_prompt()

    analysis_summary = _build_analysis_summary(analysis_data)
    prior_text = _build_prior_sections_block(prior_sections)
    company_text = _build_company_block(company)

    sections: List[str] = []

    # Role
    sections.append(
        "You are a senior proposal writer with deep experience winning "
        "government and commercial bids. You write precise, grounded "
        "proposals that directly address every RFP requirement with "
        "specific evidence and page citations."
    )

    # Retrieved RFP context
    if chunks_text:
        sections.append(
            f"=== RFP CONTEXT (retrieved from the source document) ===\n"
            f"{chunks_text}"
        )

    # Compliance requirements
    if compliance_text:
        sections.append(
            f"=== COMPLIANCE REQUIREMENTS (from bid package analysis) ===\n"
            f"{compliance_text}\n\n"
            f"You MUST explicitly address each [MUST] requirement that is "
            f"relevant to this section. For [SHOULD] requirements, address "
            f"them if you can demonstrate capability."
        )

    # Analysis summary
    if analysis_summary:
        sections.append(
            f"=== ANALYSIS SUMMARY ===\n{analysis_summary}"
        )

    # Prior sections
    if prior_text:
        sections.append(
            f"=== PREVIOUSLY GENERATED SECTIONS (for coherence) ===\n"
            f"Do NOT repeat content from these sections. Reference them "
            f"where appropriate ('As detailed in our Proposed Solution...'). "
            f"Maintain a consistent narrative voice.\n\n"
            f"{prior_text}"
        )

    # Company profile
    if company_text:
        sections.append(
            f"=== COMPANY PROFILE ===\n{company_text}"
        )

    # Phase 5: Learned preferences from past feedback
    learnings_text = _build_learnings_block(learnings)
    if learnings_text:
        sections.append(
            f"=== LEARNED PREFERENCES (from past proposal feedback) ===\n"
            f"This organization has accumulated feedback on past proposals. "
            f"Apply these preferences to improve output quality:\n\n"
            f"{learnings_text}"
        )

    # Section-specific instructions
    sections.append(
        f"=== INSTRUCTIONS: {section_label} ===\n{instructions}"
    )

    # Citation and formatting rules
    sections.append(
        f"=== RULES ===\n"
        f"- Length: {length_guidance}\n"
        f"- When referencing specific RFP content, cite the source: "
        f"'As stated in the RFP (Page 12)...' or '(Section: Scope of Work)'\n"
        f"- Address each relevant compliance requirement explicitly\n"
        f"- Be specific — use real names, dates, numbers from the RFP\n"
        f"- Do NOT invent claims the company cannot support\n"
        f"- Do NOT repeat content already covered in prior sections\n"
        f"- Write ONLY this section's content, no headers or meta-commentary"
    )

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Section prompt functions
# ---------------------------------------------------------------------------


def get_understanding_prompt(
    analysis_data: dict,
    retrieved_context: Any = None,
    prior_sections: Optional[Dict[str, str]] = None,
    company: Optional[Dict[str, Any]] = None,
    learnings: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for Understanding of Requirements section."""
    return _section_prompt(
        section_label="Understanding of Requirements",
        instructions=(
            "Demonstrate that you have thoroughly read and understood the "
            "client's needs. This section should:\n\n"
            "1. Restate the core challenge in your own words (showing comprehension, not copying)\n"
            "2. Identify the critical success factors and why they matter to the client\n"
            "3. Map the client's stated requirements to underlying business objectives\n"
            "4. Show awareness of stakeholders who will be impacted\n"
            "5. Reference specific RFP sections, page numbers, and requirements\n"
            "6. Identify any dependencies, constraints, or assumptions\n\n"
            "Tone: Consultative and analytical. Show you understand WHY, not just WHAT."
        ),
        analysis_data=analysis_data,
        retrieved_context=retrieved_context,
        prior_sections=prior_sections or {},
        company=company,
        length_guidance="400-600 words",
    )


def get_solution_prompt(
    analysis_data: dict,
    retrieved_context: Any = None,
    prior_sections: Optional[Dict[str, str]] = None,
    company: Optional[Dict[str, Any]] = None,
    learnings: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for Proposed Solution section."""
    return _section_prompt(
        section_label="Proposed Solution",
        instructions=(
            "Present a detailed, actionable solution that directly addresses "
            "every scope item and requirement from the RFP. This section should:\n\n"
            "1. Open with your overall approach / methodology / framework\n"
            "2. For EACH major scope item from the RFP, describe HOW you will deliver it\n"
            "3. Provide a phased implementation timeline with specific milestones\n"
            "4. Detail team roles and responsibilities\n"
            "5. Describe quality assurance and governance mechanisms\n"
            "6. Explain how you will handle transitions and knowledge transfer\n"
            "7. Tie every claim back to a specific RFP requirement or evaluation criterion\n\n"
            "Structure: methodology overview → phased delivery → team → QA → transition.\n"
            "Tone: Detailed, practical, solution-focused. Balance specificity with flexibility."
        ),
        analysis_data=analysis_data,
        retrieved_context=retrieved_context,
        prior_sections=prior_sections or {},
        company=company,
        learnings=learnings,
        length_guidance="600-900 words",
    )


def get_why_us_prompt(
    analysis_data: dict,
    retrieved_context: Any = None,
    prior_sections: Optional[Dict[str, str]] = None,
    company: Optional[Dict[str, Any]] = None,
    learnings: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for Why Us section."""
    company_name = company.get("name", "Our Company") if company else "Our Company"
    return _section_prompt(
        section_label=f"Why {company_name}",
        instructions=(
            f"Position {company_name} as the best choice for this opportunity. "
            f"This section should:\n\n"
            "1. State your core competitive advantages with evidence\n"
            "2. Highlight relevant past performance that matches the RFP's scope\n"
            "3. Show how your team's certifications and experience meet key personnel requirements\n"
            "4. Demonstrate industry knowledge specific to the client's sector\n"
            "5. Connect each differentiator to a specific evaluation criterion from the RFP\n"
            "6. Address longevity, stability, and commitment as a long-term partner\n\n"
            "IMPORTANT: Base all claims on the company profile provided. Do NOT fabricate "
            "experience or certifications. If the company is newer or lacks specific "
            "experience, position differently (agility, fresh perspective, specialized focus).\n\n"
            "Tone: Confident and evidence-based. Every claim maps to a proof point."
        ),
        analysis_data=analysis_data,
        retrieved_context=retrieved_context,
        prior_sections=prior_sections or {},
        company=company,
        learnings=learnings,
        length_guidance="500-700 words",
    )


def get_risk_mitigation_prompt(
    analysis_data: dict,
    retrieved_context: Any = None,
    prior_sections: Optional[Dict[str, str]] = None,
    company: Optional[Dict[str, Any]] = None,
    learnings: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for Risk Mitigation section."""
    return _section_prompt(
        section_label="Risk Mitigation",
        instructions=(
            "Present a comprehensive risk management approach that shows "
            "foresight and professionalism. This section should:\n\n"
            "1. Address EACH risk identified in the RFP analysis (see compliance requirements)\n"
            "2. Add 2-3 risks from your implementation experience that the RFP didn't mention\n"
            "3. For each risk, provide:\n"
            "   - Clear identification and why it matters\n"
            "   - Likelihood and impact assessment\n"
            "   - Specific mitigation strategy\n"
            "   - Contingency plan if mitigation fails\n"
            "   - How you will monitor and report on it\n"
            "4. Describe your overall risk governance framework\n"
            "5. Explain escalation procedures and communication cadence\n\n"
            "Tone: Proactive and confident. Risk-aware without being alarmist."
        ),
        analysis_data=analysis_data,
        retrieved_context=retrieved_context,
        prior_sections=prior_sections or {},
        company=company,
        learnings=learnings,
        length_guidance="500-650 words",
    )


def get_pricing_prompt(
    analysis_data: dict,
    retrieved_context: Any = None,
    prior_sections: Optional[Dict[str, str]] = None,
    company: Optional[Dict[str, Any]] = None,
    learnings: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for Pricing Positioning section."""
    budget = analysis_data.get("budget_clues", {})
    pricing_format = analysis_data.get("pricing_format", {})

    budget_note = ""
    if isinstance(budget, dict):
        est = budget.get("estimated_budget", "Not specified")
        model = budget.get("pricing_model", "Not specified")
        if est != "Not specified":
            budget_note = f"\nBudget indication: {est}, pricing model: {model}"

    format_note = ""
    if isinstance(pricing_format, dict) and any(pricing_format.values()):
        parts = [f"{k}: {v}" for k, v in pricing_format.items() if v]
        if parts:
            format_note = "\nPricing format requirements: " + "; ".join(parts)

    return _section_prompt(
        section_label="Pricing Positioning",
        instructions=(
            "Present your pricing philosophy and approach. This is strategic "
            "positioning, NOT specific dollar amounts. This section should:\n\n"
            "1. Explain your pricing philosophy (value-based, competitive, etc.)\n"
            "2. Describe the cost structure aligned with the RFP's pricing format\n"
            "3. Justify value relative to cost — tie pricing to ROI and outcomes\n"
            "4. Address the client's budget constraints if known\n"
            "5. Describe flexibility (phased approach, volume discounts, options)\n"
            "6. Show alignment with the evaluation criteria's cost weighting\n\n"
            "IMPORTANT: Do NOT invent specific dollar amounts or hourly rates. "
            "This section guides pricing strategy, not binding quotes. "
            "Actual pricing will be customized based on final scope.\n"
            f"{budget_note}{format_note}\n\n"
            "Tone: Business-savvy, transparent about value proposition."
        ),
        analysis_data=analysis_data,
        retrieved_context=retrieved_context,
        prior_sections=prior_sections or {},
        company=company,
        learnings=learnings,
        length_guidance="300-450 words",
    )


def get_executive_summary_prompt(
    analysis_data: dict,
    retrieved_context: Any = None,
    prior_sections: Optional[Dict[str, str]] = None,
    company: Optional[Dict[str, Any]] = None,
    learnings: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for Executive Summary section.

    Generated AFTER the core sections so it can synthesize them.
    """
    company_name = company.get("name", "Our Company") if company else "Our Company"
    return _section_prompt(
        section_label="Executive Summary",
        instructions=(
            "Write a compelling executive summary that synthesizes the "
            "entire proposal into a concise, persuasive overview. "
            "This section should:\n\n"
            "1. Open with the client's core challenge (1-2 sentences)\n"
            f"2. State {company_name}'s value proposition for this specific opportunity\n"
            "3. Summarize the proposed solution approach (from the Proposed Solution section)\n"
            "4. Highlight 2-3 key differentiators (from the Why Us section)\n"
            "5. Preview the risk management approach\n"
            "6. Express confidence in delivering measurable results\n\n"
            "CRITICAL: This section is written AFTER all other sections. "
            "Synthesize — do NOT copy. A senior executive should be able to "
            "read this alone and understand the full value proposition.\n\n"
            "Tone: Executive-level, results-focused, compelling."
        ),
        analysis_data=analysis_data,
        retrieved_context=retrieved_context,
        prior_sections=prior_sections or {},
        company=company,
        learnings=learnings,
        length_guidance="250-400 words",
    )


def get_cover_letter_prompt(
    analysis_data: dict,
    retrieved_context: Any = None,
    prior_sections: Optional[Dict[str, str]] = None,
    company: Optional[Dict[str, Any]] = None,
    learnings: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for Cover Letter section."""
    company_name = company.get("name", "Our Company") if company else "Our Company"
    co_info = analysis_data.get("contracting_officer", {})
    recipient = ""
    if isinstance(co_info, dict) and co_info.get("name"):
        recipient = f"\nRecipient: {co_info.get('name')}, {co_info.get('title', '')}, {co_info.get('organization', '')}"

    return _section_prompt(
        section_label="Cover Letter",
        instructions=(
            "Write a professional cover letter for the proposal submission. "
            "This section should:\n\n"
            "1. Address the contracting officer by name if known\n"
            "2. State that you are submitting a proposal in response to the specific RFP\n"
            "3. Express enthusiasm and understanding of the client's needs (1-2 sentences)\n"
            "4. Highlight 1-2 key strengths drawn from the Executive Summary\n"
            "5. Express commitment to the client's success\n"
            "6. Include a professional closing with signature line placeholder\n"
            f"{recipient}\n\n"
            "Tone: Professional, warm but not effusive. First impression matters."
        ),
        analysis_data=analysis_data,
        retrieved_context=retrieved_context,
        prior_sections=prior_sections or {},
        company=company,
        learnings=learnings,
        length_guidance="150-250 words",
    )


def get_closing_prompt(
    analysis_data: dict,
    retrieved_context: Any = None,
    prior_sections: Optional[Dict[str, str]] = None,
    company: Optional[Dict[str, Any]] = None,
    learnings: Optional[Dict[str, Any]] = None,
    summary: str = "",
) -> str:
    """Generate prompt for Closing Statement section."""
    company_name = company.get("name", "Our Company") if company else "Our Company"
    return _section_prompt(
        section_label="Closing Statement",
        instructions=(
            "Write a brief, impactful closing that leaves a positive "
            "final impression. This section should:\n\n"
            f"1. Summarize {company_name}'s key value proposition in 1-2 sentences\n"
            "2. Reiterate commitment to the client's success\n"
            "3. Include a clear call to action (next steps, discussion, presentation)\n"
            "4. Provide professional contact information template\n"
            "5. Express thanks for the opportunity\n\n"
            "Tone: Confident, positive, action-oriented. Brief and memorable."
        ),
        analysis_data=analysis_data,
        retrieved_context=retrieved_context,
        prior_sections=prior_sections or {},
        company=company,
        learnings=learnings,
        length_guidance="100-175 words",
    )
