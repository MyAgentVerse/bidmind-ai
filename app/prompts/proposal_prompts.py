"""Prompts for generating proposal sections."""


def get_cover_letter_prompt(analysis_data: dict, company_name: str = "Our Company") -> str:
    """Generate prompt for cover letter section."""

    summary = analysis_data.get("opportunity_summary", "the opportunity")
    client_focus = analysis_data.get("document_type", "procurement")

    prompt = f"""Write a professional cover letter for a proposal submission.

The opportunity is: {summary}

The cover letter should:
1. Open with enthusiasm and understanding of the client's needs
2. Briefly state that you are submitting a comprehensive proposal
3. Highlight 1-2 key strengths or differentiators
4. Express commitment to the client's success
5. Include a professional closing with signature line

Length: 3-4 paragraphs (150-250 words)
Tone: Professional, confident, but not arrogant
Company: {company_name}

Write ONLY the cover letter text, no introduction or explanation."""

    return prompt


def get_executive_summary_prompt(analysis_data: dict, company_name: str = "Our Company") -> str:
    """Generate prompt for executive summary section."""

    summary = analysis_data.get("opportunity_summary", "")
    requirements = analysis_data.get("mandatory_requirements", [])
    usp = analysis_data.get("usp_suggestions", [])

    requirements_text = "\n".join([f"- {r}" for r in (requirements[:3] if requirements else [])])
    usp_text = "\n".join([f"- {u}" for u in (usp[:2] if usp else [])])

    prompt = f"""Write an executive summary for a proposal.

Opportunity Overview:
{summary}

Key Requirements:
{requirements_text if requirements_text else "- See primary document"}

Our Key Differentiators:
{usp_text if usp_text else "- Expertise and experience"}

The executive summary should:
1. Restate the opportunity and client's core challenge
2. Briefly introduce {company_name}'s approach
3. Highlight key value propositions
4. Preview the structure of the proposal
5. Express confidence in delivering results

Length: 4-5 paragraphs (250-350 words)
Tone: Executive-level, results-focused, clear and compelling
Style: Professional proposal tone

Write ONLY the executive summary text, no introduction or explanation."""

    return prompt


def get_understanding_prompt(analysis_data: dict) -> str:
    """Generate prompt for understanding of requirements section."""

    summary = analysis_data.get("opportunity_summary", "")
    requirements = analysis_data.get("mandatory_requirements", [])
    scope = analysis_data.get("scope_of_work", [])
    eval_criteria = analysis_data.get("evaluation_criteria", [])

    requirements_text = "\n".join([f"- {r}" for r in (requirements[:5] if requirements else [])])
    scope_text = "\n".join([f"- {s}" for s in (scope[:4] if scope else [])])
    criteria_text = "\n".join([f"- {c}" for c in (eval_criteria[:3] if eval_criteria else [])])

    if not requirements_text:
        requirements_text = "- Client seeks comprehensive solution"
    if not scope_text:
        scope_text = "- Multiple deliverables"
    if not criteria_text:
        criteria_text = "- Technical capability, cost, experience"

    prompt = f"""Write a section demonstrating understanding of client requirements.

Opportunity: {summary}

Client's Requirements:
{requirements_text}

Scope of Work:
{scope_text}

Evaluation Criteria:
{criteria_text}

This section should:
1. Demonstrate that you understand the client's core challenge
2. Show you've read and understood the RFP/requirements
3. Identify the critical success factors
4. Explain how you map the client's needs to your approach
5. Show stakeholder awareness (who will be impacted, who needs to be involved)

Length: 5-6 paragraphs (400-500 words)
Tone: Consultative, client-focused, analytical
Style: Show deep reading of the requirements document

Write ONLY this section, no introduction or explanation."""

    return prompt


def get_solution_prompt(analysis_data: dict, company_name: str = "Our Company") -> str:
    """Generate prompt for proposed solution section."""

    scope = analysis_data.get("scope_of_work", [])
    requirements = analysis_data.get("mandatory_requirements", [])

    scope_text = "\n".join([f"- {s}" for s in (scope[:5] if scope else [])])

    prompt = f"""Write a detailed proposed solution section for a proposal.

Company: {company_name}

Scope of Work to Address:
{scope_text if scope_text else "- Full project scope"}

Mandatory Requirements: {len(requirements)} requirements to meet

This solution section should:
1. Outline your overall approach (methodology/framework)
2. Describe how you'll address each major component of the scope
3. Explain your implementation timeline/phases
4. Detail roles and responsibilities
5. Describe quality assurance and oversight mechanisms
6. Address risks and mitigation strategies specific to implementation
7. Show how you'll ensure successful adoption/transition

Structure:
- Opening statement of approach
- Detailed solution components/workstreams
- Timeline/phases
- Quality and governance
- Risk mitigation for implementation
- Success criteria and metrics

Length: 8-10 paragraphs (600-800 words)
Tone: Detailed, practical, solution-focused
Style: Balance between specificity and flexibility

Write ONLY this section, no introduction or explanation."""

    return prompt


