"""Document analysis endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Project, UploadedFile, AnalysisResult
from app.schemas.analysis import AnalysisResponse
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES
from app.api.deps import analysis_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    """Request model for document analysis with optional company_id."""
    company_id: Optional[str] = None


@router.post("/{project_id}/analyze", response_model=SuccessResponse)
async def analyze_document(
    project_id: str,
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Analyze the full bid package for a project.

    Phase 1, Step 2: this now combines **every** uploaded file for the
    project (main RFP + addenda + SOW + pricing template + etc.) into a
    single multi-document analysis pass, instead of silently picking only
    the most recent file.
    """
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Get ALL uploaded files for this project, oldest first.
        # The first uploaded file is treated as the primary document; later
        # files are addenda / attachments.
        uploaded_files = db.query(UploadedFile).filter(
            UploadedFile.project_id == project_id
        ).order_by(UploadedFile.created_at.asc()).all()

        if not uploaded_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file uploaded for this project"
            )

        # Filter to files that actually have extracted text
        files_with_text = [
            (f.original_filename, f.extracted_text)
            for f in uploaded_files
            if f.extracted_text and f.extracted_text.strip()
        ]

        if not files_with_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extracted text found in any uploaded file"
            )

        # Combine all files into one analysis-ready document
        combined_text, source_filenames = analysis_service.combine_files_for_analysis(
            files_with_text
        )

        logger.info(
            f"Analyzing {len(source_filenames)} file(s) for project {project_id}: "
            f"{source_filenames}"
        )

        # Run analysis with company context
        # Use company_id from request body if provided, otherwise from project
        company_id = request.company_id or project.company_id

        try:
            analysis_result = await analysis_service.analyze_document(
                str(project_id),
                combined_text,
                db,
                company_id=company_id,
                source_files=source_filenames,
            )

            if company_id:
                logger.info(f"Analysis completed with company context for project {project_id}")

            return create_success_response(
                message=MESSAGES["ANALYSIS_COMPLETED"],
                data=AnalysisResponse.from_analysis_result(analysis_result).model_dump()
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Analysis failed: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_document: {str(e)}")
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
            data=AnalysisResponse.from_analysis_result(analysis).model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )
