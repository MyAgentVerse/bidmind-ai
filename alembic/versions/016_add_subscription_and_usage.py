"""Add subscription fields to organizations and usage_records table.

Revision ID: 016
Revises: 015
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Subscription columns on organizations
    op.add_column("organizations", sa.Column("subscription_tier", sa.String(20), nullable=False, server_default="none"))
    op.add_column("organizations", sa.Column("subscription_status", sa.String(20), nullable=False, server_default="inactive"))
    op.add_column("organizations", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("stripe_subscription_id", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("subscription_started_at", sa.DateTime(), nullable=True))
    op.add_column("organizations", sa.Column("subscription_ends_at", sa.DateTime(), nullable=True))

    op.create_unique_constraint("uq_org_stripe_customer_id", "organizations", ["stripe_customer_id"])

    # Usage records table
    op.create_table(
        "usage_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("usage_type", sa.String(50), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "usage_type", "period_start", name="uq_usage_org_type_period"),
    )


def downgrade() -> None:
    op.drop_table("usage_records")
    op.drop_constraint("uq_org_stripe_customer_id", "organizations", type_="unique")
    op.drop_column("organizations", "subscription_ends_at")
    op.drop_column("organizations", "subscription_started_at")
    op.drop_column("organizations", "stripe_subscription_id")
    op.drop_column("organizations", "stripe_customer_id")
    op.drop_column("organizations", "subscription_status")
    op.drop_column("organizations", "subscription_tier")
