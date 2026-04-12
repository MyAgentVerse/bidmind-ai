"""Add document_embeddings table with pgvector for semantic retrieval.

Phase 3 of the BidMind AI deep-analysis upgrade.

Creates the document_embeddings table which stores document chunks alongside
their OpenAI embedding vectors (1536 dimensions from text-embedding-3-small).
Uses pgvector's HNSW index for fast cosine-similarity search during proposal
generation.

The table is created via raw SQL because Alembic's column-type system doesn't
natively understand pgvector's ``vector(N)`` type. The HNSW index uses
``vector_cosine_ops`` for cosine-similarity search.

Revision ID: 012
Revises: 011
Create Date: 2026-04-12
"""

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create the table with a vector(1536) column via raw SQL.
    # Uses IF NOT EXISTS because init_db()'s create_all may have already
    # created this table on a prior deploy.
    op.execute("""
        CREATE TABLE IF NOT EXISTS document_embeddings (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            file_id UUID REFERENCES uploaded_files(id) ON DELETE CASCADE,
            chunk_text TEXT NOT NULL,
            chunk_page INTEGER,
            chunk_section VARCHAR(500),
            chunk_type VARCHAR(50),
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
    """)

    # Filtering indexes (used to scope vector search to a project).
    # IF NOT EXISTS prevents crashes when table was pre-created by init_db().
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_embeddings_project_id "
        "ON document_embeddings (project_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_embeddings_file_id "
        "ON document_embeddings (file_id)"
    )

    # HNSW index for fast cosine-similarity search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding_hnsw "
        "ON document_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_embeddings CASCADE")
