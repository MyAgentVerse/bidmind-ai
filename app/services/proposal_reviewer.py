"""Post-generation compliance review, LLM gap confirmation, and targeted revision.

Phase 2 introduced deterministic keyword-based coverage checking.
Phase 4 adds:

  - **LLM-enhanced gap review**: sends uncertain/negative coverage results
    to the LLM for confirmation. The LLM reads the actual proposal sections
    and the flagged requirements, then classifies each as truly-missing or
    addressed-with-different-wording. This eliminates false negatives from
    the keyword check (e.g., "performance bond" flagged as a gap when the
    pricing section actually discusses it using different terminology).

  - **Targeted section revision**: for confirmed real gaps, re-generates
    ONLY the affected sections with explicit instructions to address the
    missing requirements. Does not touch sections that have full coverage.
    Capped at 2 revision passes to bound cost.

The deterministic check always runs (fast, free). The LLM review and
targeted revision are opt-in, controlled by parameters.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import get_settings
from app.services.chunk_retriever import extract_key_terms

logger = logging.getLogger(__name__)

# Deterministic coverage thresholds
COVERAGE_THRESHOLD = 0.35
MIN_MATCHING_TERMS = 2

# LLM review settings
MAX_REVISION_PASSES = 2

# Map compliance categories to the proposal section most responsible
CATEGORY_TO_SECTION = {
    "technical": "proposed_solution",
    "management": "proposed_solution",
    "past_performance": "why_us",
    "pricing": "pricing_positioning",
    "security": "risk_mitigation",
    "administrative": "understanding_of_requirements",
    "other": "understanding_of_requirements",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RequirementCoverage:
    """Coverage assessment for a single compliance requirement."""

    requirement_id: Optional[str] = None
    requirement_text: str = ""
    requirement_type: str = "must"
    category: Optional[str] = None
    is_addressed: bool = False
    addressed_in_sections: List[str] = field(default_factory=list)
    confidence: float = 0.0
    llm_confirmed: Optional[bool] = None  # Phase 4: LLM confirmation
    llm_notes: Optional[str] = None       # Phase 4: LLM explanation
    notes: Optional[str] = None


@dataclass
class ReviewResult:
    """Full review result for a generated proposal."""

    total_requirements: int = 0
    addressed_count: int = 0
    coverage_percentage: float = 0.0
    must_coverage_percentage: float = 0.0
    gaps: List[RequirementCoverage] = field(default_factory=list)
    covered: List[RequirementCoverage] = field(default_factory=list)
    sections_needing_revision: List[str] = field(default_factory=list)
    llm_reviewed: bool = False           # Phase 4: was LLM review run?
    revision_passes_completed: int = 0   # Phase 4: how many revision passes

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API response / storage."""
        return {
            "total_requirements": self.total_requirements,
            "addressed_count": self.addressed_count,
            "coverage_percentage": round(self.coverage_percentage, 1),
            "must_coverage_percentage": round(self.must_coverage_percentage, 1),
            "gaps": [
                {
                    "requirement_id": g.requirement_id,
                    "requirement_text": g.requirement_text,
                    "requirement_type": g.requirement_type,
                    "category": g.category,
                    "confidence": g.confidence,
                    "llm_confirmed": g.llm_confirmed,
                    "llm_notes": g.llm_notes,
                }
                for g in self.gaps
            ],
            "sections_needing_revision": self.sections_needing_revision,
            "llm_reviewed": self.llm_reviewed,
            "revision_passes_completed": self.revision_passes_completed,
        }


# ---------------------------------------------------------------------------
# Reviewer
# ---------------------------------------------------------------------------


