"""Authenticated project management endpoints with multi-tenant support."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User, Project, Organization, UserOrganization
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/projects", tags=["projects-authenticated"])


@router.get("", response_model=dict)
async def list_projects(
    org_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List projects accessible to current user.
    Optionally filter by organization ID if user is member.

    Args:
        org_id: Optional organization ID to filter
        current_user: Current authenticated user

    Returns:
        List of accessible projects
    """
    try:
        # If org_id provided, verify user is member
        if org_id:
            user_org = db.query(UserOrganization).filter(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == org_id
            ).first()

            if not user_org:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this organization"
                )

            # Get projects for this organization
            # Assuming Project model has organization_id field
            projects = db.query(Project).filter(
                Project.organization_id == org_id
            ).all()
        else:
            # Get all projects from user's organizations
            user_orgs = db.query(UserOrganization).filter(
                UserOrganization.user_id == current_user.id
            ).all()

            org_ids = [uo.organization_id for uo in user_orgs]
            projects = db.query(Project).filter(
                Project.organization_id.in_(org_ids)
            ).all() if org_ids else []

        return {
            "projects": [
                {
                    "id": str(project.id),
                    "title": project.title,
                    "description": project.description,
                    "created_at": project.created_at.isoformat() if hasattr(project, 'created_at') else None
                }
                for project in projects
            ],
            "count": len(projects)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list projects"
        )


@router.post("", response_model=dict)
async def create_project(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new project in organization.

    Args:
        request: Dict with 'title', 'description', 'organization_id'
        current_user: Current authenticated user

    Returns:
        Created project details
    """
    try:
        org_id = request.get("organization_id")
        title = request.get("title")
        description = request.get("description", "")

        if not org_id or not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="organization_id and title are required"
            )

        # Verify user has access to organization
        user_org = db.query(UserOrganization).filter(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == org_id
        ).first()

        if not user_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this organization"
            )

        # Create project
        project = Project(
            title=title,
            description=description,
            organization_id=org_id
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        logger.info(f"Project created: {title} in organization {org_id}")

        return {
            "id": str(project.id),
            "title": project.title,
            "description": project.description,
            "organization_id": str(org_id),
            "created_at": project.created_at.isoformat() if hasattr(project, 'created_at') else None,
            "message": "Project created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/{project_id}", response_model=dict)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get project details. User must be member of project's organization.

    Args:
        project_id: Project ID

    Returns:
        Project details
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Verify access to project's organization
        user_org = db.query(UserOrganization).filter(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == project.organization_id
        ).first()

        if not user_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )

        return {
            "id": str(project.id),
            "title": project.title,
            "description": project.description,
            "organization_id": str(project.organization_id),
            "created_at": project.created_at.isoformat() if hasattr(project, 'created_at') else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project"
        )


@router.put("/{project_id}", response_model=dict)
async def update_project(
    project_id: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update project details. User must be admin/owner of project's organization.

    Args:
        project_id: Project ID
        request: Dict with fields to update

    Returns:
        Updated project details
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Verify access and role
        user_org = db.query(UserOrganization).filter(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == project.organization_id
        ).first()

        if not user_org or user_org.role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this project"
            )

        # Update fields
        if "title" in request:
            project.title = request["title"]
        if "description" in request:
            project.description = request["description"]

        db.commit()
        db.refresh(project)

        logger.info(f"Project updated: {project.title}")

        return {
            "id": str(project.id),
            "title": project.title,
            "description": project.description,
            "organization_id": str(project.organization_id),
            "message": "Project updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )


@router.delete("/{project_id}", response_model=dict)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a project. User must be owner of project's organization.

    Args:
        project_id: Project ID

    Returns:
        Success message
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Verify ownership
        user_org = db.query(UserOrganization).filter(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == project.organization_id,
            UserOrganization.role == "owner"
        ).first()

        if not user_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owner can delete projects"
            )

        db.delete(project)
        db.commit()

        logger.info(f"Project deleted: {project.title}")

        return {
            "message": "Project deleted successfully",
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )
