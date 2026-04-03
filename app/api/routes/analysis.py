"""Document analysis endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Project, UploadedFile, AnalysisResult
from app.schemas.analysis import AnalysisResponse
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES
from app.api.deps import analysis_service

router = APIRouter(prefix="/api/projects", tags=["analysis"])


@router.post("/{project_id}/analyze", response_model=SuccessResponse)
async def analyze_document(
    project_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Analyze uploaded procurement document."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Get latest uploaded file
        uploaded_file = db.query(UploadedFile).filter(
            UploadedFile.project_id == project_id
        ).order_by(UploadedFile.created_at.desc()).first()

        if not uploaded_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file uploaded for this project"
            )

        if not uploaded_file.extracted_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extracted text found"
            )

        # Run analysis
        try:
            analysis_result = await analysis_service.analyze_document(
                str(project_id),
                uploaded_file.extracted_text,
                db
            )

            return create_success_response(
                message=MESSAGES["ANALYSIS_COMPLETED"],
                data=AnalysisResponse.from_orm(analysis_result).model_dump()
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Analysis failed: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["INTERNAL_ERROR"]
        )


@router.get("/{project_id}/analysis", response_model=SuccessResponse)
async def get_analysis(
    project_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Get analysis results for a project."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Get analysis result
        analysis = analysis_service.get_analysis_result(str(project_id), db)

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found for this project"
            )

        return create_success_response(
            message="Analysis retrieved successfully",
            data=AnalysisResponse.from_orm(analysis).model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )
