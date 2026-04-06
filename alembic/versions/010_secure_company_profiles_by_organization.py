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
    # 1) Add organization_id as nullable first so we can backfill
    op.add_column(
        "companies",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_foreign_key(
        "fk_companies_organization_id",
        "companies",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        op.f("ix_companies_organization_id"),
        "companies",
        ["organization_id"],
        unique=False,
    )

    # 2) Backfill from projects where possible
    #    If a company has projects tied to one organization, assign that org.
    op.execute(
        """
        UPDATE companies c
        SET organization_id = mapping.organization_id
        FROM (
            SELECT
                p.company_id,
                MIN(p.organization_id) AS organization_id
            FROM projects p
            WHERE p.company_id IS NOT NULL
              AND p.organization_id IS NOT NULL
            GROUP BY p.company_id
        ) AS mapping
        WHERE c.id = mapping.company_id
          AND c.organization_id IS NULL
        """
    )

    # 3) Clean up projects that point to a company from a different org
    op.execute(
        """
        UPDATE projects p
        SET company_id = NULL
        FROM companies c
        WHERE p.company_id = c.id
          AND p.organization_id IS NOT NULL
          AND c.organization_id IS NOT NULL
          AND p.organization_id <> c.organization_id
        """
    )

    # 4) For safer enforcement, require uniqueness on organization_id
    #    This assumes one company profile per organization.
    op.create_unique_constraint(
        "uq_companies_organization_id",
        "companies",
        ["organization_id"],
    )

    # 5) Make organization_id non-null only if your existing data supports it.
    #    This line is safe if every existing company has been backfilled.
    #    If migration fails here due to old dirty data, fix data first and rerun.
    op.alter_column("companies", "organization_id", nullable=False)


def downgrade() -> None:
    op.alter_column("companies", "organization_id", nullable=True)
    op.drop_constraint("uq_companies_organization_id", "companies", type_="unique")
    op.drop_index(op.f("ix_companies_organization_id"), table_name="companies")
    op.drop_constraint("fk_companies_organization_id", "companies", type_="foreignkey")
    op.drop_column("companies", "organization_id")