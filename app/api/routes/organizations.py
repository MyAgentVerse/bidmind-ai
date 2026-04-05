"""Organization management routes."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User, Organization, UserOrganization

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/organizations", tags=["organizations"])


def check_org_access(user: User, org_id: str, db: Session, required_role: str = "member"):
    """Check if user has access to organization with minimum required role."""
    user_org = db.query(UserOrganization).filter(
        UserOrganization.user_id == user.id,
        UserOrganization.organization_id == org_id
    ).first()

    if not user_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this organization"
        )

    # Check role hierarchy: owner > admin > member > viewer
    role_hierarchy = {"owner": 4, "admin": 3, "member": 2, "viewer": 1}
    user_role_level = role_hierarchy.get(user_org.role, 0)
    required_role_level = role_hierarchy.get(required_role, 0)

    if user_role_level < required_role_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You need at least {required_role} role for this action"
        )

    return user_org


@router.get("", response_model=dict)
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all organizations the current user belongs to.

    Returns:
        List of user's organizations with roles
    """
    try:
        user_orgs = db.query(UserOrganization).filter(
            UserOrganization.user_id == current_user.id
        ).all()

        organizations = []
        for uo in user_orgs:
            org = db.query(Organization).filter(Organization.id == uo.organization_id).first()
            if org:
                organizations.append({
                    "id": str(org.id),
                    "name": org.name,
                    "description": org.description,
                    "role": uo.role,
                    "created_at": org.created_at.isoformat()
                })

        return {"organizations": organizations}

    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list organizations"
        )


@router.post("", response_model=dict)
async def create_organization(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new organization with current user as owner.

    Args:
        request: Dict with 'name' and optional 'description'
        current_user: Current authenticated user

    Returns:
        Created organization details
    """
    try:
        name = request.get("name")
        description = request.get("description", "")

        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name is required"
            )

        # Create organization
        org = Organization(name=name, description=description)
        db.add(org)
        db.flush()

        # Add user as owner
        user_org = UserOrganization(
            user_id=current_user.id,
            organization_id=org.id,
            role="owner"
        )
        db.add(user_org)
        db.commit()

        logger.info(f"Organization created: {name} by {current_user.email}")

        return {
            "id": str(org.id),
            "name": org.name,
            "description": org.description,
            "role": "owner",
            "message": "Organization created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating organization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create organization"
        )


@router.get("/{org_id}", response_model=dict)
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get organization details including members.

    Args:
        org_id: Organization ID

    Returns:
        Organization details and member list
    """
    try:
        check_org_access(current_user, org_id, db)

        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Get members
        members = []
        user_orgs = db.query(UserOrganization).filter(
            UserOrganization.organization_id == org_id
        ).all()

        for uo in user_orgs:
            user = db.query(User).filter(User.id == uo.user_id).first()
            if user:
                members.append({
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": uo.role,
                    "joined_at": uo.created_at.isoformat()
                })

        return {
            "id": str(org.id),
            "name": org.name,
            "description": org.description,
            "members": members,
            "member_count": len(members),
            "created_at": org.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get organization"
        )


@router.put("/{org_id}", response_model=dict)
async def update_organization(
    org_id: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update organization details. Requires owner or admin role.

    Args:
        org_id: Organization ID
        request: Dict with fields to update (name, description)

    Returns:
        Updated organization details
    """
    try:
        check_org_access(current_user, org_id, db, required_role="admin")

        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        if "name" in request:
            org.name = request["name"]
        if "description" in request:
            org.description = request["description"]

        db.commit()
        db.refresh(org)

        logger.info(f"Organization updated: {org.name}")

        return {
            "id": str(org.id),
            "name": org.name,
            "description": org.description,
            "message": "Organization updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating organization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update organization"
        )


@router.get("/{org_id}/members", response_model=dict)
async def list_members(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all members of an organization.

    Args:
        org_id: Organization ID

    Returns:
        List of members with their roles
    """
    try:
        check_org_access(current_user, org_id, db)

        # Get all members in organization
        user_orgs = db.query(UserOrganization).filter(
            UserOrganization.organization_id == org_id
        ).all()

        members = []
        for uo in user_orgs:
            user = db.query(User).filter(User.id == uo.user_id).first()
            if user:
                members.append({
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": uo.role,
                    "joined_at": uo.created_at.isoformat()
                })

        return {
            "members": members,
            "count": len(members)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list members"
        )


@router.post("/{org_id}/members", response_model=dict)
async def add_member(
    org_id: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a member to organization. Requires admin role.

    Args:
        org_id: Organization ID
        request: Dict with 'user_id' and 'role' (optional, defaults to 'member')

    Returns:
        Member details
    """
    try:
        check_org_access(current_user, org_id, db, required_role="admin")

        user_id = request.get("user_id")
        role = request.get("role", "member")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required"
            )

        if role not in ["viewer", "member", "admin", "owner"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )

        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if already member
        existing = db.query(UserOrganization).filter(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == org_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization"
            )

        # Add member
        user_org = UserOrganization(
            user_id=user_id,
            organization_id=org_id,
            role=role
        )
        db.add(user_org)
        db.commit()

        logger.info(f"Member added to organization {org_id}: {user.email}")

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": role,
            "message": "Member added successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add member"
        )


@router.put("/{org_id}/members/{user_id}", response_model=dict)
async def update_member_role(
    org_id: str,
    user_id: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update member role. Requires admin role.

    Args:
        org_id: Organization ID
        user_id: User ID to update
        request: Dict with 'role' field

    Returns:
        Updated member details
    """
    try:
        check_org_access(current_user, org_id, db, required_role="admin")

        role = request.get("role")
        if not role or role not in ["viewer", "member", "admin", "owner"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valid role is required"
            )

        user_org = db.query(UserOrganization).filter(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == org_id
        ).first()

        if not user_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in organization"
            )

        user_org.role = role
        db.commit()

        user = db.query(User).filter(User.id == user_id).first()
        logger.info(f"Member role updated for {user.email} in organization {org_id}: {role}")

        return {
            "id": str(user.id),
            "email": user.email,
            "role": role,
            "message": "Member role updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating member role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )


@router.delete("/{org_id}/members/{user_id}", response_model=dict)
async def remove_member(
    org_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove member from organization. Requires admin role.

    Args:
        org_id: Organization ID
        user_id: User ID to remove

    Returns:
        Success message
    """
    try:
        check_org_access(current_user, org_id, db, required_role="admin")

        user_org = db.query(UserOrganization).filter(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == org_id
        ).first()

        if not user_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in organization"
            )

        user = db.query(User).filter(User.id == user_id).first()
        db.delete(user_org)
        db.commit()

        logger.info(f"Member removed from organization {org_id}: {user.email}")

        return {
            "message": "Member removed successfully",
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )
