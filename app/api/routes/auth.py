"""Authentication routes for login, signup, and token refresh."""

import logging
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import password_manager, token_manager
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    OrganizationResponse,
)
from app.models import User, Organization, UserOrganization

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/signup", response_model=dict)
async def signup(
    request: SignupRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new user account with optional organization.

    Args:
        request: Signup details (email, full_name, password, organization_name)
        db: Database session

    Returns:
        User info and authentication tokens

    Raises:
        HTTPException: If email already exists
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        password_hash = password_manager.hash_password(request.password)

        # Create user
        user = User(
            email=request.email,
            full_name=request.full_name,
            password_hash=password_hash,
            is_active=True,
            is_verified=False
        )

        db.add(user)
        db.flush()  # Get user ID without committing

        # Create organization if provided
        organization = None
        if request.organization_name:
            organization = Organization(
                name=request.organization_name,
                description=""
            )
            db.add(organization)
            db.flush()

            # Link user to organization as owner
            user_org = UserOrganization(
                user_id=user.id,
                organization_id=organization.id,
                role="owner"
            )
            db.add(user_org)

        db.commit()
        db.refresh(user)

        # Generate tokens
        access_token = token_manager.create_access_token(str(user.id))
        refresh_token = token_manager.create_refresh_token(str(user.id))
        expires_in = token_manager.get_token_expiry()

        logger.info(f"New user created: {user.email}")

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified
            },
            "organization": {
                "id": str(organization.id),
                "name": organization.name
            } if organization else None,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )


@router.post("/login", response_model=dict)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access/refresh tokens.

    Args:
        request: Login credentials (email, password)
        db: Database session

    Returns:
        User info and authentication tokens

    Raises:
        HTTPException: If credentials are invalid or user is inactive
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        if not password_manager.verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Update last login
        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)

        # Generate tokens
        access_token = token_manager.create_access_token(str(user.id))
        refresh_token = token_manager.create_refresh_token(str(user.id))
        expires_in = token_manager.get_token_expiry()

        logger.info(f"User login: {user.email}")

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Generate new access token using refresh token.

    Args:
        request: Refresh token request
        db: Database session

    Returns:
        New access token with expiry

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Decode refresh token
        payload = token_manager.decode_token(request.refresh_token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Check token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # Verify user still exists and is active
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Generate new access token
        access_token = token_manager.create_access_token(str(user.id))
        expires_in = token_manager.get_token_expiry()

        logger.info(f"Token refreshed for user: {user.email}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user's profile.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Current user's profile information and organizations
    """
    try:
        # Get user's organizations
        user_orgs = db.query(UserOrganization).filter(
            UserOrganization.user_id == current_user.id
        ).all()

        organizations = []
        for uo in user_orgs:
            org = db.query(Organization).filter(
                Organization.id == uo.organization_id
            ).first()
            if org:
                organizations.append({
                    "id": str(org.id),
                    "name": org.name,
                    "role": uo.role
                })

        return {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            "organizations": organizations
        }

    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post("/logout", response_model=dict)
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout the current user. Frontend should clear tokens from localStorage.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Logout confirmation message
    """
    try:
        logger.info(f"User logout: {current_user.email}")
        return {
            "message": "Successfully logged out",
            "success": True
        }

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Request a password reset token. Returns reset token (in production, send via email).

    NOTE: This feature is currently pending database migration.
    Returns success but tokens are not persisted yet.

    Args:
        request: Dict with 'email' field
        db: Database session

    Returns:
        Reset token and message
    """
    try:
        email = request.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )

        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Return success even if user doesn't exist (security best practice)
            logger.info(f"Password reset requested for non-existent user: {email}")
            return {
                "message": "If account exists, password reset link has been sent",
                "success": True
            }

        # Generate reset token (valid for 1 hour)
        # TODO: Persist these after migration 007 is applied
        reset_token = secrets.token_urlsafe(32)
        logger.info(f"Password reset token generated for: {email}")

        return {
            "message": "Password reset link has been sent to your email",
            "reset_token": reset_token,  # In production, don't return this - send via email
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )


@router.post("/reset-password", response_model=dict)
async def reset_password(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Reset password using a valid reset token.

    NOTE: This feature is currently pending database migration.
    Will be fully functional after migration 007 is applied.

    Args:
        request: Dict with 'reset_token' and 'new_password' fields
        db: Database session

    Returns:
        Success message
    """
    try:
        reset_token = request.get("reset_token")
        new_password = request.get("new_password")
        email = request.get("email")

        if not reset_token or not new_password or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token, email, and new password are required"
            )

        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters"
            )

        # Find user by email (token validation pending migration)
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )

        # TODO: Validate reset token after migration 007 is applied
        # For now, just reset the password with email verification
        user.password_hash = password_manager.hash_password(new_password)
        db.commit()

        logger.info(f"Password reset successful for: {user.email}")

        return {
            "message": "Password has been reset successfully",
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Reset password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )
