"""seed subscription plans

Revision ID: k0l1m2n3o4p5
Revises: j9k0l1m2n3o4
Create Date: 2025-01-XX

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "k0l1m2n3o4p5"
down_revision: Union[str, None] = "j9k0l1m2n3o4"  # Revises: add_stripe_customer_id_to_users
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed initial subscription plans."""
    # Get connection
    connection = op.get_bind()
    
    # Plans to create
    plans = [
        {
            "name": "starter",
            "display_name": "Starter",
            "description": "Perfect for small law firms getting started",
            "price_monthly": "149.00",
            "currency": "USD",
            "is_active": True,
            "is_public": True,
            "features_json": '{"included_minutes": 500, "overage_rate_per_minute": 0.18}',
        },
        {
            "name": "professional",
            "display_name": "Professional",
            "description": "For growing law firms with higher call volumes",
            "price_monthly": "399.00",
            "currency": "USD",
            "is_active": True,
            "is_public": True,
            "features_json": '{"included_minutes": 2000, "overage_rate_per_minute": 0.15}',
        },
        {
            "name": "enterprise",
            "display_name": "Enterprise",
            "description": "For large firms with custom needs",
            "price_monthly": None,  # Custom pricing
            "currency": "USD",
            "is_active": True,
            "is_public": True,
            "features_json": '{"included_minutes": null, "overage_rate_per_minute": null}',
        },
    ]
    
    # Insert plans (idempotent - only insert if they don't exist)
    for plan in plans:
        # Check if plan already exists
        result = connection.execute(
            sa.text("SELECT id FROM plans WHERE name = :name"),
            {"name": plan["name"]}
        ).fetchone()
        
        if result is None:
            # Generate UUID for plan ID using PostgreSQL's gen_random_uuid()
            plan_id_result = connection.execute(
                sa.text("SELECT gen_random_uuid()::text")
            ).fetchone()
            plan_id = plan_id_result[0]
            
            # Build INSERT statement (handle NULL price_monthly for Enterprise)
            if plan["price_monthly"]:
                insert_stmt = sa.text("""
                    INSERT INTO plans (
                        id, name, display_name, description, price_monthly, currency,
                        features_json, is_active, is_public, created_at, updated_at
                    ) VALUES (
                        :id, :name, :display_name, :description, 
                        CAST(:price_monthly AS NUMERIC(10, 2)), :currency,
                        :features_json, :is_active, :is_public, NOW(), NOW()
                    )
                """)
                params = {
                    "id": plan_id,
                    "name": plan["name"],
                    "display_name": plan["display_name"],
                    "description": plan["description"],
                    "price_monthly": plan["price_monthly"],
                    "currency": plan["currency"],
                    "features_json": plan["features_json"],
                    "is_active": plan["is_active"],
                    "is_public": plan["is_public"],
                }
            else:
                insert_stmt = sa.text("""
                    INSERT INTO plans (
                        id, name, display_name, description, price_monthly, currency,
                        features_json, is_active, is_public, created_at, updated_at
                    ) VALUES (
                        :id, :name, :display_name, :description, 
                        NULL, :currency,
                        :features_json, :is_active, :is_public, NOW(), NOW()
                    )
                """)
                params = {
                    "id": plan_id,
                    "name": plan["name"],
                    "display_name": plan["display_name"],
                    "description": plan["description"],
                    "currency": plan["currency"],
                    "features_json": plan["features_json"],
                    "is_active": plan["is_active"],
                    "is_public": plan["is_public"],
                }
            
            # Insert plan
            connection.execute(insert_stmt, params)


def downgrade() -> None:
    """Remove seeded plans."""
    # Get connection
    connection = op.get_bind()
    
    # Delete plans by name
    plan_names = ["starter", "professional", "enterprise"]
    for plan_name in plan_names:
        connection.execute(
            sa.text("DELETE FROM plans WHERE name = :name"),
            {"name": plan_name}
        )
