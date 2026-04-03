"""Writing preferences management endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import CompanyWritingPreferences, Company
from app.schemas.writing_preferences import (
    WritingPreferencesCreate,
    WritingPreferencesUpdate,
    WritingPreferencesResponse
)
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/companies", tags=["writing_preferences"])


@router.post("/{company_id}/writing-preferences", response_model=SuccessResponse)
async def create_writing_preferences(
    company_id: str,
    preferences_data: WritingPreferencesCreate,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Create writing preferences for a company."""
    try:
        # Verify company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # Check if preferences already exist
        existing = db.query(CompanyWritingPreferences).filter(
            CompanyWritingPreferences.company_id == company_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Writing preferences already exist for this company. Use PATCH to update."
            )

        # Create new preferences
        preferences = CompanyWritingPreferences(
            company_id=company_id,
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

        logger.info(f"Writing preferences created for company {company_id}")

        return create_success_response(
            message="Writing preferences created successfully",
            data=WritingPreferencesResponse.from_orm(preferences).model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating writing preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create writing preferences: {str(e)}"
        )


@router.get("/{company_id}/writing-preferences", response_model=SuccessResponse)
async def get_writing_preferences(
    company_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Get writing preferences for a company."""
    try:
        # Verify company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        preferences = db.query(CompanyWritingPreferences).filter(
            CompanyWritingPreferences.company_id == company_id
        ).first()

        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Writing preferences not found for this company"
            )

        return create_success_response(
            message="Writing preferences retrieved successfully",
            data=WritingPreferencesResponse.from_orm(preferences).model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving writing preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve writing preferences: {str(e)}"
        )


@router.patch("/{company_id}/writing-preferences", response_model=SuccessResponse)
async def update_writing_preferences(
    company_id: str,
    preferences_data: WritingPreferencesUpdate,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Update writing preferences for a company."""
    try:
        # Verify company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        preferences = db.query(CompanyWritingPreferences).filter(
            CompanyWritingPreferences.company_id == company_id
        ).first()

        if not preferences:
            # If doesn't exist, create with defaults first
            preferences = CompanyWritingPreferences(company_id=company_id)
            db.add(preferences)

        # Update only provided fields
        update_data = preferences_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preferences, field, value)

        db.commit()
        db.refresh(preferences)

        logger.info(f"Writing preferences updated for company {company_id}")

        return create_success_response(
            message="Writing preferences updated successfully",
            data=WritingPreferencesResponse.from_orm(preferences).model_dump()
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating writing preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update writing preferences: {str(e)}"
        )


@router.delete("/{company_id}/writing-preferences", response_model=SuccessResponse)
async def delete_writing_preferences(
    company_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Delete writing preferences for a company."""
    try:
        # Verify company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        preferences = db.query(CompanyWritingPreferences).filter(
            CompanyWritingPreferences.company_id == company_id
        ).first()

        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Writing preferences not found for this company"
            )

        db.delete(preferences)
        db.commit()

        logger.info(f"Writing preferences deleted for company {company_id}")

        return create_success_response(
            message="Writing preferences deleted successfully"
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting writing preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete writing preferences: {str(e)}"
        )
