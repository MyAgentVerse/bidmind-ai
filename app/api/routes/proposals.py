"""
Proposal Generation and Feedback API Routes
Endpoints for managing proposals and feedback
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.proposal_generation import ProposalGeneration
from app.models.proposal_feedback import ProposalFeedback
from app.models.proposal_preferences import ProposalPreferences
from app.models.proposal_learnings import ProposalLearnings
from app.api.routes.organizations import check_org_access
from app.services import subscription_service
from app.services.proposal_analytics import ProposalAnalyticsService

router = APIRouter(prefix="/api/proposals", tags=["proposals"])

# ==================== PROPOSAL PREFERENCES ====================

@router.get("/preferences/{org_id}", response_model=dict)
async def get_proposal_preferences(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get organization's proposal writing preferences"""
    check_org_access(current_user, str(org_id), db)

    prefs = db.query(ProposalPreferences).filter(
        ProposalPreferences.organization_id == org_id
    ).first()

    if not prefs:
        # Return empty/default preferences
        return {
            "organization_id": str(org_id),
            "tone_level": 3,
            "brand_voice_tags": [],
            "language_complexity": "standard",
            "company_jargon": "",
            "must_include": [],
            "do_not_include": "",
            "focus_areas": {},
            "section_lengths": {},
            "custom_sections": [],
            "section_order": [],
        }

    return prefs.to_dict()


