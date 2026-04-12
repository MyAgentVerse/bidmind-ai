"""Post-generation compliance coverage check for proposals.

Phase 2 of the BidMind AI deep-analysis upgrade.

After a proposal is generated, this module checks whether every
compliance_matrix requirement was addressed somewhere in the 8
generated sections. The check is **deterministic** (no LLM call)
and uses keyword overlap between requirement text and section text.

The result is a ``ReviewResult`` with:
  - ``coverage_percentage`` — overall coverage
  - ``must_coverage_percentage`` — coverage of ``must`` requirements only
  - ``gaps`` — requirements that appear to be unaddressed
  - ``covered`` — requirements that appear to be addressed
  - ``sections_needing_revision`` — sections with the most gaps
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from app.services.chunk_retriever import extract_key_terms

logger = logging.getLogger(__name__)

# A requirement is considered "addressed" if at least this fraction of
# its key terms appear somewhere in the proposal sections.
COVERAGE_THRESHOLD = 0.35

# Minimum number of matching terms required (absolute floor).
MIN_MATCHING_TERMS = 2


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RequirementCoverage:
    """Coverage assessment for a single compliance requirement."""

    requirement_id: Optional[str] = None
    requirement_text: str = ""
    requirement_type: str = "must"  # must / should / may
    category: Optional[str] = None
    is_addressed: bool = False
    addressed_in_sections: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0–1.0 keyword match strength
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


# ---------------------------------------------------------------------------
# Reviewer
# ---------------------------------------------------------------------------


class ProposalReviewer:
    """Deterministic compliance coverage checker.

    No LLM call — uses keyword overlap between requirement text and
    the generated proposal sections. Fast, free, and repeatable.

    Usage::

        reviewer = ProposalReviewer()
        result = reviewer.review_coverage(sections, compliance_matrix)
        print(f"Coverage: {result.coverage_percentage:.0f}%")
        for gap in result.gaps:
            print(f"  GAP: {gap.requirement_text[:80]}")
    """

    def review_coverage(
        self,
        sections: Dict[str, str],
        compliance_matrix: List[Dict],
    ) -> ReviewResult:
        """Run the deterministic coverage check.

        For each compliance_matrix entry:
          1. Extract key terms from ``requirement_text``
          2. Search for those terms across all proposal sections
          3. Compute confidence = (matched terms / total terms)
          4. Mark as addressed if confidence >= threshold AND
             matched terms >= minimum

        Returns a ``ReviewResult`` with coverage stats and gap list.
        """
        if not compliance_matrix:
            return ReviewResult()

        # Pre-normalize all section text for searching
        normalized_sections: Dict[str, str] = {
            name: text.lower() for name, text in sections.items() if text
        }

        results: List[RequirementCoverage] = []

        for entry in compliance_matrix:
            req_text = entry.get("requirement_text", "")
            if not req_text:
                continue

            terms = extract_key_terms(req_text)
            if not terms:
                # No meaningful terms — consider it trivially addressed
                results.append(
                    RequirementCoverage(
                        requirement_id=entry.get("requirement_id"),
                        requirement_text=req_text,
                        requirement_type=entry.get("requirement_type", "must"),
                        category=entry.get("category"),
                        is_addressed=True,
                        confidence=1.0,
                        notes="No discriminative terms to search for",
                    )
                )
                continue

            # Search for terms across sections
            found_in: List[str] = []
            total_found = 0

            for section_name, section_text in normalized_sections.items():
                section_matches = sum(
                    1 for t in terms if t in section_text
                )
                if section_matches > 0:
                    found_in.append(section_name)
                    total_found = max(total_found, section_matches)

            confidence = total_found / len(terms) if terms else 0.0
            is_addressed = (
                confidence >= COVERAGE_THRESHOLD
                and total_found >= min(MIN_MATCHING_TERMS, len(terms))
            )

            results.append(
                RequirementCoverage(
                    requirement_id=entry.get("requirement_id"),
                    requirement_text=req_text,
                    requirement_type=entry.get("requirement_type", "must"),
                    category=entry.get("category"),
                    is_addressed=is_addressed,
                    addressed_in_sections=found_in,
                    confidence=round(confidence, 3),
                )
            )

        # Compute aggregates
        total = len(results)
        addressed = sum(1 for r in results if r.is_addressed)
        gaps = [r for r in results if not r.is_addressed]
        covered = [r for r in results if r.is_addressed]

        must_total = sum(
            1 for r in results if r.requirement_type == "must"
        )
        must_addressed = sum(
            1 for r in results
            if r.requirement_type == "must" and r.is_addressed
        )

        coverage_pct = (addressed / total * 100) if total else 0.0
        must_pct = (must_addressed / must_total * 100) if must_total else 0.0

        # Identify sections that need revision (sections with the most
        # unaddressed requirements). For each gap, the "responsible"
        # section is determined by the gap's category.
        section_gap_count: Dict[str, int] = {}
        category_to_section = {
            "technical": "proposed_solution",
            "management": "proposed_solution",
            "past_performance": "why_us",
            "pricing": "pricing_positioning",
            "security": "risk_mitigation",
            "administrative": "understanding_of_requirements",
        }
        for gap in gaps:
            target = category_to_section.get(
                gap.category or "", "understanding_of_requirements"
            )
            section_gap_count[target] = section_gap_count.get(target, 0) + 1

        # Sections with 2+ gaps need revision
        needing_revision = [
            name
            for name, count in sorted(
                section_gap_count.items(), key=lambda x: x[1], reverse=True
            )
            if count >= 2
        ]

        result = ReviewResult(
            total_requirements=total,
            addressed_count=addressed,
            coverage_percentage=coverage_pct,
            must_coverage_percentage=must_pct,
            gaps=gaps,
            covered=covered,
            sections_needing_revision=needing_revision,
        )

        logger.info(
            f"Coverage review: {addressed}/{total} addressed "
            f"({coverage_pct:.0f}%), {must_addressed}/{must_total} must "
            f"({must_pct:.0f}%), {len(gaps)} gaps, "
            f"{len(needing_revision)} sections need revision"
        )

        return result
