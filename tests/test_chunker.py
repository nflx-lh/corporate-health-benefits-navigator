"""Tests for clause-aware markdown chunker."""

import pytest

from app.services.chunker import ClauseChunk, extract_chunks_from_markdown


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_MD = """\
# Section One

**CL-001:** First clause body text.

**CL-002:** Second clause body text.
"""

BULLET_PREFIX_MD = """\
## Bullet Section

- CL-010 Bullet dash clause.
* CL-011 Bullet asterisk clause.
+ CL-012 Bullet plus clause.
"""

SUFFIX_MD = """\
## Suffix Section

**CL-073A:** Clause with uppercase suffix letter.
"""

FULL_METADATA_MD = """\
# Main Heading

## Sub Heading

**CL-100:** Some important rule about benefits.
Additional detail on next line.
"""

MALFORMED_START_MD = """\
# Bad

**CL-12:** Only two digits.
"""

MALFORMED_BODY_MD = """\
# Good

**CL-001:** This clause mentions CL-9999 in the body, which is fine.
"""

DUPLICATE_MD = """\
# Dup

**CL-001:** First occurrence.

**CL-001:** Duplicate occurrence.
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBasicExtraction:
    """Test clause extraction from simple markdown."""

    def test_extracts_two_clauses(self) -> None:
        chunks = extract_chunks_from_markdown(SIMPLE_MD, "simple.md")
        assert len(chunks) == 2
        assert chunks[0].clause_id == "CL-001"
        assert chunks[1].clause_id == "CL-002"

    def test_clause_text_contains_body(self) -> None:
        chunks = extract_chunks_from_markdown(SIMPLE_MD, "simple.md")
        assert "First clause body text" in chunks[0].text


class TestBulletPrefixExtraction:
    """Test clause-start with bullet prefix (-, *, +)."""

    def test_dash_bullet(self) -> None:
        chunks = extract_chunks_from_markdown(BULLET_PREFIX_MD, "bullet.md")
        ids = [c.clause_id for c in chunks]
        assert "CL-010" in ids

    def test_asterisk_bullet(self) -> None:
        chunks = extract_chunks_from_markdown(BULLET_PREFIX_MD, "bullet.md")
        ids = [c.clause_id for c in chunks]
        assert "CL-011" in ids

    def test_plus_bullet(self) -> None:
        chunks = extract_chunks_from_markdown(BULLET_PREFIX_MD, "bullet.md")
        ids = [c.clause_id for c in chunks]
        assert "CL-012" in ids


class TestExactClauseIdPreservation:
    """Test that clause IDs are preserved exactly (e.g. CL-073A)."""

    def test_suffix_preserved(self) -> None:
        chunks = extract_chunks_from_markdown(SUFFIX_MD, "suffix.md")
        assert len(chunks) == 1
        assert chunks[0].clause_id == "CL-073A"


class TestMetadataCompleteness:
    """Test that each chunk carries all required metadata."""

    def test_all_fields_present(self) -> None:
        chunks = extract_chunks_from_markdown(FULL_METADATA_MD, "meta.md")
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.clause_id == "CL-100"
        assert chunk.source_file == "meta.md"
        assert "Sub Heading" in chunk.section
        assert "important rule" in chunk.text
        assert chunk.chunk_id == "meta.md::0"

    def test_multiline_body_preserved(self) -> None:
        chunks = extract_chunks_from_markdown(FULL_METADATA_MD, "meta.md")
        assert "Additional detail" in chunks[0].text


class TestMalformedClauseStart:
    """Test that malformed clause-start candidates raise ValueError."""

    def test_malformed_id_at_line_start_raises(self) -> None:
        with pytest.raises(ValueError, match="Malformed clause ID"):
            extract_chunks_from_markdown(MALFORMED_START_MD, "bad.md")

    def test_malformed_two_digit_raises(self) -> None:
        bad = "## X\n\n- CL-01 Two digits only.\n"
        with pytest.raises(ValueError, match="Malformed clause ID"):
            extract_chunks_from_markdown(bad, "bad2.md")

    def test_malformed_four_digit_raises(self) -> None:
        bad = "## X\n\n**CL-1234:** Four digits.\n"
        with pytest.raises(ValueError, match="Malformed clause ID"):
            extract_chunks_from_markdown(bad, "bad3.md")


class TestMalformedBodyToken:
    """Test that malformed CL-* tokens in body text do NOT raise."""

    def test_body_malformed_does_not_raise(self) -> None:
        chunks = extract_chunks_from_markdown(MALFORMED_BODY_MD, "ok.md")
        assert len(chunks) == 1
        assert "CL-9999" in chunks[0].text


class TestDuplicateClauseId:
    """Test that duplicate clause IDs within the same source file raise."""

    def test_duplicate_raises(self) -> None:
        with pytest.raises(ValueError, match="Duplicate clause ID"):
            extract_chunks_from_markdown(DUPLICATE_MD, "dup.md")
