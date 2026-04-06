"""Pydantic schemas for Company model."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class CompanyBase(BaseModel):
    """Base company schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    unique_selling_proposition: Optional[str] = Field(
        None,
        description="What makes this company unique and different from competitors",
    )
    key_capabilities: Optional[str] = Field(
        None,
        description="Core strengths, services, and what company can deliver",
    )
    experience: Optional[str] = Field(
        None,
        description="Years of experience, past successes, relevant projects",
    )
    industry_focus: Optional[str] = Field(
        None,
        description="Industries and sectors the company specializes in",
    )


class CompanyCreate(CompanyBase):
    """Schema for creating a company profile for an organization."""
    pass


class CompanyUpdate(BaseModel):
    """Schema for updating a company (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    unique_selling_proposition: Optional[str] = None
    key_capabilities: Optional[str] = None
    experience: Optional[str] = None
    industry_focus: Optional[str] = None


class CompanyResponse(CompanyBase):
    """Schema for company response (includes id, organization_id and timestamps)."""
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        