@router.post("/preferences/{org_id}", response_model=dict)
async def update_proposal_preferences(
    org_id: UUID,
    preferences: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update organization's proposal writing preferences"""
    check_org_access(current_user, str(org_id), db)

    prefs = db.query(ProposalPreferences).filter(
        ProposalPreferences.organization_id == org_id
    ).first()

    if not prefs:
        prefs = ProposalPreferences(
            organization_id=org_id,
            updated_by=current_user.id
        )
        db.add(prefs)

    # Update fields
    for key, value in preferences.items():
        if hasattr(prefs, key):
            setattr(prefs, key, value)

    prefs.updated_at = datetime.utcnow()
    prefs.updated_by = current_user.id

    db.commit()
    db.refresh(prefs)

    return prefs.to_dict()


# ==================== PROPOSALS ====================

@router.post("/generate", response_model=dict)
async def create_proposal(
    org_id: UUID,
    proposal_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new AI-generated proposal"""
    check_org_access(current_user, str(org_id), db)

    proposal = ProposalGeneration(
        organization_id=org_id,
        created_by=current_user.id,
        proposal_title=proposal_data.get("proposal_title", "Untitled Proposal"),
        proposal_type=proposal_data.get("proposal_type", "general"),
        proposal_content=proposal_data.get("proposal_content"),
        proposal_metadata=proposal_data.get("proposal_metadata"),
        writing_preferences=proposal_data.get("writing_preferences"),
        status="draft"
    )

    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    return proposal.to_dict()


@router.get("/list/{org_id}", response_model=list)
async def list_proposals(
    org_id: UUID,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all proposals for organization"""
    check_org_access(current_user, str(org_id), db)

    proposals = db.query(ProposalGeneration).filter(
        ProposalGeneration.organization_id == org_id
    ).order_by(
        ProposalGeneration.created_at.desc()
    ).offset(offset).limit(limit).all()

    return [p.to_dict() for p in proposals]


@router.get("/{proposal_id}", response_model=dict)
async def get_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full proposal details"""
    proposal = db.query(ProposalGeneration).filter(
        ProposalGeneration.id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    check_org_access(current_user, str(proposal.organization_id), db)

    return proposal.to_dict_full()


# ==================== FEEDBACK ====================

@router.post("/{proposal_id}/feedback", response_model=dict)
async def submit_feedback(
    proposal_id: UUID,
    feedback_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback on a proposal.
    Feedback format:
    {
        "rating": "love|okay|not_right",
        "feedback_text": "Optional text feedback",
        "feedback_tags": ["pricing_high", "timeline_aggressive", ...],
        "action_taken": "saved|regenerated"
    }
    """
    proposal = db.query(ProposalGeneration).filter(
        ProposalGeneration.id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    check_org_access(current_user, str(proposal.organization_id), db)

    # Pro-only: feedback drives the learning loop
    org = db.query(Organization).filter(Organization.id == proposal.organization_id).first()
    subscription_service.check_feature_access(org, "learning_loop")

    # Create feedback
    feedback = ProposalFeedback(
        organization_id=proposal.organization_id,
        proposal_id=proposal_id,
        rating=feedback_data.get("rating"),
        feedback_text=feedback_data.get("feedback_text"),
        feedback_tags=feedback_data.get("feedback_tags"),
        action_taken=feedback_data.get("action_taken", "saved"),
        created_by=current_user.id
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    # Update analytics
    analytics_service = ProposalAnalyticsService(db)
    await analytics_service.update_learnings(proposal.organization_id)

    return feedback.to_dict()


@router.get("/{proposal_id}/feedback", response_model=list)
async def get_proposal_feedback(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all feedback for a proposal"""
    proposal = db.query(ProposalGeneration).filter(
        ProposalGeneration.id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    check_org_access(current_user, str(proposal.organization_id), db)

    feedback_list = db.query(ProposalFeedback).filter(
        ProposalFeedback.proposal_id == proposal_id
    ).order_by(ProposalFeedback.created_at.desc()).all()

    return [f.to_dict() for f in feedback_list]


@router.post("/{proposal_id}/regenerate", response_model=dict)
async def regenerate_proposal(
    proposal_id: UUID,
    regeneration_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate a proposal based on feedback.
    Updates the feedback record with the regenerated proposal.
    """
    original_proposal = db.query(ProposalGeneration).filter(
        ProposalGeneration.id == proposal_id
    ).first()

    if not original_proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    check_org_access(current_user, str(original_proposal.organization_id), db)

    # Create new proposal generation
    new_proposal = ProposalGeneration(
        organization_id=original_proposal.organization_id,
        created_by=current_user.id,
        proposal_title=regeneration_data.get("proposal_title", original_proposal.proposal_title),
        proposal_type=original_proposal.proposal_type,
        proposal_content=regeneration_data.get("proposal_content"),
        proposal_metadata=regeneration_data.get("proposal_metadata"),
        writing_preferences=regeneration_data.get("writing_preferences"),
        status="draft",
        parent_proposal_id=proposal_id
    )

    db.add(new_proposal)
    db.commit()
    db.refresh(new_proposal)

    # Update feedback if feedback_id provided
    if "feedback_id" in regeneration_data:
        feedback = db.query(ProposalFeedback).filter(
            ProposalFeedback.id == regeneration_data["feedback_id"]
        ).first()
        if feedback:
            feedback.regenerated_proposal_id = new_proposal.id
            feedback.action_taken = "regenerated"
            db.commit()

    # Update analytics
    analytics_service = ProposalAnalyticsService(db)
    await analytics_service.update_learnings(original_proposal.organization_id)

    return new_proposal.to_dict()


# ==================== ANALYTICS / LEARNINGS ====================

@router.get("/analytics/{org_id}", response_model=dict)
async def get_proposal_analytics(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI learning analytics for organization"""
    try:
        check_org_access(current_user, str(org_id), db)

        learnings = db.query(ProposalLearnings).filter(
            ProposalLearnings.organization_id == org_id
        ).first()

        if not learnings:
            # Create default learnings if doesn't exist
            learnings = ProposalLearnings(organization_id=org_id)
            db.add(learnings)
            db.commit()
            db.refresh(learnings)

        analytics_dict = learnings.to_dict()
        analytics_dict["avg_rating"] = learnings.get_avg_rating()
        analytics_dict["satisfaction_percentage"] = learnings.get_satisfaction_percentage()

        return analytics_dict

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Analytics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")


@router.get("/feedback/history/{org_id}", response_model=list)
async def get_feedback_history(
    org_id: UUID,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent feedback entries for organization"""
    check_org_access(current_user, str(org_id), db)

    feedback_list = db.query(ProposalFeedback).filter(
        ProposalFeedback.organization_id == org_id
    ).order_by(ProposalFeedback.created_at.desc()).offset(offset).limit(limit).all()

    return [f.to_dict() for f in feedback_list]


@router.post("/analytics/recalculate/{org_id}", response_model=dict)
async def recalculate_analytics(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Recalculate all analytics for organization (manual trigger)"""
    check_org_access(current_user, str(org_id), db)

    analytics_service = ProposalAnalyticsService(db)
    await analytics_service.update_learnings(org_id)

    learnings = db.query(ProposalLearnings).filter(
        ProposalLearnings.organization_id == org_id
    ).first()

    return learnings.to_dict()
