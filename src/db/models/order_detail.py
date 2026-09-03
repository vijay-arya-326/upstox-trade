from datetime import datetime

from sqlmodel import Field, SQLModel

# Persist / display as YYYY-MM-DD HH:mm:ss


class OrderDetail(SQLModel, table=True):
    __tablename__ = "order_details"

    id: int | None = Field(default=None, primary_key=True)
    order_id: str = Field(unique=True, index=True)
    placement_batch_id: str | None = None
    instrument_token: str
    exchange_type: str = Field(max_length=5)
    quantity: int
    filled_qty: int
    product: str
    validity: str
    price: float
    tag: str | None = None
    order_type: str
    transaction_type: str
    disclosed_quantity: int | None = None
    trigger_price: float
    is_amo: bool = False
    slice: bool = False
    market_protection: int | None = -1
    status: str | None = None
    created_at: datetime
    updated_at: datetime
    total_charges: float
