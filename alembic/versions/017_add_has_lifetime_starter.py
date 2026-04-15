"""Add has_lifetime_starter flag for Starter fallback after Pro lapse.

Revision ID: 017
Revises: 016
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "has_lifetime_starter",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Backfill for existing starter owners so they keep lifetime access if they upgrade to Pro.
    op.execute(
        "UPDATE organizations SET has_lifetime_starter = TRUE WHERE subscription_tier = 'starter'"
    )


def downgrade() -> None:
    op.drop_column("organizations", "has_lifetime_starter")
