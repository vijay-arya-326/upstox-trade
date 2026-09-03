from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel
from helper_func.common_models import PositionStatus

class Position(SQLModel, table=True):
    __tablename__ =  "positions"
    """A closed (or partially closed) round-trip trade: one buy matched to one sell."""
    id: Optional[int] = Field(default=None, primary_key=True)

    trading_symbol: str = Field(index=True)

    buy_order_id: int = Field(foreign_key="order.id")
    sell_order_id: Optional[int] = Field(default=None, foreign_key="order.id")

    quantity: int                      # matched quantity for this pair
    buy_price: float
    sell_price: Optional[float] = None

    buy_timestamp: datetime
    sell_timestamp: Optional[datetime] = None

    status: PositionStatus = PositionStatus.OPEN

    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None

    def calculate_pnl(self):
        if self.sell_price is not None:
            self.pnl = round((self.sell_price - self.buy_price) * self.quantity, 2)
            self.pnl_percent = round(
                ((self.sell_price - self.buy_price) / self.buy_price) * 100, 2
            )