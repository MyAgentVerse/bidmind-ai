"""Secure company profiles by organization ownership.

Revision ID: 010
Revises: 009
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add organization_id to companies
    op.add_column(
        "companies",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Foreign key to organizations
    op.create_foreign_key(
        "fk_companies_organization_id",
        "companies",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Index for tenant scoping queries
    op.create_index(
        "ix_companies_organization_id",
        "companies",
        ["organization_id"],
        unique=False,
    )

    # One company profile per organization
    op.create_unique_constraint(
        "uq_companies_organization_id",
        "companies",
        ["organization_id"],
    )

    # Safe because your companies table currently has 0 rows
    op.alter_column("companies", "organization_id", nullable=False)


def downgrade() -> None:
    op.alter_column("companies", "organization_id", nullable=True)

    op.drop_constraint(
        "uq_companies_organization_id",
        "companies",
        type_="unique",
    )

    op.drop_index(
        "ix_companies_organization_id",
        table_name="companies",
    )

    op.drop_constraint(
        "fk_companies_organization_id",
        "companies",
        type_="foreignkey",
    )

    op.drop_column("companies", "organization_id")
    