def get_why_us_prompt(analysis_data: dict, company_name: str = "Our Company") -> str:
    """Generate prompt for why us section."""

    usp = analysis_data.get("usp_suggestions", [])
    fit_score = analysis_data.get("fit_score", 75)

    usp_text = "\n".join([f"- {u}" for u in (usp[:4] if usp else [])])

    if not usp_text:
        usp_text = "- Industry expertise\n- Proven methodology\n- Client success"

    prompt = f"""Write a 'Why Us' section that positions {company_name} as the best choice.

Company: {company_name}
Estimated Fit to Opportunity: {fit_score}%

Key Differentiators to Highlight:
{usp_text}

This section should:
1. State your core competitive advantages
2. Highlight relevant experience (without fabricating certifications or references)
3. Demonstrate industry knowledge
4. Show understanding of client's business context
5. Explain your culture and team's commitment
6. Address longevity and stability as a partner
7. Connect your capabilities to the client's specific evaluation criteria

Important:
- Base all claims on actual {company_name} capabilities
- Suggest positioning strategies without inventing false credentials
- Focus on how your real strengths match the client's needs
- Avoid exaggeration or unsupported claims

Structure:
- Opening statement of competitive advantage
- Experience and track record (with caveats if needed)
- Methodology and approach
- Team capabilities
- Client commitment and support
- Partnership and long-term value

Length: 6-8 paragraphs (500-700 words)
Tone: Confident, evidence-based, consultative
Style: Differentiation-focused

Write ONLY this section, no introduction or explanation."""

    return prompt


def get_pricing_prompt(analysis_data: dict) -> str:
    """Generate prompt for pricing positioning section."""

    budget_clues = analysis_data.get("budget_clues", {})
    eval_criteria = analysis_data.get("evaluation_criteria", [])
    doc_type = analysis_data.get("document_type", "RFP")

    budget_text = budget_clues.get("estimated_budget", "Not specified")
    pricing_model = budget_clues.get("pricing_model", "To be determined")

    prompt = f"""Write a pricing positioning section for a proposal.

Document Type: {doc_type}
Budget Indication: {budget_text}
Suggested Pricing Model: {pricing_model}
Evaluation Criteria: {eval_criteria}

This section should:
1. Explain your pricing philosophy and approach
2. Justify value provided relative to cost
3. Describe cost structure (labor, materials, overhead, profit margin)
4. Explain your delivery value and ROI
5. Address flexibility in pricing (volume discounts, phased approach, etc.)
6. Demonstrate cost awareness and value orientation

IMPORTANT:
- This is POSITIONING guidance, not actual pricing quotes
- Do NOT invent specific dollar amounts or rates
- Focus on strategy: value-based, cost-plus, performance-based pricing etc.
- Show alignment with client's budget constraints if known
- Explain pricing rationale without specific numbers

This section guides pricing negotiations:
- It's strategic guidance, not a binding quote
- Actual pricing will be customized based on final scope
- It demonstrates business acumen and flexibility

Length: 4-5 paragraphs (300-400 words)
Tone: Business-savvy, transparent about costs
Style: Strategic and consultative

Write ONLY this section, no introduction or explanation."""

    return prompt


def get_risk_mitigation_prompt(analysis_data: dict) -> str:
    """Generate prompt for risk mitigation section."""

    risks = analysis_data.get("risks", [])
    scope = analysis_data.get("scope_of_work", [])

    risks_text = "\n".join([f"- {r}" for r in (risks[:5] if risks else [])])

    if not risks_text:
        risks_text = "- Project complexity\n- Timeline constraints\n- Resource availability"

    scope_risks_text = "\n".join([f"- {s}" for s in (scope[:3] if scope else [])])

    prompt = f"""Write a risk mitigation section for a proposal.

Identified Risks from Document:
{risks_text}

Scope Elements at Risk:
{scope_risks_text}

This section should address:
1. Key risks identified in the RFP/opportunity
2. Additional risks from your implementation experience
3. Mitigation strategies for each major risk
4. Contingency plans and fallbacks
5. Communication and escalation procedures
6. Quality assurance checkpoints
7. How you'll ensure timeline and budget adherence

Risk Categories to Address:
- Technical/implementation risks
- Schedule/timeline risks
- Resource/staffing risks
- Integration/transition risks
- Organizational/adoption risks
- External dependency risks

For each risk:
- Identify the risk clearly
- Explain why it matters
- Describe your mitigation strategy
- Explain how you'll monitor/manage it

Length: 6-7 paragraphs (500-650 words)
Tone: Professional, proactive, confident
Style: Risk-aware without being alarmist

Write ONLY this section, no introduction or explanation."""

    return prompt


def get_closing_prompt(company_name: str = "Our Company", summary: str = "") -> str:
    """Generate prompt for closing statement section."""

    prompt = f"""Write a closing statement for a proposal submission.

Company: {company_name}
Summary: {summary if summary else "Professional services engagement"}

This closing should:
1. Summarize the key value proposition in 1-2 sentences
2. Reiterate your commitment to the client's success
3. Highlight your enthusiasm for the engagement
4. Include a call to action (next steps, discussion)
5. Provide professional contact information template
6. Express thanks for the opportunity

The closing should:
- Reinforce your positioning
- Leave a positive final impression
- Be memorable but not overly dramatic
- Include next steps or timeline expectations
- Be brief and impactful

Structure:
- Brief recap of key value
- Commitment and enthusiasm
- Call to action/next steps
- Professional closing
- Contact template

Length: 2-3 paragraphs (100-150 words)
Tone: Professional, positive, action-oriented
Style: Strong conclusion without redundancy

Write ONLY this closing section, no introduction or explanation."""

    return prompt
