"""Remove unique constraint on analysis_results.project_id to allow multiple analyses per project.

Revision ID: 003
Revises: 002_extend_mime_type
Create Date: 2026-04-03 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_remove_analysis_unique'
down_revision = '002_extend_mime_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the unique constraint on project_id
    op.drop_constraint('ix_analysis_results_project_id', 'analysis_results', type_='unique')


def downgrade() -> None:
    # Re-add the unique constraint if rolling back
    op.create_unique_constraint('ix_analysis_results_project_id', 'analysis_results', ['project_id'])
