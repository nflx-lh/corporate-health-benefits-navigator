"""B-707 – Sensitive Logging Hygiene tests."""

from __future__ import annotations

import logging

from app.middleware.log_sanitizer import SensitiveDataFilter, sanitize


# ---------------------------------------------------------------------------
# Unit: sanitize function
# ---------------------------------------------------------------------------

class TestJwtTokenNotInLogs:
    def test_jwt_token_redacted(self):
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = sanitize(f"Auth token: {token}")
        assert "eyJ" not in result
        assert "[REDACTED_JWT]" in result

    def test_bearer_token_redacted(self):
        result = sanitize("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U")
        assert "eyJ" not in result


class TestPasswordNotInLogs:
    def test_password_redacted(self):
        result = sanitize('{"employee_id": "EMP001", "password": "supersecret123"}')
        assert "supersecret123" not in result
        assert "[REDACTED]" in result


class TestApiKeyNotInLogs:
    def test_sk_key_redacted(self):
        result = sanitize("Using key sk-1234567890abcdefghijklmnopqrs")
        assert "sk-1234567890" not in result
        assert "[REDACTED_API_KEY]" in result

    def test_api_key_env_pattern(self):
        result = sanitize("api_key=ABCDEF1234567890GHIJ")
        assert "ABCDEF1234567890GHIJ" not in result


# ---------------------------------------------------------------------------
# Integration: logging.Filter applied to records
# ---------------------------------------------------------------------------

class TestFilterApplied:
    def test_filter_scrubs_message(self):
        filt = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            args=None, exc_info=None,
        )
        filt.filter(record)
        assert "eyJ" not in record.msg
        assert "[REDACTED_JWT]" in record.msg

    def test_filter_scrubs_args(self):
        filt = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="User %s logged in with password %s",
            args=("EMP001", '{"password": "secret"}'),
            exc_info=None,
        )
        filt.filter(record)
        # Args should be scrubbed
        assert "secret" not in str(record.args)

    def test_safe_text_unchanged(self):
        filt = SensitiveDataFilter()
        original = "Employee EMP001 queried dental coverage"
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=original, args=None, exc_info=None,
        )
        filt.filter(record)
        assert record.msg == original
