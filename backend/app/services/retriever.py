"""Policy retriever for citation-ready clause lookup.

Wraps the local embedding index with cosine-similarity search and
deterministic tie-breaking.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.services.embed_index import DEFAULT_MODEL, LocalIndexStore


@dataclass(frozen=True)
class RetrievalHit:
    """A single retrieval result with citation-ready fields."""

    clause_id: str
    source_file: str
    section: str
    text: str
    score: float
    chunk_id: str


class PolicyRetriever:
    """Retrieves top-k clause hits for a free-text query.

    Uses cosine similarity against a pre-built local embedding index,
    with deterministic tie-breaking:
      1) score DESC
      2) source_file ASC
      3) clause_id ASC
      4) chunk_id ASC
    """

    def __init__(
        self,
        index_dir: Path,
        embedding_model_name: str = DEFAULT_MODEL,
    ) -> None:
        self._embedding_model_name = embedding_model_name
        self._model: Any = None
        self._chunks, self._embeddings, self._meta = LocalIndexStore.load(index_dir)

        # Pre-normalise embeddings for cosine similarity.
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        self._normed = self._embeddings / norms

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._embedding_model_name)
        return self._model

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievalHit]:
        """Return the top-*k* clause hits for *query*.

        Args:
            query: Free-text search query.
            top_k: Maximum number of results to return.

        Returns:
            List of :class:`RetrievalHit`, sorted by the deterministic
            tie-break ordering described in the class docstring.
        """
        model = self._get_model()
        q_vec: np.ndarray = model.encode([query], show_progress_bar=False)
        q_vec = q_vec.astype(np.float32).flatten()
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        scores = self._normed @ q_vec  # shape (N,)

        # Build candidate list with all fields needed for sorting.
        candidates: list[tuple[float, str, str, str, int]] = []
        for i, chunk in enumerate(self._chunks):
            candidates.append((
                float(scores[i]),
                chunk["source_file"],
                chunk["clause_id"],
                chunk["chunk_id"],
                i,
            ))

        # Deterministic sort: score DESC, then source_file/clause_id/chunk_id ASC.
        candidates.sort(key=lambda c: (-c[0], c[1], c[2], c[3]))

        results: list[RetrievalHit] = []
        for score_val, _, _, _, idx in candidates[:top_k]:
            chunk = self._chunks[idx]
            results.append(
                RetrievalHit(
                    clause_id=chunk["clause_id"],
                    source_file=chunk["source_file"],
                    section=chunk["section"],
                    text=chunk["text"],
                    score=round(score_val, 6),
                    chunk_id=chunk["chunk_id"],
                )
            )
        return results
