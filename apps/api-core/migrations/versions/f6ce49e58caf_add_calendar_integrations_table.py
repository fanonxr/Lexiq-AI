"""add calendar integrations table

Revision ID: f6ce49e58caf
Revises: 3d14f2c29b60
Create Date: 2025-12-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6ce49e58caf"
down_revision: Union[str, None] = "3d14f2c29b60"  # Depends on appointments_calendar migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_integrations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("integration_type", sa.String(length=50), nullable=False),  # "outlook" or "google"
        sa.Column("access_token", sa.Text(), nullable=True),  # Encrypted
        sa.Column("refresh_token", sa.Text(), nullable=True),  # Encrypted
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calendar_id", sa.String(length=255), nullable=True),  # Outlook calendar ID
        sa.Column("email", sa.String(length=255), nullable=True),  # User's email for this calendar
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes
    op.create_index(op.f("ix_calendar_integrations_id"), "calendar_integrations", ["id"], unique=False)
    op.create_index(
        op.f("ix_calendar_integrations_user_id"),
        "calendar_integrations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calendar_integrations_type"),
        "calendar_integrations",
        ["integration_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_calendar_integrations_type"), table_name="calendar_integrations")
    op.drop_index(op.f("ix_calendar_integrations_user_id"), table_name="calendar_integrations")
    op.drop_index(op.f("ix_calendar_integrations_id"), table_name="calendar_integrations")
    op.drop_table("calendar_integrations")

