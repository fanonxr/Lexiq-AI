"""add notifications table

Revision ID: 8f7a6b5c4d3e
Revises: 5d3b9c1a2e4f
Create Date: 2025-12-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f7a6b5c4d3e"
down_revision: Union[str, None] = "5d3b9c1a2e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firm_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("to", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_firm_id"), "notifications", ["firm_id"], unique=False)
    op.create_index(
        op.f("ix_notifications_created_by_user_id"),
        "notifications",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_notifications_channel"), "notifications", ["channel"], unique=False)
    op.create_index(op.f("ix_notifications_status"), "notifications", ["status"], unique=False)
    op.create_index(
        op.f("ix_notifications_idempotency_key"), "notifications", ["idempotency_key"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_idempotency_key"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_status"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_channel"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_created_by_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_firm_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")


