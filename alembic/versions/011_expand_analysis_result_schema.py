"""Expand analysis_results with deep-analysis fields (Phase 1 Step C).

Adds 12 new columns to analysis_results so the LLM can extract the
artifacts a real proposal team needs:

  - compliance_matrix: every requirement with type, source, evidence
  - eligibility_requirements: hard go/no-go gates
  - submission_instructions: page limits, format, where to submit
  - pricing_format: CLINs, line items, basis
  - key_personnel_requirements: required roles + certs + clearance
  - naics_codes: list of NAICS codes (queryable for filtering)
  - set_aside_status: 8(a), SDVOSB, WOSB, HUBZone, etc. (indexed)
  - contract_type: FFP, T&M, IDIQ, CPFF, etc. (indexed)
  - period_of_performance: e.g., "5 years base + 5 option years"
  - place_of_performance: e.g., "Washington DC"
  - estimated_value: e.g., "$5M-$10M"
  - contracting_officer: name, email, phone, etc.

All columns are nullable so existing rows are unaffected. Two columns
(set_aside_status, contract_type) get an index because they're the
two most likely filter fields ("show me everything that's a SDVOSB
set-aside" / "show me all firm-fixed-price IDIQ opportunities").

Less-queryable fields (insurance, required forms, clauses by reference,
wage determinations, protest procedures, funding source, past
performance) live in the existing JSONB raw_ai_json column — no new
columns needed for those.

Revision ID: 011
Revises: 010
Create Date: 2026-04-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


# All new columns are nullable JSONB or short strings.
# Adding nullable columns is a fast metadata-only operation in PostgreSQL,
# so this migration is safe to run on a populated table without locking.
NEW_JSONB_COLUMNS = [
    "eligibility_requirements",
    "compliance_matrix",
    "submission_instructions",
    "pricing_format",
    "key_personnel_requirements",
    "naics_codes",
    "contracting_officer",
]

NEW_STRING_COLUMNS = [
    ("set_aside_status", 100, True),     # (name, length, indexed?)
    ("contract_type", 100, True),
    ("period_of_performance", 255, False),
    ("place_of_performance", 255, False),
    ("estimated_value", 100, False),
]


def upgrade() -> None:
    # JSONB columns
    for col in NEW_JSONB_COLUMNS:
        op.add_column(
            "analysis_results",
            sa.Column(col, postgresql.JSONB, nullable=True),
        )

    # String columns (with optional indexes)
    for name, length, indexed in NEW_STRING_COLUMNS:
        op.add_column(
            "analysis_results",
            sa.Column(name, sa.String(length=length), nullable=True),
        )
        if indexed:
            op.create_index(
                f"ix_analysis_results_{name}",
                "analysis_results",
                [name],
                unique=False,
            )


def downgrade() -> None:
    # Drop indexes first, then columns, in reverse order.
    for name, _length, indexed in reversed(NEW_STRING_COLUMNS):
        if indexed:
            op.drop_index(
                f"ix_analysis_results_{name}",
                table_name="analysis_results",
            )
        op.drop_column("analysis_results", name)

    for col in reversed(NEW_JSONB_COLUMNS):
        op.drop_column("analysis_results", col)
