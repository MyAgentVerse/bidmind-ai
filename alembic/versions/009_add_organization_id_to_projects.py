"""Add organization_id to projects table for multi-tenant support.

Revision ID: 009
Revises: 008
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add organization_id column to projects table."""
    op.add_column(
        'projects',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_projects_organization_id',
        'projects',
        'organizations',
        ['organization_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index(
        op.f('ix_projects_organization_id'),
        'projects',
        ['organization_id']
    )


def downgrade() -> None:
    """Remove organization_id column from projects table."""
    op.drop_index(op.f('ix_projects_organization_id'), table_name='projects')
    op.drop_constraint('fk_projects_organization_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'organization_id')
