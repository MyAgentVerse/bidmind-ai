"""Add organization invites table for invite code system.

Revision ID: 008
Revises: 007
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create organization_invites table."""
    op.create_table(
        'organization_invites',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('code', sa.String(12), nullable=False, unique=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('used_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_organization_invites_code'), 'organization_invites', ['code'], unique=True)
    op.create_index(op.f('ix_organization_invites_organization_id'), 'organization_invites', ['organization_id'])


def downgrade() -> None:
    """Drop organization_invites table."""
    op.drop_index(op.f('ix_organization_invites_organization_id'), table_name='organization_invites')
    op.drop_index(op.f('ix_organization_invites_code'), table_name='organization_invites')
    op.drop_table('organization_invites')
