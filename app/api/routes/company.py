"""Tenant-safe company profile management endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Company, Organization, User, UserOrganization
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response
from app.services.company_ai_service import CompanyAIService

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


# ==================== AI-POWERED PROFILE GENERATION ====================


class GenerateFromURLRequest(BaseModel):
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None


class AIEditFieldRequest(BaseModel):
    field_name: str  # e.g. "description", "key_capabilities"
    current_value: str
    instruction: str  # e.g. "make it more concise", "add cybersecurity focus"


@router.post("/organization/{organization_id}/generate-from-url", response_model=SuccessResponse)
async def generate_company_from_url(
    organization_id: UUID,
    request: GenerateFromURLRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Generate a company profile from website and/or LinkedIn URL.

    The AI fetches the URL content and extracts: name, description,
    USP, capabilities, experience, and industry focus. If a profile
    already exists, it returns the generated data WITHOUT overwriting
    — the frontend should let the user review and confirm.
    """
    try:
        _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)

        if not request.website_url and not request.linkedin_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one URL (website_url or linkedin_url) is required",
            )

        service = CompanyAIService()
        profile_data = await service.generate_profile_from_urls(
            website_url=request.website_url,
            linkedin_url=request.linkedin_url,
        )

        return create_success_response(
            message="Company profile generated from URL",
            data=profile_data,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error generating company from URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate company profile: {str(e)}",
        )


@router.post("/organization/{organization_id}/ai-edit", response_model=SuccessResponse)
async def ai_edit_company_field(
    organization_id: UUID,
    request: AIEditFieldRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """AI-edit a single company profile field.

    Sends the current field value + user instruction to the LLM,
    returns the updated value. Does NOT save automatically — the
    frontend should show the result and let the user confirm.
    """
    try:
        _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)

        valid_fields = {
            "name", "description", "unique_selling_proposition",
            "key_capabilities", "experience", "industry_focus",
        }
        if request.field_name not in valid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field. Must be one of: {', '.join(sorted(valid_fields))}",
            )

        # Get existing company for context
        company = _get_company_by_org(db, organization_id)
        company_context = None
        if company:
            company_context = {
                "name": company.name,
                "industry_focus": company.industry_focus,
            }

        service = CompanyAIService()
        updated_value = await service.ai_edit_field(
            field_name=request.field_name,
            current_value=request.current_value,
            instruction=request.instruction,
            company_context=company_context,
        )

        return create_success_response(
            message="Field updated by AI",
            data={
                "field_name": request.field_name,
                "original_value": request.current_value,
                "updated_value": updated_value,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in AI edit: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI edit failed: {str(e)}",
        )
        