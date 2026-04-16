"""Billing and subscription management endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User, Organization, UserOrganization
from app.services import stripe_service, subscription_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    org_id: str
    tier: str  # "starter" or "pro"
    success_url: str
    cancel_url: str


class PortalRequest(BaseModel):
    org_id: str
    return_url: str


@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session. Returns the checkout URL."""
    # Verify user owns this org
    user_org = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id,
        UserOrganization.organization_id == request.org_id,
        UserOrganization.role == "owner",
    ).first()

    if not user_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization owner can manage billing.",
        )

    org = db.query(Organization).filter(Organization.id == request.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if request.tier not in ("starter", "pro"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tier must be 'starter' or 'pro'.",
        )

    # Block re-purchasing the same tier. Starter→Pro upgrade is allowed; the
    # $59 Starter receipt stays valid as lifetime fallback after Pro lapses.
    if org.subscription_status == "active" and org.subscription_tier == request.tier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization already has an active {request.tier} subscription.",
        )
    if request.tier == "starter" and org.has_lifetime_starter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already has lifetime Starter access.",
        )

    try:
        checkout_url, customer_id = stripe_service.create_checkout_session(
            org=org,
            tier=request.tier,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        # Persist stripe_customer_id immediately so webhook can find the org
        if not org.stripe_customer_id:
            org.stripe_customer_id = customer_id
            db.commit()

        return {"checkout_url": checkout_url}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/portal")
async def create_portal(
    request: PortalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing subscription."""
    user_org = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id,
        UserOrganization.organization_id == request.org_id,
        UserOrganization.role == "owner",
    ).first()

    if not user_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization owner can manage billing.",
        )

    org = db.query(Organization).filter(Organization.id == request.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        portal_url = stripe_service.create_customer_portal_session(org, request.return_url)
        return {"portal_url": portal_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stripe portal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.get("/subscription")
async def get_subscription(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get subscription details and usage stats for an organization."""
    user_org = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id,
        UserOrganization.organization_id == org_id,
    ).first()

    if not user_org:
        raise HTTPException(status_code=403, detail="No access to this organization")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    usage = subscription_service.get_usage_stats(org, db)

    # Determine what happens after Pro ends, if relevant
    fallback_tier = "starter" if org.has_lifetime_starter else "none"

    return {
        "subscription": {
            "tier": org.subscription_tier,
            "status": org.subscription_status,
            "started_at": org.subscription_started_at.isoformat() if org.subscription_started_at else None,
            "ends_at": org.subscription_ends_at.isoformat() if org.subscription_ends_at else None,
            "has_lifetime_starter": org.has_lifetime_starter,
            "fallback_tier_on_end": fallback_tier,  # "starter" or "none" — shown to cancelled Pro users
            "can_manage_billing": org.stripe_customer_id is not None,  # false for comped/internal accounts
        },
        "usage": usage,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook endpoint. No auth — verified by Stripe signature.

    Must receive raw body (not JSON-parsed) for signature verification.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        result = stripe_service.handle_webhook_event(payload, sig_header, db)
        return result
    except ValueError as e:
        logger.warning(f"Webhook signature failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed")
