"""add appointment source tracking

Revision ID: a7b8c9d0e1f2
Revises: f6ce49e58caf
Create Date: 2025-12-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6ce49e58caf"  # Depends on calendar_integrations migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source tracking columns to appointments table
    op.add_column(
        "appointments",
        sa.Column("source_calendar_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("source_event_id", sa.String(length=255), nullable=True),
    )
    
    # Create foreign key constraint
    op.create_foreign_key(
        "fk_appointments_source_calendar_id",
        "appointments",
        "calendar_integrations",
        ["source_calendar_id"],
        ["id"],
        ondelete="SET NULL",
    )
    
    # Create index on source_calendar_id for faster lookups
    op.create_index(
        op.f("ix_appointments_source_calendar_id"),
        "appointments",
        ["source_calendar_id"],
        unique=False,
    )
    
    # Create index on source_event_id for idempotency checks
    op.create_index(
        op.f("ix_appointments_source_event_id"),
        "appointments",
        ["source_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_appointments_source_event_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_source_calendar_id"), table_name="appointments")
    op.drop_constraint("fk_appointments_source_calendar_id", "appointments", type_="foreignkey")
    op.drop_column("appointments", "source_event_id")
    op.drop_column("appointments", "source_calendar_id")

