"""add account lockout fields to users table

Revision ID: h7i8j9k0l1m2
Revises: g1h2i3j4k5l6
Create Date: 2025-01-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h7i8j9k0l1m2"
down_revision: Union[str, None] = "g1h2i3j4k5l6"  # Revises: add_google_auth_fields
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add account lockout fields to users table
    op.add_column(
        "users",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Drop columns
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")

