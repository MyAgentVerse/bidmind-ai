"""Chunk retrieval for proposal sections — keyword + semantic hybrid.

Phase 2 introduced structural keyword-based retrieval.
Phase 3 adds semantic retrieval via pgvector embeddings, creating a
**hybrid** mode that combines both signals for the best results.

Keyword retrieval: fast, deterministic, good for exact section-heading matches.
Semantic retrieval: handles paraphrasing and non-standard headings ("Article IV"
instead of "Scope of Work").
Hybrid: union of both, re-ranked by combined score.

This module maps each of the 8 proposal sections to relevant RFP chunks
using structural matching against ``DocumentChunk.section`` (the nearest
heading text) and ``compliance_matrix`` category fields, plus optional
semantic similarity when embeddings are available.

The retriever is initialized once per proposal-generation request with
the pre-parsed chunks and the analysis compliance matrix, then called
once per section to get a ``RetrievedContext`` containing:

  - Ranked chunks with page numbers (for LLM citation)
  - Filtered compliance_matrix entries by category
  - A token estimate for prompt budget planning

The ``format_for_prompt`` methods render the retrieved context into
citation-ready strings that the rewritten ``proposal_prompts.py``
injects directly into section prompts.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Heuristic: ~4 chars per token (same as file_parser_service.py)
CHARS_PER_TOKEN = 4

# Stop words to exclude from keyword matching
STOP_WORDS: Set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "that",
    "the", "to", "was", "were", "will", "with", "not", "this", "but",
    "they", "their", "which", "who", "whom", "can", "may", "shall",
    "should", "must", "all", "any", "each", "every", "such", "than",
    "other", "been", "being", "would", "could", "into", "also", "more",
    "no", "nor", "only", "own", "same", "so", "very", "just", "about",
    "above", "after", "before", "between", "both", "does", "during",
    "had", "how", "if", "most", "our", "out", "over", "some", "these",
    "through", "under", "up", "what", "when", "where", "your",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RetrievedContext:
    """Context retrieved for a single proposal section."""

    chunks: List[Dict[str, Any]] = field(default_factory=list)
    # Each chunk dict: {text, page, section, chunk_type, score}

    compliance_entries: List[Dict[str, Any]] = field(default_factory=list)
    # Filtered compliance_matrix entries relevant to this section

    chunk_token_estimate: int = 0

    def format_chunks_for_prompt(self) -> str:
        """Render retrieved chunks as a citation-ready string for the LLM.

        Output format::

            --- RFP Reference (Page 12, Section: Scope of Work) ---
            <chunk text>

            --- RFP Reference (Page 15, Section: Technical Requirements) ---
            <chunk text>

        Returns empty string if no chunks were retrieved.
        """
        if not self.chunks:
            return ""

        parts: List[str] = []
        for c in self.chunks:
            page = c.get("page", "?")
            section = c.get("section", "Unknown Section")
            text = c.get("text", "")
            page_label = f"Page {page}" if page and page != 1 else "Document"
            parts.append(
                f"--- RFP Reference ({page_label}, Section: {section}) ---\n"
                f"{text}"
            )
        return "\n\n".join(parts)

    def format_compliance_for_prompt(self) -> str:
        """Render compliance entries as a structured list for the LLM.

        Output format::

            [MUST] (technical) REQ-01: Vendor must provide 24/7 support
              Evidence required: Sample SLA + on-call rotation diagram

        Returns empty string if no compliance entries were retrieved.
        """
        if not self.compliance_entries:
            return ""

        lines: List[str] = []
        for entry in self.compliance_entries:
            rtype = entry.get("requirement_type", "must").upper()
            cat = entry.get("category", "general")
            rid = entry.get("requirement_id", "")
            text = entry.get("requirement_text", "")
            evidence = entry.get("evidence_required", "")

            prefix = f"[{rtype}] ({cat})"
            if rid:
                prefix += f" {rid}:"
            lines.append(f"{prefix} {text}")
            if evidence:
                lines.append(f"  Evidence required: {evidence}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section-to-keyword mapping
# ---------------------------------------------------------------------------

# Each entry: (keywords_to_match_against_headings, compliance_matrix_categories)
# Keywords are matched case-insensitively against DocumentChunk.section text.
# Compliance categories filter the compliance_matrix entries.

SECTION_RELEVANCE: Dict[str, Tuple[List[str], List[str]]] = {
    "understanding_of_requirements": (
        [
            "scope", "objective", "purpose", "background", "introduction",
            "overview", "statement of work", "sow", "requirements", "need",
            "mission", "goals", "context", "description", "summary",
            "executive", "about", "project",
        ],
        ["technical", "management", "administrative"],
    ),
    "proposed_solution": (
        [
            "scope", "statement of work", "sow", "technical", "approach",
            "methodology", "deliverables", "tasks", "work breakdown",
            "specifications", "performance", "functional", "system",
            "phase", "milestone", "timeline", "schedule", "implementation",
            "design", "architecture", "solution", "services",
        ],
        ["technical", "management"],
    ),
    "why_us": (
        [
            "qualifications", "experience", "past performance", "references",
            "organizational", "corporate", "capability", "team", "personnel",
            "key staff", "staffing", "certifications", "awards", "track record",
            "similar", "relevant", "demonstrated",
        ],
        ["past_performance", "management"],
    ),
    "risk_mitigation": (
        [
            "risk", "contingency", "mitigation", "quality", "assurance",
            "compliance", "security", "safety", "transition", "continuity",
            "disaster", "recovery", "backup", "monitoring", "audit",
            "incident", "response", "threat", "vulnerability",
        ],
        ["security", "technical", "management"],
    ),
    "pricing_positioning": (
        [
            "pricing", "cost", "budget", "financial", "compensation",
            "rates", "labor", "fee", "payment", "billing", "clin",
            "line item", "invoice", "discount", "value", "roi",
            "economic", "price", "funding", "expenditure",
        ],
        ["pricing"],
    ),
    "executive_summary": (
        # Union of the most important keywords from all sections
        [
            "scope", "objective", "purpose", "background", "overview",
            "executive", "summary", "requirements", "approach",
            "deliverables", "qualifications", "experience", "pricing",
            "cost", "risk", "timeline", "value",
        ],
        ["technical", "management", "pricing"],
    ),
    "cover_letter": (
        [
            "introduction", "overview", "purpose", "background",
            "submission", "instructions", "solicitation", "invitation",
            "rfp", "rfq", "bid", "proposal",
        ],
        ["administrative"],
    ),
    "closing_statement": (
        [
            "submission", "instructions", "contact", "deadline",
            "protest", "award", "questions", "clarification",
            "due date", "closing",
        ],
        ["administrative"],
    ),
}


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class ChunkRetriever:
    """Structural keyword-based chunk retrieval for proposal sections.

    No embeddings, no vector DB. Uses keyword overlap between section
    heading text and the target keyword set, with boosts for high-value
    chunk types (tables, compliance-matrix-referenced pages).

    Usage::

        retriever = ChunkRetriever(parsed_chunks, compliance_matrix)
        ctx = retriever.retrieve_for_section("proposed_solution")
        prompt_text = ctx.format_chunks_for_prompt()
    """

    def __init__(
        self,
        chunks: List[Any],  # List[DocumentChunk] or list of dicts
        compliance_matrix: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.compliance_matrix = compliance_matrix or []

        # Normalize chunks to dicts for uniform handling (accepts both
        # DocumentChunk dataclass instances and raw dicts).
        self.chunks: List[Dict[str, Any]] = []
        for c in chunks:
            if isinstance(c, dict):
                self.chunks.append(c)
            elif hasattr(c, "to_dict"):
                self.chunks.append(c.to_dict())
            else:
                self.chunks.append({
                    "text": getattr(c, "text", ""),
                    "page": getattr(c, "page", 1),
                    "section": getattr(c, "section", None),
                    "chunk_type": getattr(c, "chunk_type", "paragraph"),
                    "heading_level": getattr(c, "heading_level", None),
                })

        # Pre-compute the set of pages referenced by the compliance matrix.
        # Chunks on these pages get a relevance boost (the buyer explicitly
        # pointed to them).
        self._cm_pages: Set[int] = set()
        for entry in self.compliance_matrix:
            page = entry.get("source_page")
            if page is not None:
                try:
                    self._cm_pages.add(int(page))
                except (ValueError, TypeError):
                    pass

        logger.debug(
            f"ChunkRetriever initialized: {len(self.chunks)} chunks, "
            f"{len(self.compliance_matrix)} compliance entries, "
            f"{len(self._cm_pages)} compliance-referenced pages"
        )

    # ---- Public API -------------------------------------------------------

    def retrieve_for_section(
        self,
        section_name: str,
        max_chunks: int = 15,
        max_token_budget: int = 4000,
    ) -> RetrievedContext:
        """Retrieve relevant chunks + compliance entries for a proposal section.

        Args:
            section_name: One of the 8 proposal section names (e.g.,
                ``"proposed_solution"``).
            max_chunks: Hard cap on number of chunks returned.
            max_token_budget: Soft cap on estimated token count of returned
                chunks. The retriever stops adding chunks once this budget
                is reached.

        Returns:
            ``RetrievedContext`` with ranked chunks, filtered compliance
            entries, and a token estimate.
        """
        keywords, cm_categories = SECTION_RELEVANCE.get(
            section_name, ([], [])
        )
        if not keywords:
            logger.warning(
                f"No keyword mapping for section '{section_name}'; "
                f"returning empty context"
            )
            return RetrievedContext()

        # 1. Score and rank chunks
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for chunk in self.chunks:
            score = self._score_chunk(chunk, keywords)
            if score > 0:
                scored.append((score, chunk))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        # 2. Take top-N within the token budget
        selected: List[Dict[str, Any]] = []
        token_count = 0
        seen_texts: Set[str] = set()  # de-duplicate identical chunks

        for score, chunk in scored:
            text = chunk.get("text", "")
            # Skip duplicates (repeated headers across pages, etc.)
            text_key = text.strip()[:200]
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            chunk_tokens = len(text) // CHARS_PER_TOKEN
            if token_count + chunk_tokens > max_token_budget and selected:
                break  # Budget exceeded (but always include at least 1)
            if len(selected) >= max_chunks:
                break

            selected.append({
                "text": text,
                "page": chunk.get("page", 1),
                "section": chunk.get("section", ""),
                "chunk_type": chunk.get("chunk_type", "paragraph"),
                "score": round(score, 3),
            })
            token_count += chunk_tokens

        # 3. Filter compliance entries by category
        cm_entries = self._filter_compliance(cm_categories)

        logger.debug(
            f"retrieve_for_section('{section_name}'): "
            f"{len(selected)} chunks (~{token_count} tokens), "
            f"{len(cm_entries)} compliance entries"
        )

        return RetrievedContext(
            chunks=selected,
            compliance_entries=cm_entries,
            chunk_token_estimate=token_count,
        )

    def retrieve_all_sections(self) -> Dict[str, RetrievedContext]:
        """Retrieve context for all 8 sections. Returns ``{section_name: RetrievedContext}``."""
        return {
            name: self.retrieve_for_section(name)
            for name in SECTION_RELEVANCE
        }

    # ---- Phase 3: Hybrid retrieval (keyword + semantic) ------------------

    def retrieve_for_section_hybrid(
        self,
        section_name: str,
        semantic_results: List[Dict[str, Any]],
        max_chunks: int = 15,
        max_token_budget: int = 4000,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6,
    ) -> RetrievedContext:
        """Hybrid retrieval: combine keyword matching with semantic search.

        Args:
            section_name: One of the 8 proposal section names.
            semantic_results: Pre-fetched semantic search results from
                ``EmbeddingService.search_similar()``. Each dict has:
                ``{text, page, section, chunk_type, similarity}``.
            max_chunks: Hard cap on chunks returned.
            max_token_budget: Soft cap on estimated tokens.
            keyword_weight: Weight for keyword score in combined ranking.
            semantic_weight: Weight for semantic similarity in combined ranking.

        Returns:
            ``RetrievedContext`` with the best chunks from both sources.
        """
        keywords, cm_categories = SECTION_RELEVANCE.get(
            section_name, ([], [])
        )

        # 1. Keyword-scored chunks (from the existing structural retriever)
        keyword_scored: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        for chunk in self.chunks:
            score = self._score_chunk(chunk, keywords)
            if score > 0:
                key = (chunk.get("text", "").strip()[:200])
                if key not in keyword_scored or score > keyword_scored[key][0]:
                    keyword_scored[key] = (score, chunk)

        # Normalize keyword scores to 0-1 range
        max_kw = max((s for s, _ in keyword_scored.values()), default=1.0)
        if max_kw > 0:
            for key in keyword_scored:
                score, chunk = keyword_scored[key]
                keyword_scored[key] = (score / max_kw, chunk)

        # 2. Semantic-scored chunks
        semantic_scored: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        for result in semantic_results:
            key = (result.get("text", "").strip()[:200])
            sim = result.get("similarity", 0.0)
            semantic_scored[key] = (sim, result)

        # 3. Merge: union of both sets, combined score
        all_keys = set(keyword_scored.keys()) | set(semantic_scored.keys())
        combined: List[Tuple[float, Dict[str, Any]]] = []

        for key in all_keys:
            kw_score = keyword_scored.get(key, (0.0, None))[0]
            sem_score = semantic_scored.get(key, (0.0, None))[0]

            # Pick the chunk data from whichever source has it
            chunk = (
                keyword_scored.get(key, (0, None))[1]
                or semantic_scored.get(key, (0, None))[1]
            )
            if chunk is None:
                continue

            score = (keyword_weight * kw_score) + (semantic_weight * sem_score)
            combined.append((score, chunk))

        # Sort descending
        combined.sort(key=lambda x: x[0], reverse=True)

        # 4. Take top-N within token budget
        selected: List[Dict[str, Any]] = []
        token_count = 0
        seen: Set[str] = set()

        for score, chunk in combined:
            text_val = chunk.get("text", "")
            text_key = text_val.strip()[:200]
            if text_key in seen:
                continue
            seen.add(text_key)

            chunk_tokens = len(text_val) // CHARS_PER_TOKEN
            if token_count + chunk_tokens > max_token_budget and selected:
                break
            if len(selected) >= max_chunks:
                break

            selected.append({
                "text": text_val,
                "page": chunk.get("page", chunk.get("chunk_page", 1)),
                "section": chunk.get("section", chunk.get("chunk_section", "")),
                "chunk_type": chunk.get("chunk_type", "paragraph"),
                "score": round(score, 3),
            })
            token_count += chunk_tokens

        # 5. Compliance entries (same as keyword-only mode)
        cm_entries = self._filter_compliance(cm_categories)

        logger.debug(
            f"retrieve_hybrid('{section_name}'): "
            f"{len(selected)} chunks (~{token_count} tok), "
            f"kw_candidates={len(keyword_scored)}, "
            f"sem_candidates={len(semantic_scored)}, "
            f"{len(cm_entries)} compliance"
        )

        return RetrievedContext(
            chunks=selected,
            compliance_entries=cm_entries,
            chunk_token_estimate=token_count,
        )

    # ---- Scoring ----------------------------------------------------------

    def _score_chunk(
        self,
        chunk: Dict[str, Any],
        keywords: List[str],
    ) -> float:
        """Score a chunk against a keyword set. Higher = more relevant.

        Scoring factors:
          - Keyword overlap between the chunk's section heading and the
            keyword set (primary signal).
          - Keyword overlap in the chunk text itself (secondary signal,
            weighted lower to avoid noise).
          - Boost for table chunks (contain structured data like pricing,
            evaluation matrices).
          - Boost for chunks on pages referenced by the compliance matrix.
          - Slight penalty for heading-only chunks (label, not substance).
        """
        section_text = (chunk.get("section") or "").lower()
        chunk_text = (chunk.get("text") or "").lower()
        chunk_type = chunk.get("chunk_type", "paragraph")
        page = chunk.get("page", 0)

        # Primary: keyword matches in the section heading
        heading_matches = sum(
            1 for kw in keywords if kw.lower() in section_text
        )
        heading_score = heading_matches / max(len(keywords), 1)

        # Secondary: keyword matches in the chunk body (lower weight)
        body_matches = sum(
            1 for kw in keywords if kw.lower() in chunk_text
        )
        body_score = (body_matches / max(len(keywords), 1)) * 0.3

        score = heading_score + body_score

        # Type boosts
        if chunk_type == "table":
            score *= 1.5  # Tables are high-value (pricing, eval matrices)
        elif chunk_type == "heading":
            score *= 0.5  # Headings provide context but little substance

        # Compliance-page boost
        if page in self._cm_pages:
            score += 0.15

        return score

    def _filter_compliance(
        self,
        categories: List[str],
    ) -> List[Dict[str, Any]]:
        """Filter compliance_matrix entries by category.

        Always includes ``must`` requirements regardless of category
        (mandatory requirements should be visible in every section).
        """
        if not self.compliance_matrix:
            return []

        results: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        for entry in self.compliance_matrix:
            entry_cat = (entry.get("category") or "").lower()
            entry_type = (entry.get("requirement_type") or "").lower()
            req_text = entry.get("requirement_text", "")

            # De-duplicate by requirement text
            text_key = req_text.strip()[:150]
            if text_key in seen:
                continue

            # Include if category matches OR if it's a mandatory requirement
            if entry_cat in categories or entry_type == "must":
                seen.add(text_key)
                results.append(entry)

        return results


# ---------------------------------------------------------------------------
# Utility: extract key terms (used by proposal_reviewer.py too)
# ---------------------------------------------------------------------------


def extract_key_terms(text: str) -> List[str]:
    """Extract meaningful search terms from a text string.

    Strips stop words, normalizes to lowercase, removes very short tokens,
    and returns terms that are discriminative enough to search for.

    Used by both ``ChunkRetriever`` and ``ProposalReviewer`` for keyword
    matching.
    """
    if not text:
        return []

    # Normalize: lowercase, split on non-alphanumeric
    tokens = re.split(r"[^a-z0-9]+", text.lower())

    # Filter: remove stop words, very short tokens, and pure numbers
    terms = [
        t for t in tokens
        if t
        and len(t) > 2
        and t not in STOP_WORDS
        and not t.isdigit()
    ]

    return terms
