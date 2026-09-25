"""create order and position tables

Revision ID: 6a8f5623ba5d
Revises: 1fd78598cb2d
Create Date: 2026-09-03 15:35:12.431167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "6a8f5623ba5d"
down_revision: Union[str, Sequence[str], None] = "1fd78598cb2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("trading_symbol", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("buy_order_id", sa.Integer(), nullable=False),
        sa.Column("sell_order_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("buy_price", sa.Float(), nullable=False),
        sa.Column("sell_price", sa.Float(), nullable=True),
        sa.Column("buy_timestamp", sa.DateTime(), nullable=False),
        sa.Column("sell_timestamp", sa.DateTime(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("pnl_percent", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["buy_order_id"], ["order_details.id"]),
        sa.ForeignKeyConstraint(["sell_order_id"], ["order_details.id"]),
    )
    op.create_index(
        op.f("ix_positions_trading_symbol"), "positions", ["trading_symbol"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_positions_trading_symbol"), table_name="positions")
    op.drop_table("positions")
