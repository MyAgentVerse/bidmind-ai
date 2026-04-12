"""Learning service for the proposal feedback loop.

Phase 5 of the BidMind AI deep-analysis upgrade.

This service enables the AI to learn from past proposals:

  - **Record** each proposal generation for later feedback
  - **Submit feedback** (love/okay/not_right + tags + text) on proposals
  - **Synthesize learnings** from accumulated feedback using an LLM call
    that analyzes patterns and produces actionable preferences
  - **Retrieve learnings** at proposal-generation time so the AI avoids
    past mistakes and doubles down on what worked

The learning loop:
  1. User generates a proposal → recorded in proposal_generations
  2. User rates the proposal → saved in proposal_feedback
  3. System synthesizes all feedback for the org → updates proposal_learnings
  4. Next proposal generation reads learned_preferences → injected into prompts
  5. AI avoids common_issues and follows learned preferences → better output
  6. Repeat
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.proposal_generation import ProposalGeneration
from app.models.proposal_feedback import ProposalFeedback
from app.models.proposal_learnings import ProposalLearnings

logger = logging.getLogger(__name__)


class LearningService:
    """Service for the proposal feedback/learning loop."""

    def __init__(self):
        self.settings = get_settings()

    # ---- Record generation -----------------------------------------------

    def record_generation(
        self,
        organization_id: str,
        proposal_title: str,
        sections: Dict[str, str],
        analysis_data: Optional[Dict] = None,
        writing_preferences: Optional[Dict] = None,
        user_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[ProposalGeneration]:
        """Record a proposal generation for later feedback.

        Called at the end of generate_proposal() to create a
        ProposalGeneration record that the user can later rate.
        """
        if not db or not organization_id:
            return None

        try:
            # Build content + metadata
            content = "\n\n---\n\n".join(
                f"## {name.replace('_', ' ').title()}\n\n{text_val}"
                for name, text_val in sections.items()
                if text_val
            )

            metadata = {
                "section_word_counts": {
                    name: len(text_val.split())
                    for name, text_val in sections.items()
                    if text_val
                },
                "total_words": sum(
                    len(t.split()) for t in sections.values() if t
                ),
            }
            if analysis_data:
                metadata["document_type"] = analysis_data.get("document_type")
                metadata["fit_score"] = analysis_data.get("fit_score")

            record = ProposalGeneration(
                id=uuid.uuid4(),
                organization_id=organization_id,
                created_by=user_id,
                proposal_title=proposal_title,
                proposal_type=analysis_data.get("document_type", "bid") if analysis_data else "bid",
                proposal_content=content,
                proposal_metadata=metadata,
                writing_preferences=writing_preferences,
                status="draft",
            )
            db.add(record)
            db.flush()

            # Update org's generation count
            self._increment_generation_count(organization_id, db)

            logger.info(
                f"Recorded proposal generation {record.id} "
                f"for org {organization_id}"
            )
            return record

        except Exception as e:
            logger.warning(f"Failed to record generation (non-fatal): {e}")
            return None

    # ---- Submit feedback -------------------------------------------------

    def submit_feedback(
        self,
        organization_id: str,
        proposal_id: str,
        rating: str,
        db: Session,
        feedback_text: Optional[str] = None,
        feedback_tags: Optional[List[str]] = None,
        action_taken: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ProposalFeedback:
        """Record user feedback on a generated proposal.

        After recording, automatically updates the org's aggregate learnings.

        Args:
            rating: "love", "okay", or "not_right"
            feedback_text: Optional free-text explanation
            feedback_tags: Optional tags like ["too_formal", "missing_pricing"]
            action_taken: "saved", "regenerated", or "ignored"
        """
        # Validate rating
        if rating not in ("love", "okay", "not_right"):
            raise ValueError(f"Invalid rating: {rating}. Must be love/okay/not_right")

        feedback = ProposalFeedback(
            id=uuid.uuid4(),
            organization_id=organization_id,
            proposal_id=proposal_id,
            rating=rating,
            feedback_text=feedback_text,
            feedback_tags=feedback_tags,
            action_taken=action_taken,
            created_by=user_id,
        )
        db.add(feedback)

        # Update aggregate learnings
        self._update_learnings_from_feedback(organization_id, rating, feedback_tags, db)

        db.flush()
        logger.info(
            f"Feedback recorded: {rating} on proposal {proposal_id} "
            f"for org {organization_id}"
        )
        return feedback

    # ---- Retrieve learnings for prompts ----------------------------------

    def get_learnings_for_prompt(
        self, organization_id: Optional[str], db: Session
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the org's learned preferences for injection into prompts.

        Returns a dict with keys that the prompt template can use:
          - common_issues: list of issues to avoid
          - learned_preferences: dict of preferences to follow
          - satisfaction_rate: percentage
          - total_proposals: count
        """
        if not organization_id:
            return None

        try:
            learnings = (
                db.query(ProposalLearnings)
                .filter(ProposalLearnings.organization_id == organization_id)
                .first()
            )
            if not learnings:
                return None

            # Only return if there's meaningful data
            if learnings.total_feedback_entries == 0:
                return None

            return {
                "common_issues": learnings.common_issues or {},
                "learned_preferences": learnings.learned_preferences or {},
                "satisfaction_rate": learnings.get_satisfaction_percentage(),
                "avg_rating": learnings.get_avg_rating(),
                "total_proposals": learnings.total_proposals_generated,
                "total_feedback": learnings.total_feedback_entries,
            }

        except Exception as e:
            logger.warning(f"Failed to retrieve learnings: {e}")
            return None

    # ---- LLM synthesis of learnings --------------------------------------

    async def synthesize_learnings(
        self, organization_id: str, db: Session
    ) -> Optional[Dict[str, Any]]:
        """Analyze all feedback for an org and produce learned_preferences.

        This is an LLM call that reads all feedback entries and produces
        a structured set of preferences:
          - What tone works best
          - What topics to emphasize
          - What to avoid
          - Common complaints and how to address them
          - Pricing patterns
          - Section length preferences

        Should be called periodically (e.g., after every 5 feedback entries)
        or on-demand via an API endpoint.
        """
        from openai import AsyncOpenAI

        # Gather all feedback for this org
        feedback_entries = (
            db.query(ProposalFeedback)
            .filter(ProposalFeedback.organization_id == organization_id)
            .order_by(ProposalFeedback.created_at.desc())
            .limit(50)  # Cap at last 50 entries
            .all()
        )

        if not feedback_entries:
            return None

        # Build feedback summary for the LLM
        feedback_lines = []
        for fb in feedback_entries:
            tags = ", ".join(fb.feedback_tags) if fb.feedback_tags else "none"
            feedback_lines.append(
                f"- Rating: {fb.rating} | Tags: {tags} | "
                f"Text: {fb.feedback_text or 'no comment'}"
            )
        feedback_text = "\n".join(feedback_lines)

        prompt = f"""You are analyzing user feedback on AI-generated proposals to extract actionable preferences for improving future proposals.

Here are the {len(feedback_entries)} most recent feedback entries for this organization:

{feedback_text}

Analyze these feedback entries and produce a JSON object with learned preferences:

{{
    "tone_preference": "formal|professional|casual|technical (what tone gets the best ratings)",
    "emphasis_areas": ["list of topics that should be emphasized based on positive feedback"],
    "avoid_areas": ["list of topics or approaches that received negative feedback"],
    "pricing_guidance": "any learned pricing preferences (value-based vs competitive, etc.)",
    "length_preference": "brief|standard|detailed (based on feedback patterns)",
    "common_complaints": ["specific recurring complaints to address proactively"],
    "winning_patterns": ["approaches or phrases that received positive feedback"],
    "section_specific_notes": {{
        "executive_summary": "any notes for this section",
        "proposed_solution": "any notes for this section"
    }}
}}

Return ONLY valid JSON."""

        try:
            async with AsyncOpenAI(api_key=self.settings.openai_api_key) as client:
                response = await client.chat.completions.create(
                    model=self.settings.openai_model,
                    max_tokens=1500,
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}],
                )

            result = json.loads(response.choices[0].message.content or "{}")

            # Update the learnings record
            learnings = (
                db.query(ProposalLearnings)
                .filter(ProposalLearnings.organization_id == organization_id)
                .first()
            )
            if learnings:
                learnings.learned_preferences = result
                learnings.last_feedback_at = datetime.utcnow()
            else:
                learnings = ProposalLearnings(
                    id=uuid.uuid4(),
                    organization_id=organization_id,
                    learned_preferences=result,
                    last_feedback_at=datetime.utcnow(),
                )
                db.add(learnings)

            db.flush()
            logger.info(f"Synthesized learnings for org {organization_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to synthesize learnings: {e}")
            return None

    # ---- Internal helpers ------------------------------------------------

    def _increment_generation_count(
        self, organization_id: str, db: Session
    ) -> None:
        """Increment the org's total_proposals_generated counter."""
        try:
            learnings = (
                db.query(ProposalLearnings)
                .filter(ProposalLearnings.organization_id == organization_id)
                .first()
            )
            if learnings:
                learnings.total_proposals_generated = (
                    learnings.total_proposals_generated or 0
                ) + 1
            else:
                learnings = ProposalLearnings(
                    id=uuid.uuid4(),
                    organization_id=organization_id,
                    total_proposals_generated=1,
                )
                db.add(learnings)
        except Exception as e:
            logger.warning(f"Failed to increment generation count: {e}")

    def _update_learnings_from_feedback(
        self,
        organization_id: str,
        rating: str,
        feedback_tags: Optional[List[str]],
        db: Session,
    ) -> None:
        """Update aggregate counters from a single feedback entry."""
        try:
            learnings = (
                db.query(ProposalLearnings)
                .filter(ProposalLearnings.organization_id == organization_id)
                .first()
            )
            if not learnings:
                learnings = ProposalLearnings(
                    id=uuid.uuid4(),
                    organization_id=organization_id,
                )
                db.add(learnings)

            # Update counters
            learnings.total_feedback_entries = (
                learnings.total_feedback_entries or 0
            ) + 1

            if rating == "love":
                learnings.love_count = (learnings.love_count or 0) + 1
            elif rating == "okay":
                learnings.okay_count = (learnings.okay_count or 0) + 1
            elif rating == "not_right":
                learnings.not_right_count = (learnings.not_right_count or 0) + 1

            # Update common issues from tags
            if feedback_tags:
                issues = learnings.common_issues or {}
                for tag in feedback_tags:
                    issues[tag] = issues.get(tag, 0) + 1
                learnings.common_issues = issues

            learnings.last_feedback_at = datetime.utcnow()

        except Exception as e:
            logger.warning(f"Failed to update learnings: {e}")
