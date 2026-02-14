"""Create employees table.

Revision ID: 001
Revises: None
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("employee_id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=True),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("employment_type", sa.String, nullable=True),
        sa.Column("plan_tier", sa.String, nullable=True),
        sa.Column("tenure_months", sa.Integer, nullable=True),
        sa.Column("dependents_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_table("employees")
