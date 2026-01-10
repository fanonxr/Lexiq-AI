"""add composite index to usage_records for performance

Revision ID: l1m2n3o4p5q6
Revises: k0l1m2n3o4p5
Create Date: 2025-01-XX

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "l1m2n3o4p5q6"
down_revision: Union[str, None] = "k0l1m2n3o4p5"  # Revises: seed_subscription_plans
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add composite index on (user_id, feature, period_start) to usage_records table.
    
    This index improves query performance for the common query pattern:
    - Filter by user_id AND feature AND period_start
    - Used in get_by_user_and_feature() method in UsageRecordRepository
    
    The composite index is more efficient than individual indexes for this query pattern.
    """
    op.create_index(
        "ix_usage_records_user_feature_period",
        "usage_records",
        ["user_id", "feature", "period_start"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the composite index."""
    op.drop_index("ix_usage_records_user_feature_period", table_name="usage_records")
