"""Add password fields to employees and create password_reset_requests table.

Revision ID: 003
Revises: 002
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add password columns to employees
    op.add_column("employees", sa.Column("password_hash", sa.String, nullable=True))
    op.add_column(
        "employees",
        sa.Column("must_reset_password", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )

    # Create password_reset_requests table
    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("resolved_by", sa.String, nullable=True),
        sa.Column("notes", sa.String, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("password_reset_requests")
    op.drop_column("employees", "must_reset_password")
    op.drop_column("employees", "password_hash")
