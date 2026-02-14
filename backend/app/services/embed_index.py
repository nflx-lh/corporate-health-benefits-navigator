"""Local embedding index builder and loader.

Uses sentence-transformers for embedding and numpy for storage.
No external vector DB required.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.services.chunker import ClauseChunk

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class LocalIndexBuilder:
    """Builds a local embedding index from clause chunks."""

    def __init__(self, embedding_model_name: str = DEFAULT_MODEL) -> None:
        self.embedding_model_name = embedding_model_name
        self._model: Any = None  # lazy-loaded

    def _get_model(self) -> Any:
        """Lazy-load the sentence-transformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.embedding_model_name)
        return self._model

    def build(self, chunks: list[ClauseChunk], index_dir: Path) -> None:
        """Embed *chunks* and persist index artifacts to *index_dir*.

        Creates three files:
        - ``chunks.jsonl``: One JSON object per chunk (metadata).
        - ``embeddings.npy``: float32 matrix of shape (N, dim).
        - ``meta.json``: Index metadata (model, dim, count, timestamp).

        Args:
            chunks: Clause chunks to embed.
            index_dir: Target directory (created if absent).
        """
        index_dir.mkdir(parents=True, exist_ok=True)

        model = self._get_model()
        texts = [c.text for c in chunks]
        embeddings: np.ndarray = model.encode(texts, show_progress_bar=False)
        embeddings = embeddings.astype(np.float32)

        # chunks.jsonl
        with open(index_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
            for chunk in chunks:
                row = {
                    "chunk_id": chunk.chunk_id,
                    "clause_id": chunk.clause_id,
                    "source_file": chunk.source_file,
                    "section": chunk.section,
                    "text": chunk.text,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        # embeddings.npy
        np.save(index_dir / "embeddings.npy", embeddings)

        # meta.json
        meta = {
            "embedding_model": self.embedding_model_name,
            "dim": int(embeddings.shape[1]),
            "chunk_count": len(chunks),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(index_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)


class LocalIndexStore:
    """Loads a previously built local embedding index."""

    @staticmethod
    def load(index_dir: Path) -> tuple[list[dict[str, Any]], np.ndarray, dict[str, Any]]:
        """Load index artifacts from *index_dir*.

        Returns:
            Tuple of (chunk_metadata_list, embeddings_matrix, meta_dict).

        Raises:
            FileNotFoundError: If any expected artifact is missing.
        """
        chunks_path = index_dir / "chunks.jsonl"
        embeddings_path = index_dir / "embeddings.npy"
        meta_path = index_dir / "meta.json"

        for p in (chunks_path, embeddings_path, meta_path):
            if not p.exists():
                raise FileNotFoundError(f"Missing index artifact: {p}")

        chunk_rows: list[dict[str, Any]] = []
        with open(chunks_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    chunk_rows.append(json.loads(line))

        embeddings = np.load(embeddings_path)
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        return chunk_rows, embeddings, meta
