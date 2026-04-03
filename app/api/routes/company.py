"""Company profile management endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Company
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/companies", tags=["company"])


@router.post("", response_model=SuccessResponse)
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Create a new company profile."""
    try:
        company = Company(
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
            data=CompanyResponse.from_orm(company).model_dump()
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating company: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {str(e)}"
        )


@router.get("", response_model=SuccessResponse)
async def list_companies(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> SuccessResponse:
    """List all company profiles."""
    try:
        companies = db.query(Company).offset(skip).limit(limit).all()
        total = db.query(Company).count()

        return create_success_response(
            message="Companies retrieved successfully",
            data={
                "companies": [CompanyResponse.from_orm(c).model_dump() for c in companies],
                "total": total
            }
        )

    except Exception as e:
        logger.error(f"Error listing companies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve companies: {str(e)}"
        )


@router.get("/{company_id}", response_model=SuccessResponse)
async def get_company(
    company_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Get company profile by ID."""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        return create_success_response(
            message="Company retrieved successfully",
            data=CompanyResponse.from_orm(company).model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving company {company_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve company: {str(e)}"
        )


@router.patch("/{company_id}", response_model=SuccessResponse)
async def update_company(
    company_id: str,
    company_data: CompanyUpdate,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Update company profile."""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        update_data = company_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(company, field, value)

        db.commit()
        db.refresh(company)

        return create_success_response(
            message="Company profile updated successfully",
            data=CompanyResponse.from_orm(company).model_dump()
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating company {company_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update company: {str(e)}"
        )


@router.delete("/{company_id}", response_model=SuccessResponse)
async def delete_company(
    company_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Delete company profile."""
    try:
        company = db.query(Company).filter(Company.id == company_id).first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        db.delete(company)
        db.commit()

        return create_success_response(
            message="Company profile deleted successfully"
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting company {company_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete company: {str(e)}"
        )
