"""Embedding service for semantic chunk retrieval via pgvector.

Phase 3 of the BidMind AI deep-analysis upgrade.

This service:
  - Embeds document chunks using OpenAI's text-embedding-3-small model
    (1536 dimensions, $0.02 per million tokens — essentially free)
  - Stores embeddings in the ``document_embeddings`` pgvector table
  - Provides cosine-similarity search scoped to a project
  - Handles batching (OpenAI allows up to 2048 texts per call)

Embeddings are created lazily at proposal-generation time. If the
project already has embeddings, they are reused. If files are
re-uploaded, old embeddings should be deleted and regenerated.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document_embedding import DocumentEmbedding, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

# OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-3-small"

# Max texts per OpenAI embeddings API call
BATCH_SIZE = 512

# Max chars per chunk to embed (truncate very long chunks)
MAX_CHUNK_CHARS = 8000


class EmbeddingService:
    """Service for creating, storing, and searching document embeddings."""

    def __init__(self):
        self.settings = get_settings()

    # ---- Embed + Store ---------------------------------------------------

    async def embed_and_store_chunks(
        self,
        project_id: str,
        file_id: Optional[str],
        chunks: List[Any],  # List[DocumentChunk] or list of dicts
        db: Session,
    ) -> int:
        """Embed a list of chunks and store them in the database.

        Args:
            project_id: The project these chunks belong to.
            file_id: The uploaded file these chunks came from (optional).
            chunks: List of DocumentChunk objects or dicts with
                text/page/section/chunk_type keys.
            db: Database session.

        Returns:
            Number of embeddings created.
        """
        if not chunks:
            return 0

        # Normalize chunks to dicts
        chunk_dicts = []
        for c in chunks:
            if isinstance(c, dict):
                chunk_dicts.append(c)
            elif hasattr(c, "to_dict"):
                chunk_dicts.append(c.to_dict())
            else:
                chunk_dicts.append({
                    "text": getattr(c, "text", ""),
                    "page": getattr(c, "page", 1),
                    "section": getattr(c, "section", None),
                    "chunk_type": getattr(c, "chunk_type", "paragraph"),
                })

        # Filter out empty chunks
        chunk_dicts = [c for c in chunk_dicts if c.get("text", "").strip()]

        if not chunk_dicts:
            return 0

        # Extract texts for embedding (truncate very long chunks)
        texts = [
            c["text"][:MAX_CHUNK_CHARS] for c in chunk_dicts
        ]

        # Embed in batches
        all_embeddings = await self._embed_texts_batched(texts)

        if len(all_embeddings) != len(chunk_dicts):
            logger.error(
                f"Embedding count mismatch: {len(all_embeddings)} embeddings "
                f"for {len(chunk_dicts)} chunks"
            )
            return 0

        # Store in database (skip chunks whose embedding failed)
        count = 0
        for chunk_dict, embedding_vector in zip(chunk_dicts, all_embeddings):
            if embedding_vector is None:
                continue  # Embedding failed for this chunk — don't store a zero vector
            record = DocumentEmbedding(
                id=uuid.uuid4(),
                project_id=project_id,
                file_id=file_id,
                chunk_text=chunk_dict["text"][:MAX_CHUNK_CHARS],
                chunk_page=chunk_dict.get("page"),
                chunk_section=chunk_dict.get("section"),
                chunk_type=chunk_dict.get("chunk_type"),
                embedding=embedding_vector,
            )
            db.add(record)
            count += 1

        db.flush()
        logger.info(
            f"Stored {count} embeddings for project {project_id}"
        )
        return count

    # ---- Search ----------------------------------------------------------

    async def search_similar(
        self,
        project_id: str,
        query_text: str,
        db: Session,
        top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        """Find the most similar chunks to a query string.

        Uses pgvector's cosine distance operator (<=>) with an HNSW index.
        Results are scoped to the given project.

        Args:
            project_id: Scope search to this project's embeddings.
            query_text: The text to find similar chunks for.
            db: Database session.
            top_k: Number of results to return.

        Returns:
            List of dicts: {text, page, section, chunk_type, similarity}
            sorted by similarity descending (1.0 = identical).
        """
        # Embed the query
        query_embedding = await self._embed_single(query_text)
        if not query_embedding:
            return []

        # Convert to pgvector-compatible string
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Cosine similarity search via pgvector
        # cosine_distance = 1 - cosine_similarity, so we ORDER BY distance ASC
        # and convert back to similarity for the result
        results = db.execute(
            text("""
                SELECT
                    chunk_text,
                    chunk_page,
                    chunk_section,
                    chunk_type,
                    1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity
                FROM document_embeddings
                WHERE project_id = CAST(:project_id AS uuid)
                ORDER BY embedding <=> CAST(:query_vec AS vector)
                LIMIT :top_k
            """),
            {
                "query_vec": vec_str,
                "project_id": project_id,
                "top_k": top_k,
            },
        ).fetchall()

        return [
            {
                "text": row[0],
                "page": row[1],
                "section": row[2],
                "chunk_type": row[3],
                "similarity": round(float(row[4]), 4),
            }
            for row in results
        ]

    # ---- Helpers ---------------------------------------------------------

    def has_embeddings(self, project_id: str, db: Session) -> bool:
        """Check if a project already has embeddings stored."""
        result = db.execute(
            text(
                "SELECT EXISTS("
                "  SELECT 1 FROM document_embeddings "
                "  WHERE project_id = CAST(:pid AS uuid) LIMIT 1"
                ")"
            ),
            {"pid": project_id},
        ).scalar()
        return bool(result)

    def delete_project_embeddings(self, project_id: str, db: Session) -> int:
        """Delete all embeddings for a project (e.g., before regenerating)."""
        result = db.execute(
            text(
                "DELETE FROM document_embeddings WHERE project_id = CAST(:pid AS uuid)"
            ),
            {"pid": project_id},
        )
        count = result.rowcount
        db.flush()
        if count:
            logger.info(f"Deleted {count} embeddings for project {project_id}")
        return count

    # ---- OpenAI API calls ------------------------------------------------

    async def _embed_texts_batched(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Embed a list of texts in batches using OpenAI's API.

        Returns a list of embedding vectors in the same order as input.
        """
        from openai import AsyncOpenAI

        all_embeddings: List[List[float]] = []

        async with AsyncOpenAI(api_key=self.settings.openai_api_key) as client:
            for i in range(0, len(texts), BATCH_SIZE):
                batch = texts[i : i + BATCH_SIZE]
                try:
                    response = await client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=batch,
                    )
                    # Response data is sorted by index
                    batch_embeddings = [
                        item.embedding
                        for item in sorted(response.data, key=lambda x: x.index)
                    ]
                    all_embeddings.extend(batch_embeddings)
                except Exception as e:
                    logger.error(f"Embedding API error on batch {i}: {e}")
                    # Fill with None to maintain alignment — the store step
                    # skips None entries so failed batches don't pollute the
                    # database with zero vectors.
                    all_embeddings.extend([None] * len(batch))

        return all_embeddings

    async def _embed_single(self, text_input: str) -> Optional[List[float]]:
        """Embed a single text string. Returns the vector or None on error."""
        from openai import AsyncOpenAI

        async with AsyncOpenAI(api_key=self.settings.openai_api_key) as client:
            try:
                response = await client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text_input[:MAX_CHUNK_CHARS],
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"Embedding API error: {e}")
                return None
