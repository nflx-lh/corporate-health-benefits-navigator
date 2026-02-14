"""Smoke tests for the policy retriever.

Creates a tiny temp corpus, builds a temp index, and verifies
retrieval returns citation-ready fields with deterministic ordering.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from app.services.chunker import extract_chunks_from_markdown
from app.services.embed_index import LocalIndexBuilder
from app.services.retriever import PolicyRetriever, RetrievalHit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TINY_POLICY = """\
# Test Policy

## Coverage

**CL-001:** Dental cleaning is covered at 80 percent for Plus plan.

**CL-002:** Root canal treatment requires pre-authorization.

**CL-003:** Orthodontics are excluded for all plan tiers.
"""


@pytest.fixture()
def tiny_index(tmp_path: Path) -> Path:
    """Build a tiny index in a temp directory using the real model."""
    chunks = extract_chunks_from_markdown(TINY_POLICY, "tiny.md")
    builder = LocalIndexBuilder()
    index_dir = tmp_path / "index"
    builder.build(chunks, index_dir)
    return index_dir


# ---------------------------------------------------------------------------
# Tests — citation-ready fields
# ---------------------------------------------------------------------------


class TestRetrievalFields:
    """Verify retrieval returns complete citation-ready hits."""

    def test_returns_retrieval_hits(self, tiny_index: Path) -> None:
        retriever = PolicyRetriever(tiny_index)
        hits = retriever.retrieve("dental cleaning coverage", top_k=2)
        assert len(hits) <= 2
        assert all(isinstance(h, RetrievalHit) for h in hits)

    def test_hit_has_all_fields(self, tiny_index: Path) -> None:
        retriever = PolicyRetriever(tiny_index)
        hits = retriever.retrieve("dental cleaning", top_k=1)
        assert len(hits) == 1
        hit = hits[0]
        assert hit.clause_id.startswith("CL-")
        assert hit.source_file == "tiny.md"
        assert isinstance(hit.section, str)
        assert len(hit.text) > 0
        assert isinstance(hit.score, float)
        assert hit.chunk_id.startswith("tiny.md::")

    def test_top_k_limits_results(self, tiny_index: Path) -> None:
        retriever = PolicyRetriever(tiny_index)
        hits = retriever.retrieve("benefits", top_k=2)
        assert len(hits) <= 2


# ---------------------------------------------------------------------------
# Tests — deterministic tie-break ordering
# ---------------------------------------------------------------------------


class TestDeterministicTieBreak:
    """Verify tie-break ordering when scores are equal.

    Monkeypatches the embedding model to return identical vectors,
    forcing all scores to be equal so tie-break logic is exercised.
    """

    def test_equal_score_ordering(self, tmp_path: Path) -> None:
        """When all scores are identical, results should be sorted by
        source_file ASC, clause_id ASC, chunk_id ASC.
        """
        # Build index with two source files to test cross-file ordering.
        md_a = """\
# A

## Section A

**CL-002:** Clause two from file A.

**CL-001:** Clause one from file A.
"""
        md_b = """\
# B

## Section B

**CL-001:** Clause one from file B.
"""
        chunks_a = extract_chunks_from_markdown(md_a, "a_policy.md")
        chunks_b = extract_chunks_from_markdown(md_b, "b_policy.md")
        all_chunks = chunks_a + chunks_b

        # Build index with constant embeddings so all scores are equal.
        index_dir = tmp_path / "tie_index"
        index_dir.mkdir()

        dim = 8
        n = len(all_chunks)
        constant_emb = np.ones((n, dim), dtype=np.float32)
        np.save(index_dir / "embeddings.npy", constant_emb)

        with open(index_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
            for c in all_chunks:
                f.write(json.dumps({
                    "chunk_id": c.chunk_id,
                    "clause_id": c.clause_id,
                    "source_file": c.source_file,
                    "section": c.section,
                    "text": c.text,
                }) + "\n")

        meta = {"embedding_model": "mock", "dim": dim, "chunk_count": n, "created_at": "test"}
        with open(index_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f)

        # Mock the sentence-transformer model to return a constant query vector.
        class _MockModel:
            def encode(self, texts: list[str], **kwargs) -> np.ndarray:  # type: ignore[override]
                return np.ones((len(texts), dim), dtype=np.float32)

        with patch(
            "app.services.retriever.SentenceTransformer",
            return_value=_MockModel(),
            create=True,
        ):
            retriever = PolicyRetriever(index_dir, embedding_model_name="mock")
            # Patch in our mock model directly.
            retriever._model = _MockModel()

            hits = retriever.retrieve("anything", top_k=10)

        assert len(hits) == 3

        # All scores should be equal (normalised dot product of identical vectors).
        scores = [h.score for h in hits]
        assert len(set(scores)) == 1, f"Expected equal scores, got {scores}"

        # Tie-break: source_file ASC, then clause_id ASC, then chunk_id ASC.
        # a_policy.md comes before b_policy.md.
        # Within a_policy.md: CL-001 < CL-002.
        assert hits[0].source_file == "a_policy.md"
        assert hits[0].clause_id == "CL-001"
        assert hits[1].source_file == "a_policy.md"
        assert hits[1].clause_id == "CL-002"
        assert hits[2].source_file == "b_policy.md"
        assert hits[2].clause_id == "CL-001"
