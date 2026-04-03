"""Export endpoints for generating downloadable files."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Project, ProposalDraft
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES
from app.api.deps import export_service, proposal_service

router = APIRouter(prefix="/api/projects", tags=["export"])


@router.get("/{project_id}/export/docx")
async def export_docx(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Download proposal as DOCX file."""
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

        # Generate DOCX
        try:
            filepath = export_service.generate_docx(
                proposal,
                project_title=project.title,
                db=db
            )

            # Get filename
            filename = export_service.get_export_filename(project.title)

            return FileResponse(
                path=filepath,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=filename
            )

        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="DOCX generation is not available"
            )
        except IOError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=MESSAGES["EXPORT_ERROR"]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["INTERNAL_ERROR"]
        )
