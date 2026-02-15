"""Logging filter that scrubs sensitive patterns from log records."""

from __future__ import annotations

import logging
import re

# Patterns to redact from log messages
_SENSITIVE_PATTERNS = [
    # JWT tokens (three base64 segments separated by dots)
    (re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'), '[REDACTED_JWT]'),
    # Bearer tokens
    (re.compile(r'Bearer\s+[A-Za-z0-9_\-.]+'), 'Bearer [REDACTED]'),
    # password field values in JSON-like strings
    (re.compile(r'("password"\s*:\s*)"[^"]*"'), r'\1"[REDACTED]"'),
    # API keys (common patterns)
    (re.compile(r'(sk-[A-Za-z0-9]{20,})'), '[REDACTED_API_KEY]'),
    (re.compile(r'(api[_-]?key\s*[=:]\s*)["\']?[A-Za-z0-9_\-]{16,}["\']?', re.IGNORECASE), r'\1[REDACTED]'),
]


class SensitiveDataFilter(logging.Filter):
    """Scrub sensitive data from log record messages before emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.msg and isinstance(record.msg, str):
            record.msg = sanitize(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: sanitize(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(sanitize(str(a)) if isinstance(a, str) else a for a in record.args)
        return True


def sanitize(text: str) -> str:
    """Remove sensitive patterns from a string."""
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
