"""Proposal generation and management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Project, ProposalDraft
from app.schemas.proposal import ProposalResponse, ProposalUpdate, ProposalSectionUpdate
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES
from app.api.deps import proposal_service

router = APIRouter(prefix="/api/projects", tags=["proposal"])


@router.post("/{project_id}/generate-proposal", response_model=SuccessResponse)
async def generate_proposal(
    project_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Generate proposal draft from analysis results."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Run proposal generation
        try:
            proposal = await proposal_service.generate_proposal(str(project_id), db)

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["INTERNAL_ERROR"]
        )


@router.post("/{project_id}/proposal", response_model=SuccessResponse)
async def generate_proposal_endpoint(
    project_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Generate proposal draft from analysis results."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Run proposal generation
        try:
            proposal = await proposal_service.generate_proposal(str(project_id), db)

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )
