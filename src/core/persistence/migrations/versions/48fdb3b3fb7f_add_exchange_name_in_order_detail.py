"""add exchange name in order detail

Revision ID: 48fdb3b3fb7f
Revises:
Create Date: 2026-09-01 15:52:48.687467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "48fdb3b3fb7f"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "api_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("method", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("headers", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("payload", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "order_details",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("order_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("placement_batch_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("instrument_token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("product", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("validity", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("tag", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("order_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("transaction_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("disclosed_quantity", sa.Integer(), nullable=True),
        sa.Column("trigger_price", sa.Float(), nullable=False),
        sa.Column("is_amo", sa.Boolean(), nullable=False),
        sa.Column("slice", sa.Boolean(), nullable=False),
        sa.Column("market_protection", sa.Integer(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        op.f("ix_order_details_order_id"), "order_details", ["order_id"], unique=True
    )

    op.create_table(
        "stock_table",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("instrument_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("qty_purchased", sa.Integer(), nullable=False),
        sa.Column("avg_purchase_price", sa.Float(), nullable=True),
        sa.Column("buy_amount", sa.Float(), nullable=False),
        sa.Column("purchase_order_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("bought_on", sa.DateTime(), nullable=True),
        sa.Column("qty_sold", sa.Integer(), nullable=False),
        sa.Column("avg_selling_price", sa.Float(), nullable=True),
        sa.Column("sell_amount", sa.Float(), nullable=False),
        sa.Column("sell_order_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("sold_on", sa.DateTime(), nullable=True),
        sa.Column("buy_charges", sa.Float(), nullable=False),
        sa.Column("sell_charges", sa.Float(), nullable=False),
        sa.Column("net_profit_before_tax", sa.Float(), nullable=True),
        sa.Column("tax", sa.Float(), nullable=True),
        sa.Column("profit_after_tax", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_stock_table_instrument_key"),
        "stock_table",
        ["instrument_key"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_stock_table_instrument_key"), table_name="stock_table")
    op.drop_table("stock_table")
    op.drop_index(op.f("ix_order_details_order_id"), table_name="order_details")
    op.drop_table("order_details")
    op.drop_table("api_logs")
