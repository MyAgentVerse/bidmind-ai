"""Extend mime_type column to support longer MIME types

Revision ID: 002
Revises: 001
Create Date: 2026-04-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Extend mime_type column from VARCHAR(50) to VARCHAR(255)."""
    op.alter_column(
        'uploaded_files',
        'mime_type',
        existing_type=sa.String(50),
        type_=sa.String(255),
        existing_nullable=False
    )


def downgrade() -> None:
    """Revert mime_type column back to VARCHAR(50)."""
    op.alter_column(
        'uploaded_files',
        'mime_type',
        existing_type=sa.String(255),
        type_=sa.String(50),
        existing_nullable=False
    )
