"""Tenant-safe company profile management endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Company, Organization, User, UserOrganization
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/companies", tags=["company"])


def _assert_user_in_org(db: Session, user_id: UUID, organization_id: UUID) -> None:
    membership = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == organization_id,
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization",
        )


def _get_org_or_404(db: Session, organization_id: UUID) -> Organization:
    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization


def _get_company_by_org(db: Session, organization_id: UUID) -> Optional[Company]:
    return (
        db.query(Company)
        .filter(Company.organization_id == organization_id)
        .first()
    )


@router.post("/organization/{organization_id}", response_model=SuccessResponse)
async def create_company_for_organization(
    organization_id: UUID,
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Create the company profile for a specific organization."""
    try:
        _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)

        existing = _get_company_by_org(db, organization_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Company profile already exists for this organization",
            )

        company = Company(
            organization_id=organization_id,
            name=company_data.name,
            description=company_data.description,
            unique_selling_proposition=company_data.unique_selling_proposition,
            key_capabilities=company_data.key_capabilities,
            experience=company_data.experience,
            industry_focus=company_data.industry_focus,
        )

        db.add(company)
        db.commit()
        db.refresh(company)

        return create_success_response(
            message="Company profile created successfully",
            data=CompanyResponse.from_orm(company).model_dump(),
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating company profile for org {organization_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company profile: {str(e)}",
        )


@router.get("/organization/{organization_id}", response_model=SuccessResponse)
async def get_company_for_organization(
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Get the company profile for the selected organization."""
    try:
        _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)

        company = _get_company_by_org(db, organization_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company profile not found for this organization",
            )

        return create_success_response(
            message="Company profile retrieved successfully",
            data=CompanyResponse.from_orm(company).model_dump(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving company profile for org {organization_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve company profile: {str(e)}",
        )


@router.patch("/organization/{organization_id}", response_model=SuccessResponse)
async def update_company_for_organization(
    organization_id: UUID,
    company_data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Update the company profile for the selected organization."""
    try:
        _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)

        company = _get_company_by_org(db, organization_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company profile not found for this organization",
            )

        update_data = company_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(company, field, value)

        db.commit()
        db.refresh(company)

        return create_success_response(
            message="Company profile updated successfully",
            data=CompanyResponse.from_orm(company).model_dump(),
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating company profile for org {organization_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update company profile: {str(e)}",
        )


@router.delete("/organization/{organization_id}", response_model=SuccessResponse)
async def delete_company_for_organization(
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Delete the company profile for the selected organization."""
    try:
        _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)

        company = _get_company_by_org(db, organization_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company profile not found for this organization",
            )

        db.delete(company)
        db.commit()

        return create_success_response(
            message="Company profile deleted successfully",
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting company profile for org {organization_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete company profile: {str(e)}",
        )
        