class ProposalReviewer:
    """Compliance coverage reviewer with optional LLM confirmation and revision."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    # ---- Phase 2: Deterministic coverage check ---------------------------

    def review_coverage(
        self,
        sections: Dict[str, str],
        compliance_matrix: List[Dict],
    ) -> ReviewResult:
        """Deterministic keyword-based coverage check. No LLM call.

        For each compliance_matrix entry: extract key terms, search across
        all proposal sections, compute confidence, mark as addressed or gap.
        """
        if not compliance_matrix:
            return ReviewResult()

        normalized_sections = {
            name: text.lower() for name, text in sections.items() if text
        }

        results: List[RequirementCoverage] = []

        for entry in compliance_matrix:
            req_text = entry.get("requirement_text", "")
            if not req_text:
                continue

            terms = extract_key_terms(req_text)
            if not terms:
                results.append(RequirementCoverage(
                    requirement_id=entry.get("requirement_id"),
                    requirement_text=req_text,
                    requirement_type=entry.get("requirement_type", "must"),
                    category=entry.get("category"),
                    is_addressed=True,
                    confidence=1.0,
                    notes="No discriminative terms to search for",
                ))
                continue

            found_in: List[str] = []
            total_found = 0

            for section_name, section_text in normalized_sections.items():
                section_matches = sum(1 for t in terms if t in section_text)
                if section_matches > 0:
                    found_in.append(section_name)
                    total_found = max(total_found, section_matches)

            confidence = total_found / len(terms) if terms else 0.0
            is_addressed = (
                confidence >= COVERAGE_THRESHOLD
                and total_found >= min(MIN_MATCHING_TERMS, len(terms))
            )

            results.append(RequirementCoverage(
                requirement_id=entry.get("requirement_id"),
                requirement_text=req_text,
                requirement_type=entry.get("requirement_type", "must"),
                category=entry.get("category"),
                is_addressed=is_addressed,
                addressed_in_sections=found_in,
                confidence=round(confidence, 3),
            ))

        return self._build_review_result(results)

    # ---- Phase 4: LLM-enhanced gap review --------------------------------

    async def review_coverage_with_llm(
        self,
        sections: Dict[str, str],
        compliance_matrix: List[Dict],
    ) -> ReviewResult:
        """Two-stage coverage check: deterministic first, then LLM confirmation.

        Stage 1: Run the deterministic keyword check (same as review_coverage).
        Stage 2: Send the flagged gaps to the LLM along with the relevant
            proposal sections. The LLM classifies each as:
            - "addressed" (false alarm — the proposal covers it with different wording)
            - "missing" (real gap — the proposal doesn't address it)
            - "partial" (partially addressed — needs strengthening)

        This eliminates false negatives from the keyword check without
        re-reading the entire proposal (only the gap-relevant sections are sent).
        """
        # Stage 1: deterministic
        base_result = self.review_coverage(sections, compliance_matrix)

        if not base_result.gaps:
            base_result.llm_reviewed = True
            return base_result

        # Stage 2: LLM confirmation of gaps
        confirmed_gaps: List[RequirementCoverage] = []
        resolved_gaps: List[RequirementCoverage] = []

        try:
            llm_results = await self._llm_confirm_gaps(
                base_result.gaps, sections
            )

            for gap, llm_verdict in zip(base_result.gaps, llm_results):
                verdict = llm_verdict.get("verdict", "missing").lower()
                notes = llm_verdict.get("explanation", "")

                gap.llm_notes = notes

                if verdict == "addressed":
                    gap.llm_confirmed = False  # Not a real gap
                    gap.is_addressed = True
                    resolved_gaps.append(gap)
                elif verdict == "partial":
                    gap.llm_confirmed = True  # Still a gap, needs strengthening
                    gap.llm_notes = f"Partially addressed: {notes}"
                    confirmed_gaps.append(gap)
                else:  # "missing"
                    gap.llm_confirmed = True
                    confirmed_gaps.append(gap)

        except Exception as e:
            logger.warning(f"LLM gap review failed (keeping keyword results): {e}")
            confirmed_gaps = base_result.gaps

        # Rebuild result with LLM-refined gaps
        all_results = base_result.covered + resolved_gaps + confirmed_gaps
        for item in resolved_gaps:
            item.is_addressed = True
        for item in confirmed_gaps:
            item.is_addressed = False

        result = self._build_review_result(all_results)
        result.llm_reviewed = True
        return result

    async def _llm_confirm_gaps(
        self,
        gaps: List[RequirementCoverage],
        sections: Dict[str, str],
    ) -> List[Dict[str, str]]:
        """Ask the LLM to confirm whether each gap is real or a false alarm.

        Sends only the relevant sections (based on gap category) to minimize
        token usage. Returns a list of {verdict, explanation} dicts.
        """
        from openai import AsyncOpenAI

        # Build the gap list for the prompt
        gap_lines = []
        for i, gap in enumerate(gaps, 1):
            gap_lines.append(
                f"{i}. [{gap.requirement_type.upper()}] ({gap.category or 'general'}) "
                f"{gap.requirement_text}"
            )
        gaps_text = "\n".join(gap_lines)

        # Collect only the sections relevant to the gaps
        relevant_section_names: Set[str] = set()
        for gap in gaps:
            section = CATEGORY_TO_SECTION.get(gap.category or "", "understanding_of_requirements")
            relevant_section_names.add(section)
        # Always include understanding + solution (they cover the most ground)
        relevant_section_names.update(["understanding_of_requirements", "proposed_solution"])

        sections_text = ""
        for name in relevant_section_names:
            if name in sections and sections[name]:
                label = name.replace("_", " ").title()
                sections_text += f"\n--- {label} ---\n{sections[name]}\n"

        prompt = f"""You are a proposal compliance reviewer. I have a list of RFP requirements that a keyword-based check flagged as potentially NOT addressed in our proposal. Your job is to read the relevant proposal sections and determine whether each requirement is actually addressed (perhaps with different wording), partially addressed, or truly missing.

FLAGGED REQUIREMENTS:
{gaps_text}

RELEVANT PROPOSAL SECTIONS:
{sections_text}

For each numbered requirement, respond with a JSON array where each element has:
- "requirement_number": the number (1, 2, 3, ...)
- "verdict": "addressed" | "partial" | "missing"
- "explanation": brief reason (1 sentence)

Example:
[
  {{"requirement_number": 1, "verdict": "addressed", "explanation": "The proposed solution section discusses 24/7 support availability in paragraph 3."}},
  {{"requirement_number": 2, "verdict": "missing", "explanation": "No mention of performance bond anywhere in the proposal."}}
]

Return ONLY the JSON array, no other text."""

        async with AsyncOpenAI(api_key=self.settings.openai_api_key) as client:
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                max_tokens=2000,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )

        response_text = response.choices[0].message.content or ""

        try:
            parsed = json.loads(response_text)
            # Handle both {"results": [...]} and [...] formats
            if isinstance(parsed, dict):
                parsed = parsed.get("results", parsed.get("requirements", []))
            if isinstance(parsed, list):
                return parsed
            return [{"verdict": "missing", "explanation": "Could not parse LLM response"}] * len(gaps)
        except json.JSONDecodeError:
            logger.warning(f"Could not parse LLM gap review response")
            return [{"verdict": "missing", "explanation": "Parse error"}] * len(gaps)

    # ---- Phase 4: Targeted section revision ------------------------------

    async def revise_sections_for_gaps(
        self,
        sections: Dict[str, str],
        review: ReviewResult,
        retriever: Any,  # ChunkRetriever
        analysis_data: Dict[str, Any],
        company: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, str], ReviewResult]:
        """Re-generate sections that have confirmed gaps.

        Only re-generates sections listed in ``review.sections_needing_revision``.
        Each revision prompt includes the original section text + the explicit
        list of missing requirements that must be addressed.

        Runs up to MAX_REVISION_PASSES passes. After each pass, re-checks
        coverage. Stops early if coverage reaches 100%.

        Returns:
            (updated_sections, final_review_result)
        """
        from openai import AsyncOpenAI

        updated_sections = dict(sections)
        current_review = review

        async with AsyncOpenAI(api_key=self.settings.openai_api_key) as client:
            for pass_num in range(1, MAX_REVISION_PASSES + 1):
                if not current_review.gaps:
                    logger.info(f"No gaps remaining after pass {pass_num - 1}")
                    break

                sections_to_revise = current_review.sections_needing_revision
                if not sections_to_revise:
                    # Map remaining gaps to sections
                    sections_to_revise = list(set(
                        CATEGORY_TO_SECTION.get(g.category or "", "proposed_solution")
                        for g in current_review.gaps
                    ))

                logger.info(
                    f"Revision pass {pass_num}: revising {sections_to_revise} "
                    f"for {len(current_review.gaps)} gap(s)"
                )

                for section_name in sections_to_revise:
                    if section_name not in updated_sections:
                        continue

                    # Find gaps assigned to this section
                    section_gaps = [
                        g for g in current_review.gaps
                        if CATEGORY_TO_SECTION.get(g.category or "", "proposed_solution") == section_name
                    ]
                    if not section_gaps:
                        continue

                    # Build revision prompt
                    gap_list = "\n".join(
                        f"- [{g.requirement_type.upper()}] {g.requirement_text}"
                        + (f" (LLM note: {g.llm_notes})" if g.llm_notes else "")
                        for g in section_gaps
                    )

                    revision_prompt = f"""You are revising a proposal section to address compliance gaps. The section below was flagged for not adequately addressing certain RFP requirements. Your job is to revise the section to explicitly address each missing requirement while preserving the existing content and tone.

CURRENT SECTION TEXT:
{updated_sections[section_name]}

MISSING REQUIREMENTS THAT MUST BE ADDRESSED IN THIS SECTION:
{gap_list}

INSTRUCTIONS:
1. Keep all existing content that is good
2. Add new paragraphs or sentences that explicitly address each missing requirement
3. Be specific — reference the requirement directly
4. Maintain the same professional tone and style
5. Do not make the section significantly longer — integrate naturally
6. Return ONLY the revised section text, no commentary

Write the complete revised section now:"""

                    try:
                        response = await client.chat.completions.create(
                            model=self.settings.openai_model,
                            max_tokens=3000,
                            messages=[{"role": "user", "content": revision_prompt}],
                        )
                        revised_text = response.choices[0].message.content
                        if revised_text and len(revised_text) > 100:
                            updated_sections[section_name] = revised_text
                            logger.info(
                                f"Revised {section_name} to address {len(section_gaps)} gap(s)"
                            )
                    except Exception as e:
                        logger.warning(f"Revision failed for {section_name}: {e}")

                # Re-check coverage after this pass
                cm = analysis_data.get("compliance_matrix", [])
                current_review = self.review_coverage(updated_sections, cm)
                current_review.revision_passes_completed = pass_num

                logger.info(
                    f"After revision pass {pass_num}: "
                    f"{current_review.coverage_percentage:.0f}% coverage, "
                    f"{len(current_review.gaps)} gap(s) remaining"
                )

                if current_review.coverage_percentage >= 100.0:
                    break

        return updated_sections, current_review

    # ---- Helpers ---------------------------------------------------------

    @staticmethod
    def _build_review_result(results: List[RequirementCoverage]) -> ReviewResult:
        """Build aggregate ReviewResult from individual coverage assessments."""
        total = len(results)
        addressed = sum(1 for r in results if r.is_addressed)
        gaps = [r for r in results if not r.is_addressed]
        covered = [r for r in results if r.is_addressed]

        must_total = sum(1 for r in results if r.requirement_type == "must")
        must_addressed = sum(
            1 for r in results
            if r.requirement_type == "must" and r.is_addressed
        )

        coverage_pct = (addressed / total * 100) if total else 0.0
        must_pct = (must_addressed / must_total * 100) if must_total else 0.0

        # Identify sections needing revision
        section_gap_count: Dict[str, int] = {}
        for gap in gaps:
            target = CATEGORY_TO_SECTION.get(gap.category or "", "understanding_of_requirements")
            section_gap_count[target] = section_gap_count.get(target, 0) + 1

        needing_revision = [
            name for name, count in sorted(
                section_gap_count.items(), key=lambda x: x[1], reverse=True
            )
            if count >= 1  # Phase 4: revise even for 1 gap (was 2 in Phase 2)
        ]

        return ReviewResult(
            total_requirements=total,
            addressed_count=addressed,
            coverage_percentage=coverage_pct,
            must_coverage_percentage=must_pct,
            gaps=gaps,
            covered=covered,
            sections_needing_revision=needing_revision,
        )
