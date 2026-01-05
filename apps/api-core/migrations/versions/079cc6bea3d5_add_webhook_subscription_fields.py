"""add webhook subscription fields to calendar integrations

Revision ID: 079cc6bea3d5
Revises: c1d2e3f4g5h6
Create Date: 2026-01-04

This migration adds webhook subscription tracking fields to the calendar_integrations table
to support real-time calendar event synchronization via Microsoft Graph webhooks.

Fields added:
- webhook_subscription_id: Microsoft Graph subscription ID
- webhook_subscription_expires_at: When the subscription expires (must be renewed before expiration)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "079cc6bea3d5"
down_revision: Union[str, None] = "c1d2e3f4g5h6"  # Revises: add_client_memory_tables
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add webhook subscription fields to calendar_integrations table."""
    
    # Add webhook_subscription_id column
    # Stores the Microsoft Graph subscription ID (e.g., "sub-abc-123-def-456")
    op.add_column(
        "calendar_integrations",
        sa.Column(
            "webhook_subscription_id",
            sa.String(length=255),
            nullable=True,
            comment="Microsoft Graph webhook subscription ID for real-time calendar event notifications",
        ),
    )
    
    # Add webhook_subscription_expires_at column
    # Stores when the subscription expires (must be renewed before expiration)
    # Microsoft Graph subscriptions expire after 3 days maximum
    op.add_column(
        "calendar_integrations",
        sa.Column(
            "webhook_subscription_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the webhook subscription expires. Must be renewed before expiration to maintain real-time sync.",
        ),
    )
    
    # Create index on webhook_subscription_id for faster lookups
    # Used when processing webhook notifications to find the integration
    op.create_index(
        op.f("ix_calendar_integrations_webhook_subscription_id"),
        "calendar_integrations",
        ["webhook_subscription_id"],
        unique=False,
    )
    
    # Create index on webhook_subscription_expires_at for renewal queries
    # Used by the scheduled task to find subscriptions expiring soon
    op.create_index(
        op.f("ix_calendar_integrations_webhook_subscription_expires_at"),
        "calendar_integrations",
        ["webhook_subscription_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove webhook subscription fields from calendar_integrations table."""
    
    # Drop indexes first
    op.drop_index(
        op.f("ix_calendar_integrations_webhook_subscription_expires_at"),
        table_name="calendar_integrations",
    )
    op.drop_index(
        op.f("ix_calendar_integrations_webhook_subscription_id"),
        table_name="calendar_integrations",
    )
    
    # Drop columns
    op.drop_column("calendar_integrations", "webhook_subscription_expires_at")
    op.drop_column("calendar_integrations", "webhook_subscription_id")

