"""DocumentEmbedding model for semantic chunk retrieval via pgvector.

Phase 3 of the BidMind AI deep-analysis upgrade.

Each row stores a single document chunk along with its OpenAI embedding
vector (text-embedding-3-small, 1536 dimensions). The table uses pgvector's
HNSW index for fast cosine-similarity search.

Embeddings are created lazily at proposal-generation time (if not already
present for the project) and reused across multiple proposal generations.
If files are re-uploaded, old embeddings for that project are deleted and
regenerated.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

from app.db.base import BaseModel


# OpenAI text-embedding-3-small produces 1536-dimensional vectors
EMBEDDING_DIMENSIONS = 1536


class DocumentEmbedding(BaseModel):
    """A single document chunk with its embedding vector."""

    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Which project and file this chunk belongs to
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploaded_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Chunk content and metadata (mirrors DocumentChunk from file_parser)
    chunk_text = Column(Text, nullable=False)
    chunk_page = Column(Integer, nullable=True)
    chunk_section = Column(String(500), nullable=True)
    chunk_type = Column(String(50), nullable=True)  # heading/paragraph/table/etc.

    # The embedding vector (1536 dims for text-embedding-3-small)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)

    def __repr__(self):
        return (
            f"<DocumentEmbedding(id={self.id}, "
            f"page={self.chunk_page}, "
            f"section={self.chunk_section!r:.30})>"
        )
