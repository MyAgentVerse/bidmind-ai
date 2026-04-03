"""Add Company model for company profiles.

Revision ID: 004
Revises: 003_remove_analysis_unique
Create Date: 2026-04-03 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_company_model'
down_revision = '003_remove_analysis_unique'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('unique_selling_proposition', sa.Text(), nullable=True),
        sa.Column('key_capabilities', sa.Text(), nullable=True),
        sa.Column('experience', sa.Text(), nullable=True),
        sa.Column('industry_focus', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)
    op.create_index(op.f('ix_companies_name'), 'companies', ['name'], unique=False)

    # Add company_id to projects table
    op.add_column('projects', sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_projects_company_id'), 'projects', ['company_id'], unique=False)


def downgrade() -> None:
    # Drop company_id from projects
    op.drop_index(op.f('ix_projects_company_id'), table_name='projects')
    op.drop_column('projects', 'company_id')

    # Drop companies table
    op.drop_index(op.f('ix_companies_name'), table_name='companies')
    op.drop_index(op.f('ix_companies_id'), table_name='companies')
    op.drop_table('companies')
