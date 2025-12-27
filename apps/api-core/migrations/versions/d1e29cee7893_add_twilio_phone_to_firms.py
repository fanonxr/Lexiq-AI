"""add twilio phone number to firms

Revision ID: d1e29cee7893
Revises: a7b8c9d0e1f2
Create Date: 2025-12-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1e29cee7893"
down_revision: Union[str, None] = "a7b8c9d0e1f2"  # Depends on appointment_source_tracking migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add twilio_phone_number column
    op.add_column(
        "firms",
        sa.Column("twilio_phone_number", sa.String(length=20), nullable=True),
    )
    
    # Add twilio_phone_number_sid (Twilio Phone Number SID - required)
    op.add_column(
        "firms",
        sa.Column("twilio_phone_number_sid", sa.String(length=100), nullable=True),
    )
    
    # Add twilio_subaccount_sid (Twilio Subaccount SID - for billing/organization)
    op.add_column(
        "firms",
        sa.Column("twilio_subaccount_sid", sa.String(length=100), nullable=True),
    )
    
    # Create index on twilio_subaccount_sid (unique - one subaccount per firm)
    op.create_index(
        op.f("ix_firms_twilio_subaccount_sid"),
        "firms",
        ["twilio_subaccount_sid"],
        unique=True,
    )
    
    # Create unique index on twilio_phone_number (one number per firm)
    op.create_index(
        op.f("ix_firms_twilio_phone_number"),
        "firms",
        ["twilio_phone_number"],
        unique=True,
    )
    
    # Create unique index on twilio_phone_number_sid
    op.create_index(
        op.f("ix_firms_twilio_phone_number_sid"),
        "firms",
        ["twilio_phone_number_sid"],
        unique=True,
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f("ix_firms_twilio_phone_number_sid"), table_name="firms")
    op.drop_index(op.f("ix_firms_twilio_phone_number"), table_name="firms")
    op.drop_index(op.f("ix_firms_twilio_subaccount_sid"), table_name="firms")
    
    # Drop columns
    op.drop_column("firms", "twilio_subaccount_sid")
    op.drop_column("firms", "twilio_phone_number_sid")
    op.drop_column("firms", "twilio_phone_number")

