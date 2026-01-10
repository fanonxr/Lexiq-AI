"""add stripe_customer_id to users table

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
Create Date: 2025-01-XX

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "j9k0l1m2n3o4"
down_revision: Union[str, None] = "i8j9k0l1m2n3"  # Revises: remove_unique_constraint_from_firm_name
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add stripe_customer_id field to users table
    op.add_column(
        "users",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
    )
    
    # Create unique index for stripe_customer_id
    # This ensures each Stripe customer ID is unique and allows fast lookups
    op.create_index(
        op.f("ix_users_stripe_customer_id"),
        "users",
        ["stripe_customer_id"],
        unique=True,
    )


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f("ix_users_stripe_customer_id"), table_name="users")
    
    # Drop column
    op.drop_column("users", "stripe_customer_id")
