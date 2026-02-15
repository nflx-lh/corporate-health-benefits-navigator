"""B-708 – Secrets Management Hygiene tests."""

from __future__ import annotations

import pathlib
import re

import pytest

from app.config import Settings


BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1] / "backend"


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------

class TestJwtSecretChangeMeRejectedInProd:
    def test_prod_rejects_change_me(self):
        s = Settings()
        s.APP_ENV = "production"
        s.JWT_SECRET = "change_me"
        with pytest.raises(ValueError, match="JWT_SECRET must not be"):
            s.validate_secrets()

    def test_staging_rejects_change_me(self):
        s = Settings()
        s.APP_ENV = "staging"
        s.JWT_SECRET = "change_me"
        with pytest.raises(ValueError, match="JWT_SECRET must not be"):
            s.validate_secrets()

    def test_dev_allows_change_me(self):
        s = Settings()
        s.APP_ENV = "development"
        s.JWT_SECRET = "change_me"
        # Should not raise
        s.validate_secrets()

    def test_prod_accepts_strong_secret(self):
        s = Settings()
        s.APP_ENV = "production"
        s.JWT_SECRET = "a-very-strong-production-secret-key-here"
        # Should not raise
        s.validate_secrets()


# ---------------------------------------------------------------------------
# Source scan: no hardcoded secrets in .py files
# ---------------------------------------------------------------------------

# Patterns that suggest hardcoded secrets (excluding test files and config defaults)
_SECRET_PATTERNS = [
    re.compile(r'(sk-[A-Za-z0-9]{20,})'),                    # OpenAI-style keys
    re.compile(r'AKIA[A-Z0-9]{16}'),                          # AWS access keys
    re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE),  # Hardcoded passwords
]

# Files that are allowed to have these patterns (test fixtures, credential maps)
_ALLOWED_FILES = {
    "routes_auth.py",   # MVP demo credentials (documented as placeholder)
    "conftest.py",
}


class TestNoHardcodedSecretsInSource:
    def test_no_hardcoded_secrets_in_source(self):
        """Scan backend .py files for common secret patterns."""
        violations = []
        for py_file in BACKEND_ROOT.rglob("*.py"):
            if py_file.name in _ALLOWED_FILES:
                continue
            if "test" in py_file.name:
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern in _SECRET_PATTERNS:
                matches = pattern.findall(content)
                if matches:
                    violations.append(
                        f"{py_file.relative_to(BACKEND_ROOT)}: matched pattern {pattern.pattern} -> {matches}"
                    )
        assert not violations, f"Hardcoded secrets found:\n" + "\n".join(violations)
