"""add minutes tracking fields to plans table

Revision ID: m2n3o4p5q6r7
Revises: l1m2n3o4p5q6
Create Date: 2025-01-XX

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "m2n3o4p5q6r7"
down_revision: Union[str, None] = "l1m2n3o4p5q6"  # Revises: add_usage_record_composite_index
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add included_minutes and overage_rate_per_minute columns to plans table.
    
    These fields provide a cleaner data structure than storing in features_json.
    The data will be migrated from features_json for existing plans.
    """
    # Add included_minutes column (nullable, can be None for unlimited plans)
    op.add_column(
        "plans",
        sa.Column("included_minutes", sa.Integer(), nullable=True),
    )
    
    # Add overage_rate_per_minute column (nullable, can be None for unlimited plans)
    op.add_column(
        "plans",
        sa.Column("overage_rate_per_minute", sa.Numeric(10, 4), nullable=True),
    )
    
    # Migrate data from features_json to new columns for existing plans
    # This is a data migration step
    connection = op.get_bind()
    
    # Get all plans with features_json
    result = connection.execute(
        sa.text("SELECT id, features_json FROM plans WHERE features_json IS NOT NULL")
    )
    plans = result.fetchall()
    
    for plan_id, features_json in plans:
        if features_json:
            import json
            try:
                features = json.loads(features_json) if isinstance(features_json, str) else features_json
                included_minutes = features.get("included_minutes")
                overage_rate_per_minute = features.get("overage_rate_per_minute")
                
                # Update the plan with migrated data
                connection.execute(
                    sa.text("""
                        UPDATE plans 
                        SET included_minutes = :included_minutes,
                            overage_rate_per_minute = :overage_rate_per_minute
                        WHERE id = :plan_id
                    """),
                    {
                        "plan_id": plan_id,
                        "included_minutes": included_minutes,
                        "overage_rate_per_minute": str(overage_rate_per_minute) if overage_rate_per_minute is not None else None,
                    }
                )
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                # If JSON parsing fails, leave columns as NULL
                # This is safe - the application can still use features_json
                pass


def downgrade() -> None:
    """Drop the minutes tracking columns."""
    op.drop_column("plans", "overage_rate_per_minute")
    op.drop_column("plans", "included_minutes")
