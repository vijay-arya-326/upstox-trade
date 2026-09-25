"""new column for exchange type in order details

Revision ID: 83c5d80031c3
Revises: 48fdb3b3fb7f
Create Date: 2026-09-01 15:53:40.266525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '83c5d80031c3'
down_revision: Union[str, Sequence[str], None] = '48fdb3b3fb7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("order_details",
          sa.Column("exchange_type", sa.String(length=5), nullable=False),)
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("order_details", "exchange_type")
    pass
