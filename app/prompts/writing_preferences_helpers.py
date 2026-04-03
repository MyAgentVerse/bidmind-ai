"""Helper functions to incorporate writing preferences into proposal prompts."""

from typing import Optional, Dict, Any


def build_writing_style_context(preferences: Optional[Dict[str, Any]]) -> str:
    """
    Build a writing style context string from preferences.

    Args:
        preferences: Writing preferences dictionary

    Returns:
        Formatted string with writing style guidelines
    """
    if not preferences:
        return ""

    lines = []

    # Tone level
    tone_level = preferences.get("tone_level", 3)
    tone_descriptions = {
        1: "very casual and friendly",
        2: "casual and conversational",
        3: "professional and neutral",
        4: "formal and authoritative",
        5: "very formal and executive-level"
    }
    lines.append(f"Tone: Write in a {tone_descriptions.get(tone_level, 'professional')} manner.")

    # Brand voice tags
    voice_tags = preferences.get("brand_voice_tags", [])
    if voice_tags:
        tags_str = ", ".join(voice_tags)
        lines.append(f"Brand Voice: Ensure the content reflects these qualities: {tags_str}.")

    # Language complexity
    complexity = preferences.get("language_complexity", "standard")
    complexity_guidance = {
        "simple": "Use clear, simple language that anyone can understand. Avoid technical jargon.",
        "standard": "Use standard business language appropriate for most audiences.",
        "technical": "Use technical language and industry jargon to demonstrate expertise."
    }
    lines.append(complexity_guidance.get(complexity, complexity_guidance["standard"]))

    # Company jargon
    jargon = preferences.get("company_jargon")
    if jargon:
        lines.append(f"Company Terminology: Use these specific terms where appropriate: {jargon}")

    return "\n".join(lines)


def build_content_guidelines_context(preferences: Optional[Dict[str, Any]]) -> str:
    """
    Build a content guidelines context string from preferences.

    Args:
        preferences: Writing preferences dictionary

    Returns:
        Formatted string with content guidelines
    """
    if not preferences:
        return ""

    lines = []

    # Must include items
    must_include = preferences.get("must_include", [])
    if must_include:
        include_str = ", ".join(must_include)
        lines.append(f"MUST INCLUDE: {include_str}")

    # Do not include
    do_not_include = preferences.get("do_not_include")
    if do_not_include:
        lines.append(f"DO NOT INCLUDE: {do_not_include}")

    # Focus areas
    focus_areas = preferences.get("focus_areas", {})
    if focus_areas:
        # Sort by weight (highest first)
        sorted_areas = sorted(focus_areas.items(), key=lambda x: x[1], reverse=True)
        focus_str = ", ".join([f"{k} ({v}/10)" for k, v in sorted_areas])
        lines.append(f"FOCUS AREAS (weighted importance): {focus_str}")

    return "\n".join(lines)


def get_section_length_multiplier(section_name: str, preferences: Optional[Dict[str, Any]]) -> float:
    """
    Get the length multiplier for a specific section.

    Args:
        section_name: Name of the section (e.g., 'why_us')
        preferences: Writing preferences dictionary

    Returns:
        Length multiplier (1.0 = default length)
    """
    if not preferences:
        return 1.0

    multipliers = preferences.get("section_length_multipliers", {})
    return multipliers.get(section_name, 1.0)


def apply_length_instruction(base_length: str, multiplier: float) -> str:
    """
    Apply length multiplier to a base length instruction.

    Args:
        base_length: Base length instruction (e.g., "3-4 paragraphs (150-250 words)")
        multiplier: Length multiplier

    Returns:
        Adjusted length instruction
    """
    if multiplier == 1.0:
        return base_length

    if multiplier < 1.0:
        return f"{base_length} (SHORTENED: make this section {int(multiplier * 100)}% of normal length)"
    else:
        return f"{base_length} (EXPANDED: make this section {int(multiplier * 100)}% of normal length)"


def get_section_order(preferences: Optional[Dict[str, Any]]) -> list:
    """
    Get custom section order or default.

    Args:
        preferences: Writing preferences dictionary

    Returns:
        List of section names in desired order
    """
    if preferences:
        custom_order = preferences.get("section_order")
        if custom_order:
            return custom_order

    # Default section order
    return [
        "cover_letter",
        "executive_summary",
        "understanding_of_requirements",
        "proposed_solution",
        "why_us",
        "pricing_positioning",
        "risk_mitigation",
        "closing_statement"
    ]


def enhance_section_prompt(
    base_prompt: str,
    section_name: str,
    preferences: Optional[Dict[str, Any]] = None
) -> str:
    """
    Enhance a section prompt with writing preferences.

    Args:
        base_prompt: Original prompt text
        section_name: Name of the section being generated
        preferences: Writing preferences dictionary

    Returns:
        Enhanced prompt with preferences integrated
    """
    if not preferences:
        return base_prompt

    enhancements = []

    # Add writing style context
    style_context = build_writing_style_context(preferences)
    if style_context:
        enhancements.append(f"\n=== WRITING STYLE GUIDELINES ===\n{style_context}")

    # Add content guidelines context
    guidelines_context = build_content_guidelines_context(preferences)
    if guidelines_context:
        enhancements.append(f"\n=== CONTENT GUIDELINES ===\n{guidelines_context}")

    # Add section-specific length instructions
    multiplier = get_section_length_multiplier(section_name, preferences)
    if multiplier != 1.0:
        enhancements.append(f"\n=== SECTION LENGTH ===\nAdjust the length of this section to {int(multiplier * 100)}% of the default length.")

    # Combine all enhancements
    if enhancements:
        return base_prompt + "\n" + "\n".join(enhancements)

    return base_prompt
