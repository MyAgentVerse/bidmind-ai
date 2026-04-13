"""Subscription tier definitions, feature gating, and usage enforcement."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.usage_record import UsageRecord

# Centralized tier definitions — single source of truth
TIER_LIMITS = {
    "starter": {
        "max_members": 1,
        "max_proposals_per_month": 5,
        "max_active_projects": 3,
        "max_company_profiles": 1,
        "features": {
            "upload", "analyze", "generate_proposal", "export_docx",
            "basic_writing_prefs",
        },
    },
    "pro": {
        "max_members": None,  # unlimited
        "max_proposals_per_month": None,
        "max_active_projects": None,
        "max_company_profiles": None,
        "features": {
            "upload", "analyze", "generate_proposal", "export_docx",
            "basic_writing_prefs", "ai_edit", "learning_loop",
            "advanced_writing_prefs", "team_invites",
        },
    },
}


def get_tier_limits(tier: str) -> Optional[dict]:
    return TIER_LIMITS.get(tier)


def is_subscription_active(org: Organization) -> bool:
    """Check if the org has an active paid subscription."""
    if org.subscription_status != "active":
        # Allow cancelled Pro users until their period ends
        if (
            org.subscription_status == "cancelled"
            and org.subscription_ends_at
            and org.subscription_ends_at > datetime.now(timezone.utc)
        ):
            return True
        return False
    return org.subscription_tier in ("starter", "pro")


def check_feature_access(org: Organization, feature: str) -> None:
    """Raise 403 if the org's tier doesn't include this feature."""
    if not is_subscription_active(org):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required. Please subscribe to access this feature.",
        )

    limits = get_tier_limits(org.subscription_tier)
    if not limits:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unknown subscription tier.",
        )

    if feature not in limits["features"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This feature requires the Pro plan. Your current plan: {org.subscription_tier}.",
        )


def _current_period_start() -> datetime:
    """Return the 1st of the current month UTC (used as period key)."""
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def get_usage_count(org_id, usage_type: str, db: Session) -> int:
    """Get current month's usage count for an org."""
    period = _current_period_start()
    record = (
        db.query(UsageRecord)
        .filter(
            UsageRecord.organization_id == str(org_id),
            UsageRecord.usage_type == usage_type,
            UsageRecord.period_start == period,
        )
        .first()
    )
    return record.count if record else 0


def check_usage_limit(org: Organization, usage_type: str, db: Session) -> None:
    """Raise 403 if the org has hit its usage limit for this type."""
    if not is_subscription_active(org):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required.",
        )

    limits = get_tier_limits(org.subscription_tier)
    if not limits:
        return

    limit_key = {
        "proposal_generated": "max_proposals_per_month",
        "project_created": "max_active_projects",
    }.get(usage_type)

    if not limit_key:
        return

    max_allowed = limits.get(limit_key)
    if max_allowed is None:
        return  # unlimited

    # For projects, count active projects instead of monthly usage
    if usage_type == "project_created":
        from app.models.project import Project
        active_count = (
            db.query(Project)
            .filter(Project.organization_id == str(org.id))
            .count()
        )
        if active_count >= max_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Project limit reached ({max_allowed} active projects on {org.subscription_tier} plan). Upgrade to Pro for unlimited projects.",
            )
        return

    current = get_usage_count(org.id, usage_type, db)
    if current >= max_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Monthly limit reached ({max_allowed} {usage_type.replace('_', ' ')}s on {org.subscription_tier} plan). Upgrade to Pro for unlimited usage.",
        )


def increment_usage(org_id, usage_type: str, db: Session) -> None:
    """Atomically increment usage count for the current month."""
    period = _current_period_start()
    # Upsert: insert or increment
    db.execute(
        text(
            """
            INSERT INTO usage_records (id, organization_id, usage_type, period_start, count, created_at, updated_at)
            VALUES (gen_random_uuid(), :org_id, :usage_type, :period, 1, NOW(), NOW())
            ON CONFLICT (organization_id, usage_type, period_start)
            DO UPDATE SET count = usage_records.count + 1, updated_at = NOW()
            """
        ),
        {"org_id": str(org_id), "usage_type": usage_type, "period": period},
    )
    db.commit()


def check_member_limit(org: Organization, db: Session) -> None:
    """Raise 403 if the org has hit its member limit."""
    if not is_subscription_active(org):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required.",
        )

    limits = get_tier_limits(org.subscription_tier)
    if not limits or limits["max_members"] is None:
        return  # unlimited

    from app.models.user_organization import UserOrganization
    current_members = (
        db.query(UserOrganization)
        .filter(UserOrganization.organization_id == str(org.id))
        .count()
    )
    if current_members >= limits["max_members"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Member limit reached ({limits['max_members']} on {org.subscription_tier} plan). Upgrade to Pro for unlimited team members.",
        )


def get_usage_stats(org: Organization, db: Session) -> dict:
    """Return current usage + limits for the frontend usage meter."""
    limits = get_tier_limits(org.subscription_tier) or {}

    from app.models.project import Project
    active_projects = (
        db.query(Project)
        .filter(Project.organization_id == str(org.id))
        .count()
    )

    proposals_this_month = get_usage_count(org.id, "proposal_generated", db)

    from app.models.user_organization import UserOrganization
    member_count = (
        db.query(UserOrganization)
        .filter(UserOrganization.organization_id == str(org.id))
        .count()
    )

    return {
        "tier": org.subscription_tier,
        "status": org.subscription_status,
        "proposals": {
            "used": proposals_this_month,
            "limit": limits.get("max_proposals_per_month"),  # None = unlimited
        },
        "projects": {
            "used": active_projects,
            "limit": limits.get("max_active_projects"),
        },
        "members": {
            "used": member_count,
            "limit": limits.get("max_members"),
        },
    }
