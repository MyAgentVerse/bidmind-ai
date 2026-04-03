"""File upload endpoints."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import UploadedFile, Project
from app.schemas.upload import FileUploadResponse, FileListResponse
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES
from app.utils.file_validators import validate_file_type, validate_file_size, validate_filename_safety
from app.api.deps import storage_service, file_parser_service

router = APIRouter(prefix="/api/projects", tags=["uploads"])


@router.post("/{project_id}/upload", response_model=SuccessResponse)
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Upload a procurement document."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Validate filename
        is_safe, error_msg = validate_filename_safety(file.filename)
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Validate file type
        is_valid, error_msg = validate_file_type(file.filename, file.content_type)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Read file content
        file_content = await file.read()

        # Validate file size
        is_valid, error_msg = validate_file_size(len(file_content))
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Validate file content
        extension = file.filename.split('.')[-1].lower()
        if not file_parser_service.validate_file_content(file_content, extension):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content is invalid or corrupted"
            )

        # Save file to storage
        stored_filename, file_path = storage_service.save_file(
            file_content,
            file.filename
        )

        # Extract text from file
        try:
            extracted_text, file_type = file_parser_service.parse_file(file_path)
        except Exception as e:
            import logging
            logging.error(f"File parsing error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File parsing error: {str(e)}"
            )

        # Create UploadedFile record
        uploaded_file = UploadedFile(
            project_id=project_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=file_path,
            mime_type=file.content_type,
            file_size=len(file_content),
            extracted_text=extracted_text
        )

        # Save to database
        db.add(uploaded_file)

        # Update project status
        project.status = "file_uploaded"

        db.commit()
        db.refresh(uploaded_file)

        return create_success_response(
            message=MESSAGES["FILE_UPLOADED"],
            data=FileUploadResponse.from_orm(uploaded_file).model_dump()
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["INTERNAL_ERROR"]
        )


@router.get("/{project_id}/files", response_model=SuccessResponse)
async def list_project_files(
    project_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """List all files for a project."""
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Get files
        files = db.query(UploadedFile).filter(
            UploadedFile.project_id == project_id
        ).all()

        return create_success_response(
            message="Files retrieved successfully",
            data={
                "files": [FileUploadResponse.from_orm(f).model_dump() for f in files],
                "total": len(files)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )
