"""
ProposalAnalyticsService
Processes feedback and updates learning analytics
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from datetime import datetime
from collections import Counter
import logging

from app.models.proposal_feedback import ProposalFeedback
from app.models.proposal_learnings import ProposalLearnings
from app.models.proposal_generation import ProposalGeneration

logger = logging.getLogger(__name__)


class ProposalAnalyticsService:
    """
    Service for processing feedback and calculating AI learnings.
    Updates ProposalLearnings table whenever feedback is received.
    """

    def __init__(self, db: Session):
        self.db = db

    async def update_learnings(self, org_id: UUID) -> ProposalLearnings:
        """
        Recalculate and update all learnings for an organization.
        Called whenever new feedback is submitted.
        """
        # Get or create learnings record
        learnings = self.db.query(ProposalLearnings).filter(
            ProposalLearnings.organization_id == org_id
        ).first()

        if not learnings:
            learnings = ProposalLearnings(organization_id=org_id)
            self.db.add(learnings)

        # Get all feedback for this organization
        feedback_list = self.db.query(ProposalFeedback).filter(
            ProposalFeedback.organization_id == org_id
        ).all()

        # Reset counters
        learnings.total_proposals_generated = self.db.query(ProposalGeneration).filter(
            ProposalGeneration.organization_id == org_id
        ).count()

        learnings.total_feedback_entries = len(feedback_list)

        learnings.total_regenerations = self.db.query(ProposalGeneration).filter(
            ProposalGeneration.organization_id == org_id,
            ProposalGeneration.parent_proposal_id != None
        ).count()

        # Count ratings
        learnings.love_count = sum(1 for f in feedback_list if f.rating == "love")
        learnings.okay_count = sum(1 for f in feedback_list if f.rating == "okay")
        learnings.not_right_count = sum(1 for f in feedback_list if f.rating == "not_right")

        # Calculate common issues
        learnings.common_issues = self._calculate_common_issues(feedback_list)

        # Calculate learned preferences
        learnings.learned_preferences = self._calculate_learned_preferences(feedback_list)

        # Update timestamp
        learnings.last_updated = datetime.utcnow()
        if feedback_list:
            learnings.last_feedback_at = max(f.created_at for f in feedback_list)

        self.db.commit()
        self.db.refresh(learnings)

        logger.info(f"Updated learnings for org {org_id}: {learnings.total_feedback_entries} feedback entries")

        return learnings

    def _calculate_common_issues(self, feedback_list: list) -> dict:
        """Calculate which issues are most common"""
        all_tags = []
        for feedback in feedback_list:
            if feedback.feedback_tags:
                all_tags.extend(feedback.feedback_tags)

        if not all_tags:
            return {}

        # Count occurrences
        tag_counts = Counter(all_tags)

        # Return as dict sorted by count
        return dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

    def _calculate_learned_preferences(self, feedback_list: list) -> dict:
        """Extract learned preferences from feedback patterns"""
        if not feedback_list:
            return {}

        preferences = {}

        # Analyze feedback text for keywords
        feedback_texts = [f.feedback_text for f in feedback_list if f.feedback_text]

        if feedback_texts:
            # Check for pricing preferences
            if any(phrase in " ".join(feedback_texts).lower() for phrase in ["pricing", "budget", "cost"]):
                # Determine pricing model preference from tags
                pricing_related = sum(1 for f in feedback_list if f.feedback_tags and any("pricing" in tag for tag in f.feedback_tags))
                if pricing_related > 0:
                    preferences["pricing_emphasis"] = "high"

            # Check for timeline preferences
            if any(phrase in " ".join(feedback_texts).lower() for phrase in ["timeline", "weeks", "duration", "schedule"]):
                preferences["timeline_emphasis"] = "important"

            # Check for tone preferences
            if any(phrase in " ".join(feedback_texts).lower() for phrase in ["formal", "casual", "technical", "tone"]):
                preferences["tone_mentioned"] = True

        # Analyze what they DON'T want (not_right ratings)
        not_right_feedback = [f for f in feedback_list if f.rating == "not_right"]
        if not_right_feedback:
            not_right_tags = []
            for f in not_right_feedback:
                if f.feedback_tags:
                    not_right_tags.extend(f.feedback_tags)
            if not_right_tags:
                preferences["avoid_issues"] = list(set(not_right_tags))

        # Analyze what they DO want (love ratings)
        love_feedback = [f for f in feedback_list if f.rating == "love"]
        if love_feedback:
            love_tags = []
            for f in love_feedback:
                if f.feedback_tags:
                    love_tags.extend(f.feedback_tags)
            if love_tags:
                tag_counts = Counter(love_tags)
                preferences["preferred_style"] = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

        # Calculate satisfaction
        total = len(feedback_list)
        positive = sum(1 for f in feedback_list if f.rating in ["love", "okay"])
        if total > 0:
            preferences["satisfaction_rate"] = round((positive / total) * 100, 1)

        return preferences if preferences else None

    def get_learning_summary(self, org_id: UUID) -> dict:
        """Get human-readable summary of what the AI has learned"""
        learnings = self.db.query(ProposalLearnings).filter(
            ProposalLearnings.organization_id == org_id
        ).first()

        if not learnings:
            return {}

        summary = {
            "total_proposals": learnings.total_proposals_generated,
            "total_feedback": learnings.total_feedback_entries,
            "satisfaction": f"{learnings.get_satisfaction_percentage()}%",
            "avg_rating": learnings.get_avg_rating(),
            "common_issues": learnings.common_issues or {},
            "learned_preferences": learnings.learned_preferences or {},
        }

        # Create human-readable insights
        insights = []

        if learnings.common_issues:
            top_issue = list(learnings.common_issues.items())[0]
            insights.append(f"Most common feedback: {top_issue[0]} ({top_issue[1]} times)")

        if learnings.learned_preferences and "avoid_issues" in learnings.learned_preferences:
            insights.append(f"Should avoid: {', '.join(learnings.learned_preferences['avoid_issues'][:3])}")

        if learnings.get_satisfaction_percentage() >= 80:
            insights.append("AI is generating proposals that satisfy the organization!")

        summary["insights"] = insights

        return summary
