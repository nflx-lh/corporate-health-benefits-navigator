#!/usr/bin/env bash
set -e

INDEX_DIR="${DATA_ROOT:-/app/data}/index"
POLICY_DIR="${DATA_ROOT:-/app/data}/raw/policies"

# Build retrieval index on first startup if missing and API key available.
# If index already exists or no API key, skip silently — retriever degrades gracefully.
if [ ! -f "$INDEX_DIR/meta.json" ] && [ -n "${OPENAI_API_KEY:-}" ] && [ -d "$POLICY_DIR" ]; then
    echo "[entrypoint] Building retrieval index on first startup..."
    python /app/scripts/build_index.py \
        --policy-dir "$POLICY_DIR" \
        --index-dir "$INDEX_DIR" \
        || echo "[entrypoint] Index build failed (non-fatal); retriever will return empty results"
fi

exec "$@"
