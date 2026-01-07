"""remove unique constraint from firm name

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2026-01-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i8j9k0l1m2n3"
down_revision: Union[str, None] = "h7i8j9k0l1m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the unique index on firms.name
    op.drop_index(op.f("ix_firms_name"), table_name="firms")
    
    # Recreate the index without the unique constraint
    op.create_index(op.f("ix_firms_name"), "firms", ["name"], unique=False)


def downgrade() -> None:
    # Drop the non-unique index
    op.drop_index(op.f("ix_firms_name"), table_name="firms")
    
    # Recreate the unique index
    op.create_index(op.f("ix_firms_name"), "firms", ["name"], unique=True)

