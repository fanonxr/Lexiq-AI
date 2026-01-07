"""add google auth fields to users table

Revision ID: g1h2i3j4k5l6
Revises: 079cc6bea3d5
Create Date: 2024-12-XX

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "079cc6bea3d5"  # Revises: add_webhook_subscription_fields (latest head)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Google OAuth fields to users table
    op.add_column(
        "users",
        sa.Column("google_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("google_email", sa.String(length=255), nullable=True),
    )
    
    # Create indexes
    # google_id is unique (for fast lookups and uniqueness constraint)
    op.create_index(op.f("ix_users_google_id"), "users", ["google_id"], unique=True)
    # google_email is not unique (user might have multiple Google accounts with different emails)
    op.create_index(op.f("ix_users_google_email"), "users", ["google_email"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_users_google_email"), table_name="users")
    op.drop_index(op.f("ix_users_google_id"), table_name="users")
    
    # Drop columns
    op.drop_column("users", "google_email")
    op.drop_column("users", "google_id")

