from datetime import datetime

from sqlmodel import Field, SQLModel

# Persist / display as YYYY-MM-DD HH:mm:ss


class Stock(SQLModel, table=True):
    __tablename__ = "stock_table"

    id: int | None = Field(default=None, primary_key=True)
    instrument_key: str = Field(unique=True, index=True)
    qty_purchased: int = 0
    avg_purchase_price: float | None = None
    buy_amount: float = 0.0  # total money spent buying
    purchase_order_id: str | None = None  # JSON array of buy order ids
    bought_on: datetime | None = None
    qty_sold: int = 0
    avg_selling_price: float | None = None
    sell_amount: float = 0.0  # total money from selling
    sell_order_id: str | None = None  # JSON array of sell order ids
    sold_on: datetime | None = None
    buy_charges: float = 0.0
    sell_charges: float = 0.0
    net_profit_before_tax: float | None = None
    tax: float | None = None
    profit_after_tax: float | None = None
    updated_at: datetime | None = None
