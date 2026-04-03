"""Prompts for AI-assisted editing of proposal sections."""


def get_edit_prompt(section_name: str, current_text: str, instruction: str) -> str:
    """
    Generate a prompt for editing a proposal section.

    Args:
        section_name: The section being edited (e.g., 'executive_summary')
        current_text: The current text of the section
        instruction: The user's editing instruction (e.g., 'make more concise')

    Returns:
        Complete prompt for the AI editor
    """

    # Map section names to friendly titles
    section_titles = {
        "cover_letter": "Cover Letter",
        "executive_summary": "Executive Summary",
        "understanding_of_requirements": "Understanding of Requirements",
        "proposed_solution": "Proposed Solution",
        "why_us": "Why Us",
        "pricing_positioning": "Pricing Positioning",
        "risk_mitigation": "Risk Mitigation",
        "closing_statement": "Closing Statement",
    }

    section_title = section_titles.get(section_name, section_name)

    prompt = f"""You are an expert proposal editor helping refine procurement proposal sections.

Your task: Revise the following proposal section based on the user's instruction.

SECTION: {section_title}

CURRENT TEXT:
---
{current_text}
---

EDITING INSTRUCTION: {instruction}

REQUIREMENTS FOR YOUR REVISION:
1. Follow the user's editing instruction precisely
2. Preserve the core message and intent
3. Maintain professional tone appropriate for procurement proposals
4. Do not add false claims, certifications, or made-up credentials
5. Keep the edited text roughly similar length (±10%)
6. Ensure the text flows naturally
7. Preserve specific facts, dates, and numbers from the original
8. Make the text more compelling and persuasive where appropriate
9. Check for clarity, conciseness, and impact
10. Maintain consistency with typical proposal section standards

EDITING GUIDELINES:
- If instruction is "make more concise": Remove redundancy, tighten language
- If instruction is "make stronger": Emphasize benefits, add power words, strengthen claims
- If instruction is "make more professional": Elevate tone, remove informal language
- If instruction is "add more detail": Expand with specific examples or explanations
- If instruction is "simplify": Use clearer language, shorter sentences, remove jargon
- If instruction is "make persuasive": Add benefits, create stronger case, increase conviction
- If instruction is "add compliance tone": Emphasize adherence, standards, governance
- If instruction is "improve flow": Better transitions, smoother reading experience

CRITICAL:
- Return ONLY the revised section text
- Do not add explanations, commentary, or suggestions
- Do not invent qualifications or credentials not in the original
- Do not change the fundamental meaning
- Preserve factual accuracy from the original text

Revise the section now:"""

    return prompt
