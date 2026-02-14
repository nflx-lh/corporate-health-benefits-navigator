"""Create benefit_rules table.

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "benefit_rules",
        sa.Column("rule_id", sa.String, primary_key=True),
        sa.Column("benefit_type", sa.String, nullable=False),
        sa.Column("plan_tier", sa.String, nullable=False),
        sa.Column("employment_type", sa.String, nullable=False),
        sa.Column("tenure_min_months", sa.Integer, nullable=False),
        sa.Column("age_min", sa.Integer, nullable=False),
        sa.Column("age_max", sa.Integer, nullable=False),
        sa.Column("preauth_required", sa.Boolean, nullable=False),
        sa.Column("coverage_percent", sa.Float, nullable=False),
        sa.Column("annual_limit_sgd", sa.Float, nullable=False),
        sa.Column("co_pay_sgd", sa.Float, nullable=False),
        sa.Column("is_excluded", sa.Boolean, nullable=False),
        sa.Column("exclusion_reason", sa.Text, nullable=False, server_default=""),
        sa.Column("required_docs", sa.Text, nullable=False, server_default=""),
        sa.Column("effective_from", sa.String, nullable=False, server_default=""),
        sa.Column("effective_to", sa.String, nullable=False, server_default=""),
        sa.Column("service_category", sa.String, nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("benefit_rules")
