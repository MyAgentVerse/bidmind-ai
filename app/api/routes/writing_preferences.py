"""Tenant-safe writing preferences management endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Company, CompanyWritingPreferences, Organization, User, UserOrganization
from app.services import subscription_service
from app.schemas.writing_preferences import (
    WritingPreferencesCreate,
    WritingPreferencesUpdate,
    WritingPreferencesResponse,
)
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/companies", tags=["writing_preferences"])


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


def _get_company_or_404_by_org(db: Session, organization_id: UUID) -> Company:
    company = (
        db.query(Company)
        .filter(Company.organization_id == organization_id)
        .first()
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company profile not found for this organization",
        )

    return company


@router.post("/organization/{organization_id}/writing-preferences", response_model=SuccessResponse)
async def create_writing_preferences(
    organization_id: UUID,
    preferences_data: WritingPreferencesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Create writing preferences for the selected organization's company profile."""
    try:
        org = _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)
        subscription_service.check_feature_access(org, "advanced_writing_prefs")
        company = _get_company_or_404_by_org(db, organization_id)

        existing = (
            db.query(CompanyWritingPreferences)
            .filter(CompanyWritingPreferences.company_id == company.id)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Writing preferences already exist for this organization. Use PATCH to update.",
            )

        preferences = CompanyWritingPreferences(
            company_id=company.id,
            tone_level=preferences_data.tone_level,
            brand_voice_tags=preferences_data.brand_voice_tags,
            language_complexity=preferences_data.language_complexity,
            company_jargon=preferences_data.company_jargon,
            must_include=preferences_data.must_include,
            do_not_include=preferences_data.do_not_include,
            focus_areas=preferences_data.focus_areas,
            required_sections=preferences_data.required_sections,
            custom_sections=preferences_data.custom_sections,
            section_order=preferences_data.section_order,
            section_length_multipliers=preferences_data.section_length_multipliers,
        )

        db.add(preferences)
        db.commit()
        db.refresh(preferences)

        logger.info(f"Writing preferences created for organization {organization_id}")

        return create_success_response(
            message="Writing preferences created successfully",
            data=WritingPreferencesResponse.from_orm(preferences).model_dump(),
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating writing preferences for org {organization_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create writing preferences: {str(e)}",
        )


@router.get("/organization/{organization_id}/writing-preferences", response_model=SuccessResponse)
async def get_writing_preferences(
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Get writing preferences for the selected organization's company profile."""
    try:
        _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)
        company = _get_company_or_404_by_org(db, organization_id)

        preferences = (
            db.query(CompanyWritingPreferences)
            .filter(CompanyWritingPreferences.company_id == company.id)
            .first()
        )

        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Writing preferences not found for this organization",
            )

        return create_success_response(
            message="Writing preferences retrieved successfully",
            data=WritingPreferencesResponse.from_orm(preferences).model_dump(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving writing preferences for org {organization_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve writing preferences: {str(e)}",
        )


@router.patch("/organization/{organization_id}/writing-preferences", response_model=SuccessResponse)
async def update_writing_preferences(
    organization_id: UUID,
    preferences_data: WritingPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Update writing preferences for the selected organization's company profile."""
    try:
        org = _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)
        subscription_service.check_feature_access(org, "advanced_writing_prefs")
        company = _get_company_or_404_by_org(db, organization_id)

        preferences = (
            db.query(CompanyWritingPreferences)
            .filter(CompanyWritingPreferences.company_id == company.id)
            .first()
        )

        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Writing preferences not found for this organization",
            )

        update_data = preferences_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preferences, field, value)

        db.commit()
        db.refresh(preferences)

        logger.info(f"Writing preferences updated for organization {organization_id}")

        return create_success_response(
            message="Writing preferences updated successfully",
            data=WritingPreferencesResponse.from_orm(preferences).model_dump(),
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating writing preferences for org {organization_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update writing preferences: {str(e)}",
        )


@router.delete("/organization/{organization_id}/writing-preferences", response_model=SuccessResponse)
async def delete_writing_preferences(
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Delete writing preferences for the selected organization's company profile."""
    try:
        _get_org_or_404(db, organization_id)
        _assert_user_in_org(db, current_user.id, organization_id)
        company = _get_company_or_404_by_org(db, organization_id)

        preferences = (
            db.query(CompanyWritingPreferences)
            .filter(CompanyWritingPreferences.company_id == company.id)
            .first()
        )

        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Writing preferences not found for this organization",
            )

        db.delete(preferences)
        db.commit()

        logger.info(f"Writing preferences deleted for organization {organization_id}")

        return create_success_response(
            message="Writing preferences deleted successfully",
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting writing preferences for org {organization_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete writing preferences: {str(e)}",
        )
        