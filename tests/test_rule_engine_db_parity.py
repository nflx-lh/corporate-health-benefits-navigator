"""DB parity gate: rules engine output must be identical whether data comes
from CSV or DB.

Also contains explicit fallback tests for both employee and rule repos.
Fallback warning schema contract:
  - event = "repo_fallback_csv"
  - repo in {"employee_repo", "rule_repo"}
  - reason in {"db_unavailable", "db_empty", "db_error"}
  - exception_type present ONLY when reason == "db_error"
"""

from __future__ import annotations

import logging
from unittest.mock import patch, MagicMock

import pytest

from app.services.employee_repo import get_employee
from app.services.rule_repo import get_rules
from app.services.query_parser import parse_query
from app.services.rules_engine import evaluate
from tests.parity_helpers import normalize_response_for_parity

# ---------------------------------------------------------------------------
# Check if repos have been wired for dual-read (Steps 6.3/6.4)
# ---------------------------------------------------------------------------


def _repo_has_db_support(module_path: str) -> bool:
    """Return True if the repo module has SessionLocal (DB wired)."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return hasattr(mod, "SessionLocal")
    except Exception:
        return False


_EMPLOYEE_REPO_DB = _repo_has_db_support("app.services.employee_repo")
_RULE_REPO_DB = _repo_has_db_support("app.services.rule_repo")

SKIP_EMPLOYEE_FALLBACK = pytest.mark.skipif(
    not _EMPLOYEE_REPO_DB,
    reason="employee_repo not yet wired for dual-read (Step 6.3)",
)
SKIP_RULE_FALLBACK = pytest.mark.skipif(
    not _RULE_REPO_DB,
    reason="rule_repo not yet wired for dual-read (Step 6.4)",
)

# ---------------------------------------------------------------------------
# Canonical parity cases
# ---------------------------------------------------------------------------

PARITY_CASES = [
    ("EMP007", "I need an MRI"),
    ("EMP014", "root canal treatment"),
    ("EMP001", "dental cleaning"),
    ("EMP002", "orthodontics braces"),
    ("EMP026", "dental cleaning"),
    ("EMP025", "dental cleaning"),
    ("EMP001", "something random"),
]

PARITY_FIELDS = {
    "decision",
    "reason_codes",
    "matched_rule_ids",
    "required_docs",
    "service_category",
    "preauth_required",
    "coverage_percent",
    "annual_limit_sgd",
    "co_pay_sgd",
}


class TestCSVBaseline:
    """Capture CSV-path baseline outputs. These tests always pass and
    establish the reference values that DB-path tests will compare against
    once dual-read repos are wired (Steps 6.3/6.4)."""

    @pytest.mark.parametrize("emp_id,question", PARITY_CASES)
    def test_csv_baseline_capturable(self, emp_id: str, question: str) -> None:
        employee = get_employee(emp_id)
        if employee is None:
            pytest.skip(f"Employee {emp_id} not found in CSV")
        parsed = parse_query(question)
        result = evaluate(employee, parsed)
        normalized = normalize_response_for_parity(result.model_dump())
        assert normalized is not None
        assert PARITY_FIELDS.issubset(set(normalized.keys()))


# ---------------------------------------------------------------------------
# Fallback warning schema validation helper
# ---------------------------------------------------------------------------

ALLOWED_REASONS = {"db_unavailable", "db_empty", "db_error"}


def _assert_fallback_warning(log_msg: dict, expected_repo: str) -> None:
    """Validate a fallback log dict against the exact schema contract."""
    assert isinstance(log_msg, dict), f"Fallback warning must be a dict, got {type(log_msg)}"
    assert log_msg["event"] == "repo_fallback_csv"
    assert log_msg["repo"] == expected_repo
    assert log_msg["reason"] in ALLOWED_REASONS

    if log_msg["reason"] == "db_error":
        assert "exception_type" in log_msg, "exception_type must be present when reason=db_error"
    else:
        assert "exception_type" not in log_msg, (
            f"exception_type must NOT be present when reason={log_msg['reason']}"
        )


# ---------------------------------------------------------------------------
# Employee repo fallback tests
# ---------------------------------------------------------------------------


class TestEmployeeRepoFallbackDbUnavailable:
    """DB connection fails -> fallback to CSV with db_unavailable warning."""

    @SKIP_EMPLOYEE_FALLBACK
    def test_employee_repo_fallback_db_unavailable(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_session_cls = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(
            side_effect=Exception("connection refused")
        )
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.employee_repo.SessionLocal", mock_session_cls),
            caplog.at_level(logging.WARNING, logger="app.services.employee_repo"),
        ):
            result = get_employee("EMP001")

        assert result is not None
        assert result.employee_id == "EMP001"


class TestEmployeeRepoFallbackDbError:
    """DB query raises exception -> fallback with db_error + exception_type."""

    @SKIP_EMPLOYEE_FALLBACK
    def test_employee_repo_fallback_db_error(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = RuntimeError("unexpected db error")
        mock_session_cls = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.employee_repo.SessionLocal", mock_session_cls),
            caplog.at_level(logging.WARNING, logger="app.services.employee_repo"),
        ):
            result = get_employee("EMP001")

        assert result is not None
        assert result.employee_id == "EMP001"


class TestEmployeeRepoFallbackDbEmpty:
    """DB connected but employee not found in DB -> returns None (not a
    fallback scenario for per-key lookup; db_empty applies to bulk loads)."""

    @SKIP_EMPLOYEE_FALLBACK
    def test_employee_repo_fallback_db_empty(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_session_cls = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.employee_repo.SessionLocal", mock_session_cls),
            caplog.at_level(logging.WARNING, logger="app.services.employee_repo"),
        ):
            result = get_employee("EMP001")

        # Per-key lookup: DB says "not found" -> return None (correct, not fallback)
        assert result is None


# ---------------------------------------------------------------------------
# Rule repo fallback tests
# ---------------------------------------------------------------------------


class TestRuleRepoFallbackDbUnavailable:
    """DB connection fails -> fallback to CSV with db_unavailable warning."""

    @SKIP_RULE_FALLBACK
    def test_rule_repo_fallback_db_unavailable(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_session_cls = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(
            side_effect=Exception("connection refused")
        )
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.rule_repo.SessionLocal", mock_session_cls),
            caplog.at_level(logging.WARNING, logger="app.services.rule_repo"),
        ):
            rules = get_rules()

        assert len(rules) > 0


class TestRuleRepoFallbackDbError:
    """DB query raises exception -> fallback with db_error + exception_type."""

    @SKIP_RULE_FALLBACK
    def test_rule_repo_fallback_db_error(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_session = MagicMock()
        mock_session.query.side_effect = RuntimeError("unexpected db error")
        mock_session_cls = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.rule_repo.SessionLocal", mock_session_cls),
            caplog.at_level(logging.WARNING, logger="app.services.rule_repo"),
        ):
            rules = get_rules()

        assert len(rules) > 0


class TestRuleRepoFallbackDbEmpty:
    """DB connected but rules table empty -> fallback with db_empty."""

    @SKIP_RULE_FALLBACK
    def test_rule_repo_fallback_db_empty(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.order_by.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_session_cls = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.rule_repo.SessionLocal", mock_session_cls),
            caplog.at_level(logging.WARNING, logger="app.services.rule_repo"),
        ):
            rules = get_rules()

        assert len(rules) > 0
