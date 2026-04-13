"""Proposal generation and management endpoints."""

import asyncio
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Project, ProposalDraft, Organization
from app.models.proposal_generation import ProposalGeneration
from app.models.proposal_feedback import ProposalFeedback
from app.services import subscription_service
from app.schemas.proposal import ProposalResponse, ProposalUpdate, ProposalSectionUpdate
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES
from app.api.deps import proposal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["proposal"])


class ProposalRequest(BaseModel):
    """Request model for proposal generation with optional company_id."""
    company_id: Optional[str] = None


@router.post("/{project_id}/generate-proposal", response_model=SuccessResponse)
async def generate_proposal(
    project_id: str,
    request: ProposalRequest,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Generate proposal draft from analysis results with company context."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Subscription: check proposal usage limit
        if project.organization_id:
            org = db.query(Organization).filter(Organization.id == project.organization_id).first()
            if org:
                subscription_service.check_usage_limit(org, "proposal_generated", db)

        # Run proposal generation with company context
        # Use company_id from request body if provided, otherwise from project
        company_id = request.company_id or project.company_id
        
        try:
            proposal = await proposal_service.generate_proposal(
                str(project_id),
                db,
                company_id=company_id
            )

            # Subscription: increment usage after successful generation
            if project.organization_id:
                subscription_service.increment_usage(project.organization_id, "proposal_generated", db)

            if company_id:
                logger.info(f"Proposal generated with company context for project {project_id}")

            return create_success_response(
                message=MESSAGES["PROPOSAL_GENERATED"],
                data=ProposalResponse.from_orm(proposal).model_dump()
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_proposal: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proposal generation failed: {type(e).__name__}: {str(e)}"
        )


@router.post("/{project_id}/proposal", response_model=SuccessResponse)
async def generate_proposal_endpoint(
    project_id: str,
    request: ProposalRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Generate proposal draft from analysis results (async background task with company context)."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Subscription: check proposal usage limit
        if project.organization_id:
            org = db.query(Organization).filter(Organization.id == project.organization_id).first()
            if org:
                subscription_service.check_usage_limit(org, "proposal_generated", db)

        # Verify analysis exists
        from app.models import AnalysisResult
        analysis = db.query(AnalysisResult).filter(
            AnalysisResult.project_id == project_id
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No analysis results found. Please analyze the document first."
            )

        # Start proposal generation in background with company context
        # Use company_id from request body if provided, otherwise from project
        company_id = request.company_id or project.company_id
        background_tasks.add_task(
            proposal_service.generate_proposal_background,
            str(project_id),
            company_id=company_id
        )

        logger.info(f"Started background proposal generation for project {project_id}")

        return create_success_response(
            message="Proposal generation started. Check back in a moment.",
            data={"status": "generating", "project_id": project_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting proposal generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["INTERNAL_ERROR"]
        )


@router.get("/{project_id}/proposal", response_model=SuccessResponse)
async def get_proposal(
    project_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Get proposal draft for a project."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Get proposal
        proposal = proposal_service.get_proposal_draft(str(project_id), db)

        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found for this project"
            )

        return create_success_response(
            message="Proposal retrieved successfully",
            data=ProposalResponse.from_orm(proposal).model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_proposal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )


@router.patch("/{project_id}/proposal", response_model=SuccessResponse)
async def update_proposal_section(
    project_id: str,
    section_update: ProposalSectionUpdate,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Update a single proposal section."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Update section
        try:
            proposal = proposal_service.update_proposal_section(
                str(project_id),
                section_update.section_name,
                section_update.text,
                db
            )

            return create_success_response(
                message=MESSAGES["PROPOSAL_UPDATED"],
                data=ProposalResponse.from_orm(proposal).model_dump()
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_proposal_section: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )


@router.put("/{project_id}/proposal", response_model=SuccessResponse)
async def update_full_proposal(
    project_id: str,
    proposal_update: ProposalUpdate,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Update multiple proposal sections at once."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Get proposal
        proposal = proposal_service.get_proposal_draft(str(project_id), db)
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found for this project"
            )

        # Update fields
        update_data = proposal_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(proposal, field, value)

        # Save
        db.commit()
        db.refresh(proposal)

        return create_success_response(
            message=MESSAGES["PROPOSAL_UPDATED"],
            data=ProposalResponse.from_orm(proposal).model_dump()
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in update_full_proposal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )


@router.post("/{project_id}/proposal/feedback", response_model=dict)
async def submit_project_feedback(
    project_id: str,
    feedback_data: dict,
    db: Session = Depends(get_db)
):
    """Submit feedback on a project's proposal.

    This endpoint finds (or creates) the ProposalGeneration record
    for the project so the frontend doesn't need to know the
    proposal_generation ID.
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Find the latest ProposalGeneration for this project's org
        generation = None
        if project.organization_id:
            generation = (
                db.query(ProposalGeneration)
                .filter(ProposalGeneration.organization_id == project.organization_id)
                .order_by(ProposalGeneration.created_at.desc())
                .first()
            )

        # If no generation record exists, create one from the proposal draft
        if not generation:
            draft = proposal_service.get_proposal_draft(str(project_id), db)
            if not draft:
                raise HTTPException(status_code=404, detail="Proposal not found")

            content = "\n\n".join(
                f"## {s.replace('_', ' ').title()}\n\n{getattr(draft, s, '') or ''}"
                for s in ProposalDraft.SECTION_ORDER
                if getattr(draft, s, None)
            )
            generation = ProposalGeneration(
                id=uuid.uuid4(),
                organization_id=project.organization_id,
                proposal_title=project.title or "Untitled",
                proposal_type="bid",
                proposal_content=content,
                status="draft",
            )
            db.add(generation)
            db.commit()

        # Map frontend rating names to DB values
        rating_map = {"great": "love", "love": "love", "okay": "okay", "not_right": "not_right"}
        rating = rating_map.get(feedback_data.get("rating", "").lower(), feedback_data.get("rating", "okay"))

        feedback = ProposalFeedback(
            id=uuid.uuid4(),
            organization_id=generation.organization_id,
            proposal_id=generation.id,
            rating=rating,
            feedback_text=feedback_data.get("feedback_text"),
            feedback_tags=feedback_data.get("feedback_tags"),
            action_taken=feedback_data.get("action_taken", "saved"),
        )
        db.add(feedback)
        db.commit()

        logger.info(f"Feedback submitted for project {project_id}: {rating}")

        return {
            "success": True,
            "message": "Feedback submitted successfully",
            "data": {"id": str(feedback.id), "rating": rating}
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")
