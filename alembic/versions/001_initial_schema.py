"""Initial schema creation

Revision ID: 001
Revises:
Create Date: 2024-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('status', sa.Enum('created', 'file_uploaded', 'analyzed', 'proposal_generated', name='projectstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_status'), 'projects', ['status'], unique=False)
    op.create_index(op.f('ix_projects_title'), 'projects', ['title'], unique=False)
    op.create_index(op.f('ix_projects_created_at'), 'projects', ['created_at'], unique=False)
    op.create_index(op.f('ix_projects_updated_at'), 'projects', ['updated_at'], unique=False)

    # Create uploaded_files table
    op.create_table(
        'uploaded_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('stored_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('mime_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_uploaded_files_id'), 'uploaded_files', ['id'], unique=False)
    op.create_index(op.f('ix_uploaded_files_project_id'), 'uploaded_files', ['project_id'], unique=False)
    op.create_index(op.f('ix_uploaded_files_stored_filename'), 'uploaded_files', ['stored_filename'], unique=True)
    op.create_index(op.f('ix_uploaded_files_created_at'), 'uploaded_files', ['created_at'], unique=False)
    op.create_index(op.f('ix_uploaded_files_updated_at'), 'uploaded_files', ['updated_at'], unique=False)

    # Create analysis_results table
    op.create_table(
        'analysis_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(100), nullable=True),
        sa.Column('opportunity_summary', sa.Text(), nullable=True),
        sa.Column('scope_of_work', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mandatory_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deadlines', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evaluation_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('budget_clues', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risks', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('fit_score', sa.Float(), nullable=True),
        sa.Column('usp_suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('pricing_strategy_summary', sa.Text(), nullable=True),
        sa.Column('raw_ai_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_results_id'), 'analysis_results', ['id'], unique=False)
    op.create_index(op.f('ix_analysis_results_project_id'), 'analysis_results', ['project_id'], unique=True)
    op.create_index(op.f('ix_analysis_results_created_at'), 'analysis_results', ['created_at'], unique=False)
    op.create_index(op.f('ix_analysis_results_updated_at'), 'analysis_results', ['updated_at'], unique=False)

    # Create proposal_drafts table
    op.create_table(
        'proposal_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('executive_summary', sa.Text(), nullable=True),
        sa.Column('understanding_of_requirements', sa.Text(), nullable=True),
        sa.Column('proposed_solution', sa.Text(), nullable=True),
        sa.Column('why_us', sa.Text(), nullable=True),
        sa.Column('pricing_positioning', sa.Text(), nullable=True),
        sa.Column('risk_mitigation', sa.Text(), nullable=True),
        sa.Column('closing_statement', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_proposal_drafts_id'), 'proposal_drafts', ['id'], unique=False)
    op.create_index(op.f('ix_proposal_drafts_project_id'), 'proposal_drafts', ['project_id'], unique=True)
    op.create_index(op.f('ix_proposal_drafts_created_at'), 'proposal_drafts', ['created_at'], unique=False)
    op.create_index(op.f('ix_proposal_drafts_updated_at'), 'proposal_drafts', ['updated_at'], unique=False)

    # Create ai_edit_history table
    op.create_table(
        'ai_edit_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_name', sa.String(100), nullable=False),
        sa.Column('instruction', sa.Text(), nullable=False),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('edited_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_edit_history_id'), 'ai_edit_history', ['id'], unique=False)
    op.create_index(op.f('ix_ai_edit_history_project_id'), 'ai_edit_history', ['project_id'], unique=False)
    op.create_index(op.f('ix_ai_edit_history_created_at'), 'ai_edit_history', ['created_at'], unique=False)
    op.create_index(op.f('ix_ai_edit_history_updated_at'), 'ai_edit_history', ['updated_at'], unique=False)


def downgrade() -> None:
    """Drop all tables."""

    # Drop tables in reverse order
    op.drop_table('ai_edit_history')
    op.drop_table('proposal_drafts')
    op.drop_table('analysis_results')
    op.drop_table('uploaded_files')
    op.drop_table('projects')
