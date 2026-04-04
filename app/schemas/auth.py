"""Pydantic schemas for authentication endpoints."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """Request model for user signup."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)
    organization_name: Optional[str] = Field(None, max_length=255)


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response model containing authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str


class UserResponse(BaseModel):
    """Response model for user information."""
    id: str
    email: str
    full_name: str
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    """Response model for organization information."""
    id: str
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True
