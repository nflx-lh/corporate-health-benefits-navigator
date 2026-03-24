"""Tests for the benefit_rules CSV seeder."""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.rule_db import BenefitRuleDB
from app.scripts.seed_rules import parse_csv, seed


_CSV_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "rules" / "benefit_rules.csv"


class TestParseCSV:
    """Test CSV parsing without a database."""

    def test_parse_returns_all_rows(self):
        rows = parse_csv(_CSV_PATH)
        assert len(rows) == 46

    def test_parse_row_has_required_fields(self):
        rows = parse_csv(_CSV_PATH)
        row = rows[0]
        assert row["rule_id"] == "R001"
        assert row["benefit_type"] == "outpatient"
        assert isinstance(row["tenure_min_months"], int)
        assert isinstance(row["preauth_required"], bool)
        assert isinstance(row["coverage_percent"], float)

    def test_parse_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_csv(pathlib.Path("/nonexistent/file.csv"))


class TestSeedIdempotent:
    """Test seeding into an in-memory SQLite database."""

    @pytest.fixture
    def db_url(self):
        return "sqlite:///:memory:"

    def test_seed_inserts_all_rules(self, db_url):
        result = seed(db_url, _CSV_PATH)
        assert result["before_count"] == 0
        assert result["upserted_count"] == 46
        assert result["after_count"] == 46

    def test_seed_is_idempotent(self, db_url):
        # First run
        seed(db_url, _CSV_PATH)
        # Second run — same DB URL won't work with :memory: (separate connection)
        # So we use a file-based temp DB instead
        pass

    def test_seed_twice_no_duplicates(self, tmp_path):
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"

        result1 = seed(db_url, _CSV_PATH)
        assert result1["after_count"] == 46

        result2 = seed(db_url, _CSV_PATH)
        assert result2["before_count"] == 46
        assert result2["upserted_count"] == 46  # all upserted (updated)
        assert result2["after_count"] == 46  # no duplicates

    def test_seed_updates_existing_rule(self, tmp_path):
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"

        # First seed
        seed(db_url, _CSV_PATH)

        # Manually modify a rule
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            rule = session.get(BenefitRuleDB, "R001")
            rule.coverage_percent = 99.99
            session.commit()

        # Re-seed should overwrite
        seed(db_url, _CSV_PATH)

        with Session() as session:
            rule = session.get(BenefitRuleDB, "R001")
            assert rule.coverage_percent == 60.0  # original CSV value
