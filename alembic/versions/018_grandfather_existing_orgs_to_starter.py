"""Grandfather existing organizations into Starter tier with lifetime access.

Context: pre-billing, production orgs existed without subscription columns.
Migration 016 added columns defaulting to tier="none" which would immediately
lock out all existing users from Pro-only features and usage limits. To keep
early testers whole, flip every org that currently has tier="none" up to
Starter with the lifetime flag so they keep access to Starter-tier features
for free, forever.

Running this migration a second time is a no-op — it only touches tier="none"
rows, and new orgs created after the billing launch stay on tier="none"
(the whole point of the default).

Revision ID: 018
Revises: 017
Create Date: 2026-04-14
"""

from alembic import op


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE organizations
        SET subscription_tier = 'starter',
            subscription_status = 'active',
            has_lifetime_starter = TRUE,
            subscription_started_at = COALESCE(subscription_started_at, NOW())
        WHERE subscription_tier = 'none'
        """
    )


def downgrade() -> None:
    # Irreversible by design — we can't tell which orgs were grandfathered
    # vs which legitimately bought Starter after the fact. No-op.
    pass
