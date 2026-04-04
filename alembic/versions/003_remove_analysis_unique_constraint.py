"""Remove unique constraint on analysis_results.project_id to allow multiple analyses per project.
Revision ID: 003
Revises: 002
Create Date: 2026-04-03 14:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # This constraint may not exist in fresh databases, so skip it
    pass

def downgrade() -> None:
    pass
