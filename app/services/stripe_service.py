"""Stripe integration for checkout, subscriptions, and webhooks."""

import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy.orm import Session


def _to_plain_dict(obj):
    """Recursively convert mapping-like objects (incl. StripeObject) to plain dicts.

    In stripe-python 7+, StripeObject is no longer a dict subclass but still
    exposes keys() and __getitem__, so we duck-type instead of isinstance(dict).
    """
    if isinstance(obj, (str, bytes, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, list):
        return [_to_plain_dict(v) for v in obj]
    if hasattr(obj, "keys") and hasattr(obj, "__getitem__"):
        return {k: _to_plain_dict(obj[k]) for k in obj.keys()}
    return obj

from app.core.config import get_settings
from app.models.organization import Organization

logger = logging.getLogger(__name__)
settings = get_settings()

stripe.api_key = settings.stripe_secret_key


def create_checkout_session(
    org: Organization,
    tier: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout session and return the URL.

    - Starter ($59): mode="payment" (one-time)
    - Pro ($29/mo): mode="subscription" (recurring)
    """
    price_id = {
        "starter": settings.stripe_starter_price_id,
        "pro": settings.stripe_pro_price_id,
    }.get(tier)

    if not price_id:
        raise ValueError(f"Unknown tier: {tier}")

    # Create or reuse Stripe customer
    customer_id = org.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            metadata={"organization_id": str(org.id)},
        )
        customer_id = customer.id

    mode = "payment" if tier == "starter" else "subscription"

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode=mode,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "organization_id": str(org.id),
            "tier": tier,
        },
    )

    return session.url, customer_id


def create_customer_portal_session(org: Organization, return_url: str) -> str:
    """Create a Stripe Customer Portal session for managing subscription."""
    if not org.stripe_customer_id:
        raise ValueError("Organization has no Stripe customer. Subscribe first.")

    session = stripe.billing_portal.Session.create(
        customer=org.stripe_customer_id,
        return_url=return_url,
    )
    return session.url


def handle_webhook_event(payload: bytes, sig_header: str, db: Session) -> dict:
    """
    Process a Stripe webhook event and update the org subscription accordingly.

    Returns a dict with event type and status for logging.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid Stripe webhook signature")

    event_type = event["type"]
    data = _to_plain_dict(event["data"]["object"])

    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data, db)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data, db)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data, db)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data, db)

    return {"event_type": event_type, "status": "processed"}


def _handle_checkout_completed(session_data: dict, db: Session) -> None:
    """Activate subscription after successful checkout."""
    org_id = session_data.get("metadata", {}).get("organization_id")
    tier = session_data.get("metadata", {}).get("tier")
    customer_id = session_data.get("customer")
    subscription_id = session_data.get("subscription")  # None for one-time payments

    if not org_id or not tier:
        logger.warning("Checkout completed but missing org_id or tier in metadata")
        return

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        logger.error(f"Checkout completed for unknown org: {org_id}")
        return

    org.subscription_tier = tier
    org.subscription_status = "active"
    org.stripe_customer_id = customer_id
    org.stripe_subscription_id = subscription_id  # None for Starter
    org.subscription_started_at = datetime.now(timezone.utc)
    org.subscription_ends_at = None  # Starter = forever, Pro = managed by Stripe

    db.commit()
    logger.info(f"Subscription activated: org={org_id}, tier={tier}")


def _handle_payment_failed(invoice_data: dict, db: Session) -> None:
    """Mark subscription as past_due when payment fails."""
    customer_id = invoice_data.get("customer")
    if not customer_id:
        return

    org = db.query(Organization).filter(Organization.stripe_customer_id == customer_id).first()
    if not org:
        return

    org.subscription_status = "past_due"
    db.commit()
    logger.warning(f"Payment failed for org: {org.id}")


def _handle_subscription_deleted(sub_data: dict, db: Session) -> None:
    """Handle subscription cancellation — set end date for grace period."""
    customer_id = sub_data.get("customer")
    if not customer_id:
        return

    org = db.query(Organization).filter(Organization.stripe_customer_id == customer_id).first()
    if not org:
        return

    # current_period_end is when access should expire
    period_end = sub_data.get("current_period_end")
    if period_end:
        org.subscription_ends_at = datetime.fromtimestamp(period_end, tz=timezone.utc)

    org.subscription_status = "cancelled"
    db.commit()
    logger.info(f"Subscription cancelled for org: {org.id}, access until: {org.subscription_ends_at}")


def _handle_subscription_updated(sub_data: dict, db: Session) -> None:
    """Handle subscription updates (e.g., plan changes)."""
    customer_id = sub_data.get("customer")
    if not customer_id:
        return

    org = db.query(Organization).filter(Organization.stripe_customer_id == customer_id).first()
    if not org:
        return

    # Update status based on Stripe subscription status
    stripe_status = sub_data.get("status")
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "cancelled",
        "unpaid": "past_due",
    }
    new_status = status_map.get(stripe_status)
    if new_status:
        org.subscription_status = new_status
        db.commit()
        logger.info(f"Subscription updated for org: {org.id}, status: {new_status}")
