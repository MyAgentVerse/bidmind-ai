"""Add password reset fields to users table.

Revision ID: 007
Revises: 006
Create Date: 2026-04-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add reset_token and reset_token_expiry columns to users table."""
    op.add_column('users', sa.Column('reset_token', sa.String(255), nullable=True, unique=True))
    op.add_column('users', sa.Column('reset_token_expiry', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove reset_token and reset_token_expiry columns from users table."""
    op.drop_column('users', 'reset_token_expiry')
    op.drop_column('users', 'reset_token')
