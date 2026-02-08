"""add phone_number_pool table for Twilio number pool (return-to-pool on terminate)

Revision ID: n3o4p5q6r7s8
Revises: m2n3o4p5q6r7
Create Date: 2025-02-07

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "n3o4p5q6r7s8"
down_revision: Union[str, None] = "m2n3o4p5q6r7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "phone_number_pool",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("twilio_phone_number_sid", sa.String(length=100), nullable=False),
        sa.Column("pool_account_sid", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="available"),
        sa.Column("firm_id", sa.String(length=36), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_phone_number_pool_id"),
        "phone_number_pool",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_number_pool_phone_number"),
        "phone_number_pool",
        ["phone_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_phone_number_pool_twilio_phone_number_sid"),
        "phone_number_pool",
        ["twilio_phone_number_sid"],
        unique=True,
    )
    op.create_index(
        op.f("ix_phone_number_pool_pool_account_sid"),
        "phone_number_pool",
        ["pool_account_sid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_number_pool_status"),
        "phone_number_pool",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_number_pool_firm_id"),
        "phone_number_pool",
        ["firm_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_phone_number_pool_firm_id"), table_name="phone_number_pool")
    op.drop_index(op.f("ix_phone_number_pool_status"), table_name="phone_number_pool")
    op.drop_index(op.f("ix_phone_number_pool_pool_account_sid"), table_name="phone_number_pool")
    op.drop_index(op.f("ix_phone_number_pool_twilio_phone_number_sid"), table_name="phone_number_pool")
    op.drop_index(op.f("ix_phone_number_pool_phone_number"), table_name="phone_number_pool")
    op.drop_index(op.f("ix_phone_number_pool_id"), table_name="phone_number_pool")
    op.drop_table("phone_number_pool")
