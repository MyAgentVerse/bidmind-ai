"""AI-assisted editing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Project
from app.schemas.ai_edit import AIEditRequest, AIEditResponse
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES
from app.api.deps import ai_edit_service

router = APIRouter(prefix="/api/projects", tags=["ai-edit"])


@router.post("/{project_id}/proposal/ai-edit", response_model=SuccessResponse)
async def ai_edit_section(
    project_id: str,
    edit_request: AIEditRequest,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Use AI to edit a proposal section."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Perform AI edit
        try:
            edited_text, edit_history = await ai_edit_service.edit_section(
                str(project_id),
                edit_request.section_name,
                edit_request.current_text,
                edit_request.instruction,
                db,
                save_to_proposal=True
            )

            return create_success_response(
                message=MESSAGES["AI_EDIT_COMPLETED"],
                data={
                    "section_name": edit_request.section_name,
                    "instruction": edit_request.instruction,
                    "original_text": edit_request.current_text,
                    "edited_text": edited_text,
                    "created_at": edit_history.created_at.isoformat()
                }
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=MESSAGES["AI_ERROR"]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["INTERNAL_ERROR"]
        )


@router.get("/{project_id}/proposal/edit-history", response_model=SuccessResponse)
async def get_edit_history(
    project_id: str,
    section_name: str = None,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Get AI edit history for a project."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Get edit history
        if section_name:
            edits = ai_edit_service.get_section_edit_history(str(project_id), section_name, db)
        else:
            edits = ai_edit_service.get_edit_history(str(project_id), db)

        # Format response
        edit_data = [
            {
                "id": str(edit.id),
                "section_name": edit.section_name,
                "instruction": edit.instruction,
                "created_at": edit.created_at.isoformat()
            }
            for edit in edits
        ]

        return create_success_response(
            message="Edit history retrieved successfully",
            data={
                "edits": edit_data,
                "total": len(edits)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )
