"""CLI script to build the local embedding index from policy markdown files.

Usage:
    python scripts/build_index.py [--policy-dir DIR] [--index-dir DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the backend package is importable when running from repo root.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build local embedding index from policy markdown files.",
    )
    parser.add_argument(
        "--policy-dir",
        type=Path,
        default=_REPO_ROOT / "data" / "raw" / "policies",
        help="Directory containing *.md policy files (default: data/raw/policies)",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=_REPO_ROOT / "data" / "index",
        help="Output directory for index artifacts (default: data/index)",
    )
    args = parser.parse_args()

    from app.services.chunker import load_policy_chunks
    from app.services.embed_index import LocalIndexBuilder

    print(f"Loading policies from: {args.policy_dir}")
    chunks = load_policy_chunks(args.policy_dir)
    print(f"  Extracted {len(chunks)} clause chunks")

    if not chunks:
        print("ERROR: No chunks extracted. Check policy directory.", file=sys.stderr)
        sys.exit(1)

    sample_ids = [c.clause_id for c in chunks[:5]]
    print(f"  Sample clause IDs: {sample_ids}")

    print(f"Building index in: {args.index_dir}")
    builder = LocalIndexBuilder()
    builder.build(chunks, args.index_dir)

    # Read back meta for summary.
    import json

    meta = json.loads((args.index_dir / "meta.json").read_text(encoding="utf-8"))
    print("Index built successfully:")
    print(f"  Chunks:    {meta['chunk_count']}")
    print(f"  Dimension: {meta['dim']}")
    print(f"  Model:     {meta['embedding_model']}")
    print(f"  Created:   {meta['created_at']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
