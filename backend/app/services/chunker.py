"""Clause-aware markdown chunker for policy documents.

Splits policy markdown files into one chunk per clause, preserving
clause IDs exactly as written for traceability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClauseChunk:
    """A single clause extracted from a policy document."""

    chunk_id: str
    clause_id: str
    source_file: str
    section: str
    text: str


# Strict clause ID: CL- followed by exactly 3 digits and optional uppercase letter.
CLAUSE_STRICT_RE = re.compile(
    r"^(?:\s*(?:[-*+]\s+)?)(?:\*{0,2})"  # optional bullet + optional bold markers
    r"(?P<clause_id>CL-\d{3}[A-Z]?)\b",
)

# Candidate detector: line starts with optional whitespace/bullet, then a token
# beginning with "CL-".  Used to detect *malformed* clause-start attempts.
# Uses punctuation-safe character class so the token stops at colons, bold
# markers, etc. instead of swallowing them.
CLAUSE_CANDIDATE_RE = re.compile(
    r"^(?:\s*(?:[-*+]\s+)?)(?:\*{0,2})"
    r"(?P<token>CL-[A-Za-z0-9-]+)\b",
)

# Markdown heading.
HEADING_RE = re.compile(r"^(?P<heading>#{1,6}\s+.+)$")

# Validates a strict clause ID token in isolation.
_STRICT_ID_RE = re.compile(r"^CL-\d{3}[A-Z]?$")


def _is_valid_clause_id(token: str) -> bool:
    """Return True if *token* is a valid strict clause ID."""
    return bool(_STRICT_ID_RE.match(token))


def extract_chunks_from_markdown(
    text: str,
    source_file: str,
) -> list[ClauseChunk]:
    """Extract clause chunks from a markdown policy document.

    Args:
        text: Raw markdown content.
        source_file: Filename (stem or relative path) used for traceability.

    Returns:
        List of ``ClauseChunk`` objects, one per clause.

    Raises:
        ValueError: If a line-start clause candidate has a malformed ID,
            or if duplicate clause IDs are found within the same source file.
    """
    lines = text.split("\n")
    chunks: list[ClauseChunk] = []
    current_section = ""
    seen_ids: set[str] = set()

    current_clause_id: str | None = None
    current_clause_section: str = ""
    current_lines: list[str] = []
    chunk_index = 0

    def _flush() -> None:
        nonlocal chunk_index
        if current_clause_id is not None:
            body = "\n".join(current_lines).strip()
            if body:
                chunks.append(
                    ClauseChunk(
                        chunk_id=f"{source_file}::{chunk_index}",
                        clause_id=current_clause_id,
                        source_file=source_file,
                        section=current_clause_section,
                        text=body,
                    )
                )
                chunk_index += 1

    for line in lines:
        # Track section headings.
        heading_m = HEADING_RE.match(line)
        if heading_m:
            current_section = heading_m.group("heading").strip()
            continue

        # Check for clause-start candidate (line-start CL-* token).
        candidate_m = CLAUSE_CANDIDATE_RE.match(line)
        if candidate_m:
            token = candidate_m.group("token")
            if not _is_valid_clause_id(token):
                raise ValueError(
                    f"Malformed clause ID at line start in {source_file}: "
                    f"{token!r}"
                )
            if token in seen_ids:
                raise ValueError(
                    f"Duplicate clause ID {token!r} in {source_file}"
                )
            seen_ids.add(token)
            _flush()
            current_clause_id = token
            current_clause_section = current_section
            current_lines = [line]
            continue

        # Accumulate body lines for the current clause.
        if current_clause_id is not None:
            current_lines.append(line)

    _flush()
    return chunks


def load_policy_chunks(policy_dir: Path) -> list[ClauseChunk]:
    """Load and chunk all ``*.md`` policy files in *policy_dir*.

    Args:
        policy_dir: Directory containing markdown policy files.

    Returns:
        Aggregated list of ``ClauseChunk`` across all files, sorted by
        (source_file, chunk_id) for deterministic ordering.

    Raises:
        ValueError: Propagated from :func:`extract_chunks_from_markdown`.
        FileNotFoundError: If *policy_dir* does not exist.
    """
    if not policy_dir.is_dir():
        raise FileNotFoundError(f"Policy directory not found: {policy_dir}")

    all_chunks: list[ClauseChunk] = []
    for md_path in sorted(policy_dir.glob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        file_chunks = extract_chunks_from_markdown(text, md_path.name)
        all_chunks.extend(file_chunks)

    return all_chunks
