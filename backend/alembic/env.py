"""Alembic env — reads DATABASE_URL from environment."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make backend/app importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import Base  # noqa: E402

# Import all models so Base.metadata has them registered.
from app.models.employee_db import EmployeeDB  # noqa: E402, F401
from app.models.rule_db import BenefitRuleDB  # noqa: E402, F401

config = context.config
config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL", ""))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
