"""Company profile management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Company
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.schemas.common import SuccessResponse
from app.utils.response_helpers import create_success_response, MESSAGES

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {str(e)}"
        )


@router.get("/{company_id}", response_model=SuccessResponse)
async def get_company(
    company_id: str,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Get company profile by ID."""
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


@router.patch("/{company_id}", response_model=SuccessResponse)
async def update_company(
    company_id: str,
    company_data: CompanyUpdate,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """Update company profile."""
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    try:
        update_data = company_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(company, field, value)

        db.commit()
        db.refresh(company)

        return create_success_response(
            message="Company profile updated successfully",
            data=CompanyResponse.from_orm(company).model_dump()
        )

    except Exception as e:
        db.rollback()
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
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    try:
        db.delete(company)
        db.commit()

        return create_success_response(
            message="Company profile deleted successfully"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete company: {str(e)}"
        )
