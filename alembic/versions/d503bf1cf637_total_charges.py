"""total charges

Revision ID: d503bf1cf637
Revises: 83c5d80031c3
Create Date: 2026-09-01 16:22:48.963583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd503bf1cf637'
down_revision: Union[str, Sequence[str], None] = '83c5d80031c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("order_details",
                  sa.Column("total_charges", sa.Float(), nullable=True))
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("order_details", "total_charges")
    pass
