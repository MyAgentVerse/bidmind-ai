"""Add proposal feedback/learning loop tables.

Phase 5 of the BidMind AI deep-analysis upgrade.

Creates 4 tables that enable the AI to learn from past proposals:

  - proposal_preferences: org-level writing preferences (tone, voice, etc.)
  - proposal_generations: tracks each generated proposal for feedback
  - proposal_feedback: user ratings + tags on generated proposals
  - proposal_learnings: aggregated lessons per org (common issues, preferences)

Note: created_by columns are nullable to support proposal generation
without auth context (the current state). When auth is wired into the
proposal endpoints, these will be populated.

Revision ID: 013
Revises: 012
Create Date: 2026-04-12
"""

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. proposal_preferences (org-level writing config)
    op.execute("""
        CREATE TABLE proposal_preferences (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            tone_level INTEGER DEFAULT 3,
            brand_voice_tags JSONB,
            language_complexity VARCHAR(50),
            company_jargon TEXT,
            must_include JSONB,
            do_not_include TEXT,
            focus_areas JSONB,
            section_lengths JSONB,
            custom_sections JSONB,
            section_order JSONB,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_by UUID REFERENCES users(id),
            CONSTRAINT uq_proposal_preferences_org UNIQUE (organization_id)
        )
    """)
    op.execute("CREATE INDEX idx_org_preferences ON proposal_preferences (organization_id)")

    # 2. proposal_generations (tracks each AI generation)
    op.execute("""
        CREATE TABLE proposal_generations (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            created_by UUID REFERENCES users(id),
            proposal_title VARCHAR(500) NOT NULL,
            proposal_type VARCHAR(100) NOT NULL DEFAULT 'bid',
            proposal_content TEXT,
            proposal_metadata JSONB,
            writing_preferences JSONB,
            status VARCHAR(50) DEFAULT 'draft',
            parent_proposal_id UUID REFERENCES proposal_generations(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
            regenerated_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX idx_org_proposals ON proposal_generations (organization_id, created_at)")
    op.execute("CREATE INDEX idx_parent_proposal ON proposal_generations (parent_proposal_id)")
    op.execute("CREATE INDEX idx_gen_created_by ON proposal_generations (created_by)")

    # 3. proposal_feedback (user ratings on proposals)
    op.execute("""
        CREATE TABLE proposal_feedback (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            proposal_id UUID NOT NULL REFERENCES proposal_generations(id) ON DELETE CASCADE,
            rating VARCHAR(20) NOT NULL,
            feedback_text TEXT,
            feedback_tags JSONB,
            action_taken VARCHAR(50),
            regenerated_proposal_id UUID REFERENCES proposal_generations(id) ON DELETE SET NULL,
            created_by UUID REFERENCES users(id),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
    """)
    op.execute("CREATE INDEX idx_proposal_feedback ON proposal_feedback (proposal_id)")
    op.execute("CREATE INDEX idx_org_feedback ON proposal_feedback (organization_id, created_at)")
    op.execute("CREATE INDEX idx_feedback_created_by ON proposal_feedback (created_by)")

    # 4. proposal_learnings (aggregated AI memory per org)
    op.execute("""
        CREATE TABLE proposal_learnings (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            total_proposals_generated INTEGER DEFAULT 0,
            total_feedback_entries INTEGER DEFAULT 0,
            total_regenerations INTEGER DEFAULT 0,
            love_count INTEGER DEFAULT 0,
            okay_count INTEGER DEFAULT 0,
            not_right_count INTEGER DEFAULT 0,
            common_issues JSONB,
            learned_preferences JSONB,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
            last_feedback_at TIMESTAMP,
            CONSTRAINT uq_proposal_learnings_org UNIQUE (organization_id)
        )
    """)
    op.execute("CREATE INDEX idx_org_learnings ON proposal_learnings (organization_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS proposal_feedback CASCADE")
    op.execute("DROP TABLE IF EXISTS proposal_generations CASCADE")
    op.execute("DROP TABLE IF EXISTS proposal_learnings CASCADE")
    op.execute("DROP TABLE IF EXISTS proposal_preferences CASCADE")
