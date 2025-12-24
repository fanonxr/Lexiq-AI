"""add agent configs table

Revision ID: e5f6a7b8c9d0
Revises: 2411b62ce18c
Create Date: 2025-12-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "2411b62ce18c"  # Depends on firms migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("firm_id", sa.String(length=36), nullable=True),
        sa.Column("voice_id", sa.String(length=100), nullable=False, server_default="1"),
        sa.Column("greeting_script", sa.Text(), nullable=False, server_default="Hello, thank you for calling. How can I assist you today?"),
        sa.Column("closing_script", sa.Text(), nullable=False, server_default="Thank you for calling. Have a great day!"),
        sa.Column("transfer_script", sa.Text(), nullable=False, server_default="Let me transfer you to someone who can better assist you."),
        sa.Column("auto_respond", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("record_calls", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("auto_transcribe", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("enable_voicemail", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes
    op.create_index(op.f("ix_agent_configs_id"), "agent_configs", ["id"], unique=False)
    op.create_index(op.f("ix_agent_configs_user_id"), "agent_configs", ["user_id"], unique=False)
    op.create_index(op.f("ix_agent_configs_firm_id"), "agent_configs", ["firm_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_configs_firm_id"), table_name="agent_configs")
    op.drop_index(op.f("ix_agent_configs_user_id"), table_name="agent_configs")
    op.drop_index(op.f("ix_agent_configs_id"), table_name="agent_configs")
    op.drop_table("agent_configs")

