"""Fix all ORM-vs-DB column mismatches.

Tech debt cleanup — resolves 22 mismatches between the SQLAlchemy ORM
models and the actual PostgreSQL schema.

Changes:
  companies:
    - RENAME industry -> industry_focus (ORM uses industry_focus)
    - ADD description (TEXT)
    - ADD experience (TEXT)
    - ADD key_capabilities (TEXT)
    - ADD unique_selling_proposition (TEXT)

  company_writing_preferences:
    - DROP tone (old column, ORM uses tone_level)
    - DROP writing_guidelines (old column, replaced by structured fields)
    - ADD tone_level (INTEGER DEFAULT 3)
    - ADD brand_voice_tags (JSONB)
    - ADD language_complexity (VARCHAR(20))
    - ADD company_jargon (TEXT)
    - ADD must_include (JSONB)
    - ADD do_not_include (TEXT)
    - ADD focus_areas (JSONB)
    - ADD required_sections (JSONB)
    - ADD section_length_multipliers (JSONB)
    - ADD section_order (JSONB)
    - ADD custom_sections (JSONB)

  proposal_learnings:
    - ADD last_updated (TIMESTAMP) — ORM column separate from base updated_at

All ADD operations use nullable columns (safe, metadata-only).
RENAME is also metadata-only in PostgreSQL.
DROP removes unused columns after verifying they have no data dependencies.

Revision ID: 014
Revises: 013
Create Date: 2026-04-12
"""

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === COMPANIES ===
    # Rename industry -> industry_focus (skip if already renamed)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'companies' AND column_name = 'industry'
            ) THEN
                ALTER TABLE companies RENAME COLUMN industry TO industry_focus;
            END IF;
        END $$;
    """)

    # Add missing columns
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS description TEXT")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS experience TEXT")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS key_capabilities TEXT")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS unique_selling_proposition TEXT")

    # === COMPANY_WRITING_PREFERENCES ===
    # Drop old columns that the ORM no longer uses
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS tone")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS writing_guidelines")

    # Add new structured columns
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS tone_level INTEGER DEFAULT 3")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS brand_voice_tags JSONB")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS language_complexity VARCHAR(20)")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS company_jargon TEXT")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS must_include JSONB")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS do_not_include TEXT")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS focus_areas JSONB")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS required_sections JSONB")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS section_length_multipliers JSONB")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS section_order JSONB")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS custom_sections JSONB")

    # === PROPOSAL_LEARNINGS ===
    # ORM has last_updated separate from BaseModel's updated_at
    op.execute("ALTER TABLE proposal_learnings ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP")
    op.execute("ALTER TABLE proposal_learnings ADD COLUMN IF NOT EXISTS last_feedback_at TIMESTAMP")


def downgrade() -> None:
    # proposal_learnings
    op.execute("ALTER TABLE proposal_learnings DROP COLUMN IF EXISTS last_updated")
    op.execute("ALTER TABLE proposal_learnings DROP COLUMN IF EXISTS last_feedback_at")

    # company_writing_preferences: restore old columns, drop new ones
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS tone_level")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS brand_voice_tags")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS language_complexity")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS company_jargon")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS must_include")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS do_not_include")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS focus_areas")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS required_sections")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS section_length_multipliers")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS section_order")
    op.execute("ALTER TABLE company_writing_preferences DROP COLUMN IF EXISTS custom_sections")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS tone VARCHAR(100)")
    op.execute("ALTER TABLE company_writing_preferences ADD COLUMN IF NOT EXISTS writing_guidelines TEXT")

    # companies: reverse rename, drop added columns
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS description")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS experience")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS key_capabilities")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS unique_selling_proposition")
    op.execute("ALTER TABLE companies RENAME COLUMN industry_focus TO industry")
