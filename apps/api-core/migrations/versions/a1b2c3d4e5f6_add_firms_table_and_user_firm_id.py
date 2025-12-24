"""add firms table and user firm_id

Revision ID: a1b2c3d4e5f6
Revises: 8f7a6b5c4d3e
Create Date: 2025-12-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "8f7a6b5c4d3e"  # Revises notifications, before firm_personas
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create firms table first
    op.create_table(
        "firms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("default_model", sa.String(length=100), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("specialties", sa.Text(), nullable=True),
        sa.Column("qdrant_collection", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes for firms table
    op.create_index(op.f("ix_firms_id"), "firms", ["id"], unique=False)
    op.create_index(op.f("ix_firms_name"), "firms", ["name"], unique=True)
    op.create_index(op.f("ix_firms_domain"), "firms", ["domain"], unique=True)
    op.create_index(op.f("ix_firms_qdrant_collection"), "firms", ["qdrant_collection"], unique=True)
    
    # Add firm_id column to users table
    op.add_column(
        "users",
        sa.Column("firm_id", sa.String(length=36), nullable=True),
    )
    
    # Create index for firm_id
    op.create_index(op.f("ix_users_firm_id"), "users", ["firm_id"], unique=False)
    
    # Add foreign key constraint
    op.create_foreign_key(
        "fk_users_firm_id",
        "users",
        "firms",
        ["firm_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint("fk_users_firm_id", "users", type_="foreignkey")
    
    # Drop index
    op.drop_index(op.f("ix_users_firm_id"), table_name="users")
    
    # Drop column
    op.drop_column("users", "firm_id")
    
    # Drop firms table indexes
    op.drop_index(op.f("ix_firms_qdrant_collection"), table_name="firms")
    op.drop_index(op.f("ix_firms_domain"), table_name="firms")
    op.drop_index(op.f("ix_firms_name"), table_name="firms")
    op.drop_index(op.f("ix_firms_id"), table_name="firms")
    
    # Drop firms table
    op.drop_table("firms")

