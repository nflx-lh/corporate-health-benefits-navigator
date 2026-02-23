import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Ensure backend package is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))


def _load_env() -> None:
    """
    Load test env in a predictable order:
    1) .env.test (if present)
    2) .env (fallback)
    """
    env_test = REPO_ROOT / ".env.test"
    env_main = REPO_ROOT / ".env"

    if env_test.exists():
        load_dotenv(env_test, override=False)
    if env_main.exists():
        load_dotenv(env_main, override=False)


def pytest_configure(config):
    _load_env()

    # Safe, deterministic defaults for tests
    os.environ.setdefault("ENV", "test")
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

    # No DB in test env — repos use CSV only (fallback tests patch to "dual")
    os.environ.setdefault("REPO_MODE", "csv_only")

    # Critical: avoid cross-test 429 pollution
    os.environ.setdefault("RATE_LIMIT", "100000/minute")

    # LLM (Phase 8)
    os.environ.setdefault("LLM_PROVIDER", "openai")
    os.environ.setdefault("LLM_ENABLED", "false")
    os.environ.setdefault("LLM_MODEL_NAME", "gpt-4o-mini")
    os.environ.setdefault("LLM_TIMEOUT_MS", "10000")
    os.environ.setdefault("MAX_EXPLAINER_RETRIES", "1")

    # Embeddings
    os.environ.setdefault("EMBEDDING_PROVIDER", "openai")
    os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-3-small")
    os.environ.setdefault("EMBEDDING_TIMEOUT_MS", "10000")


@pytest.fixture(autouse=True)
def _reset_slowapi_limiter_state():
    """
    Clear limiter storage between tests so one test cannot consume quota
    for another test (prevents flaky 429s in full-suite runs).
    """
    try:
        from app.main import limiter

        storage = getattr(limiter, "_storage", None)
        if storage is not None and hasattr(storage, "reset"):
            storage.reset()
    except Exception:
        # If app import path changes or limiter not initialized yet,
        # don't fail test setup.
        pass
