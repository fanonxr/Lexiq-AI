"""add client memory tables for long-term memory

Revision ID: c1d2e3f4g5h6
Revises: d1e29cee7893
Create Date: 2026-01-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, None] = "d1e29cee7893"  # Latest: add_twilio_phone_to_firms
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Client and ClientMemory tables for Long-Term Memory feature."""
    
    # Create clients table
    op.create_table(
        "clients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firm_id", sa.String(length=36), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("external_crm_id", sa.String(length=100), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_called_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes for efficient lookups
    op.create_index("ix_clients_id", "clients", ["id"])
    op.create_index("ix_clients_firm_id", "clients", ["firm_id"])
    op.create_index("ix_clients_phone_number", "clients", ["phone_number"])
    op.create_index("ix_clients_email", "clients", ["email"])
    op.create_index("ix_clients_external_crm_id", "clients", ["external_crm_id"])
    op.create_index("ix_clients_firm_phone", "clients", ["firm_id", "phone_number"], unique=True)
    op.create_index("ix_clients_firm_email", "clients", ["firm_id", "email"], unique=False)  # Email optional, so not unique
    
    # Create client_memories table
    op.create_table(
        "client_memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("qdrant_point_id", sa.String(length=36), nullable=True),  # Reference to Qdrant vector
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes for efficient memory retrieval
    op.create_index("ix_client_memories_id", "client_memories", ["id"])
    op.create_index("ix_client_memories_client_id", "client_memories", ["client_id"])
    op.create_index("ix_client_memories_created_at", "client_memories", ["created_at"])
    op.create_index(
        "ix_client_memories_client_created",
        "client_memories",
        ["client_id", "created_at"],
    )


def downgrade() -> None:
    """Drop Client and ClientMemory tables."""
    
    # Drop indexes first
    op.drop_index("ix_client_memories_client_created", table_name="client_memories")
    op.drop_index("ix_client_memories_created_at", table_name="client_memories")
    op.drop_index("ix_client_memories_client_id", table_name="client_memories")
    op.drop_index("ix_client_memories_id", table_name="client_memories")
    
    op.drop_index("ix_clients_firm_email", table_name="clients")
    op.drop_index("ix_clients_firm_phone", table_name="clients")
    op.drop_index("ix_clients_external_crm_id", table_name="clients")
    op.drop_index("ix_clients_email", table_name="clients")
    op.drop_index("ix_clients_phone_number", table_name="clients")
    op.drop_index("ix_clients_firm_id", table_name="clients")
    op.drop_index("ix_clients_id", table_name="clients")
    
    # Drop tables
    op.drop_table("client_memories")
    op.drop_table("clients")

