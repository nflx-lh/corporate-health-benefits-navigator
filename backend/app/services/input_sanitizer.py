"""Input sanitization for prompt injection and output leakage prevention."""

from __future__ import annotations

import re

# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(all\s+)?previous\s+instructions', re.IGNORECASE),
    re.compile(r'ignore\s+(all\s+)?above', re.IGNORECASE),
    re.compile(r'system\s*prompt', re.IGNORECASE),
    re.compile(r'<\s*/?\s*system\s*>', re.IGNORECASE),
    re.compile(r'\[\s*INST\s*\]', re.IGNORECASE),
    re.compile(r'you\s+are\s+now', re.IGNORECASE),
    re.compile(r'act\s+as\s+(a\s+)?', re.IGNORECASE),
    re.compile(r'new\s+instructions?\s*:', re.IGNORECASE),
    re.compile(r'forget\s+(everything|all)', re.IGNORECASE),
]

# Patterns for internal file paths that shouldn't leak in outputs
_FILE_PATH_PATTERN = re.compile(
    r'(?:[A-Za-z]:\\|/(?:home|var|usr|etc|opt|tmp|app|backend))[^\s"\']*\.(?:py|json|csv|yaml|yml|toml|cfg|ini|env)',
    re.IGNORECASE,
)


def sanitize_question(question: str) -> str:
    """Strip known injection patterns from the user question.

    Returns the cleaned question with injection markers removed.
    """
    cleaned = question
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub('', cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def strip_file_paths(text: str) -> str:
    """Remove internal file paths from output text."""
    return _FILE_PATH_PATTERN.sub('[internal]', text)


def sanitize_decision_path(path: list[str]) -> list[str]:
    """Ensure decision_path entries don't leak file paths."""
    return [strip_file_paths(entry) for entry in path]
