"""Project management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, create_error_response, MESSAGES

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Create a new project."""
    try:
        # Create new project
        new_project = Project(
            title=project.title,
            description=project.description
        )

        # Save to database
        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        return create_success_response(
            message=MESSAGES["PROJECT_CREATED"],
            data=ProjectResponse.from_orm(new_project).model_dump()
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )


@router.get("/{project_id}", response_model=SuccessResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Get a specific project."""
    try:
        # Query project
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        return create_success_response(
            message="Project retrieved successfully",
            data=ProjectResponse.from_orm(project).model_dump()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )


@router.get("", response_model=SuccessResponse)
async def list_projects(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> SuccessResponse:
    """List all projects."""
    try:
        # Query projects
        projects = db.query(Project).offset(skip).limit(limit).all()
        total = db.query(Project).count()

        return create_success_response(
            message="Projects retrieved successfully",
            data={
                "projects": [ProjectResponse.from_orm(p).model_dump() for p in projects],
                "total": total
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )


@router.patch("/{project_id}", response_model=SuccessResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Update a project."""
    try:
        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Update fields
        update_data = project_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        # Save to database
        db.commit()
        db.refresh(project)

        return create_success_response(
            message=MESSAGES["PROJECT_UPDATED"],
            data=ProjectResponse.from_orm(project).model_dump()
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )


@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Delete a project."""
    try:
        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MESSAGES["PROJECT_NOT_FOUND"]
            )

        # Delete from database
        db.delete(project)
        db.commit()

        return create_success_response(
            message="Project deleted successfully"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MESSAGES["DATABASE_ERROR"]
        )
