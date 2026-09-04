"""position_table_update

Revision ID: b65e174e4e3b
Revises: 6a8f5623ba5d
Create Date: 2026-09-04 15:42:57.023646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b65e174e4e3b'
down_revision: Union[str, Sequence[str], None] = '6a8f5623ba5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

table_name = "positions"

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(table_name, sa.Column("qty_bought", sa.Integer(), nullable=True, default=0))
    op.add_column(table_name, sa.Column("qty_sold", sa.Integer(), nullable=True, default=0))
    op.drop_column(table_name, "quantity")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(table_name, "qty_bought")
    op.drop_column(table_name, "qty_sold")
    op.add_column(table_name, sa.Column("quantity", sa.Integer(), nullable=False, default=0))

