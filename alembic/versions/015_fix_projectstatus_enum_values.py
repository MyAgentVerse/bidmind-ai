"""Fix projectstatus enum to use lowercase values.

The ORM sends lowercase ('created', 'file_uploaded', etc.) but the
Postgres enum was created with uppercase values ('CREATED', 'FILE_UPLOADED').
This migration recreates the enum with lowercase values and updates
existing rows.

Revision ID: 015
Revises: 014
Create Date: 2026-04-12
"""

from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename old enum type
    op.execute("ALTER TYPE projectstatus RENAME TO projectstatus_old")

    # Create new enum with lowercase values
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'created', 'file_uploaded', 'analyzed', 'proposal_generated'
        )
    """)

    # Update the column to use the new enum
    op.execute("""
        ALTER TABLE projects
        ALTER COLUMN status TYPE projectstatus
        USING LOWER(status::text)::projectstatus
    """)

    # Drop old enum
    op.execute("DROP TYPE projectstatus_old")


def downgrade() -> None:
    op.execute("ALTER TYPE projectstatus RENAME TO projectstatus_old")
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'CREATED', 'FILE_UPLOADED', 'ANALYZED', 'PROPOSAL_GENERATED'
        )
    """)
    op.execute("""
        ALTER TABLE projects
        ALTER COLUMN status TYPE projectstatus
        USING UPPER(status::text)::projectstatus
    """)
    op.execute("DROP TYPE projectstatus_old")
