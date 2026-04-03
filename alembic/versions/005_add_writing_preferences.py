"""Add CompanyWritingPreferences model.

Revision ID: 005
Revises: 004
Create Date: 2026-04-03 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Create company_writing_preferences table."""
    op.create_table(
        'company_writing_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tone_level', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('brand_voice_tags', postgresql.JSON(), nullable=False, server_default='[]'),
        sa.Column('language_complexity', sa.String(20), nullable=False, server_default='standard'),
        sa.Column('company_jargon', sa.Text(), nullable=True),
        sa.Column('must_include', postgresql.JSON(), nullable=False, server_default='[]'),
        sa.Column('do_not_include', sa.Text(), nullable=True),
        sa.Column('focus_areas', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.Column(
            'required_sections',
            postgresql.JSON(),
            nullable=False,
            server_default='["cover_letter", "executive_summary", "understanding_of_requirements", "proposed_solution", "why_us", "pricing_positioning", "risk_mitigation", "closing_statement"]'
        ),
        sa.Column('custom_sections', postgresql.JSON(), nullable=False, server_default='[]'),
        sa.Column('section_order', postgresql.JSON(), nullable=True),
        sa.Column('section_length_multipliers', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='fk_writing_prefs_company_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', name='uq_company_writing_prefs')
    )
    # Create index on company_id for faster lookups
    op.create_index(
        op.f('ix_company_writing_preferences_company_id'),
        'company_writing_preferences',
        ['company_id'],
        unique=False
    )


def downgrade():
    """Drop company_writing_preferences table."""
    op.drop_index(
        op.f('ix_company_writing_preferences_company_id'),
        table_name='company_writing_preferences'
    )
    op.drop_table('company_writing_preferences')
