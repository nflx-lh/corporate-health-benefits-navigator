"""Password hashing and temporary password generation."""

from __future__ import annotations

import secrets

import bcrypt


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plaintext password."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def generate_temp_password(length: int = 14) -> str:
    """Generate a URL-safe temporary password trimmed to *length* characters."""
    return secrets.token_urlsafe(length)[:length]
