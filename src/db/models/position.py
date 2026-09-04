from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, select

from db.helper.db_connector import orm_session
from helper_func.common_models import PositionStatus


class Position(SQLModel, table=True):
    """A closed (or partially closed) round-trip trade: one buy matched to one sell."""

    __tablename__ = "positions"

    id: Optional[int] = Field(
        default=None, primary_key=True, sa_column_kwargs={"autoincrement": True}
    )

    trading_symbol: str = Field(index=True)

    qty_bought: int= Field(default=0, description="Quantity of bought")
    qty_sold: int = Field(default=0, description="Quantity of sold")

    buy_order_id: int|None = Field(foreign_key="order_details.id", default=None)
    sell_order_id: Optional[int|None] = Field(default=None, foreign_key="order_details.id")

    buy_price: float
    sell_price: Optional[float] = None

    buy_timestamp: datetime
    sell_timestamp: Optional[datetime] = None

    status: PositionStatus = PositionStatus.OPEN

    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None

    @property
    def qty_remaining(self) -> int:
        return self.qty_bought - self.qty_sold

    def update_status(self):
        if self.qty_sold == 0:
            self.status = PositionStatus.OPEN
        elif self.qty_sold < self.qty_bought:
            self.status = PositionStatus.PARTIAL
        else:
            self.status = PositionStatus.CLOSED

    def calculate_pnl(self):
        """Realized P&L only on the sold quantity."""
        if self.sell_price is not None and self.qty_sold > 0:
            self.pnl = round((self.sell_price - self.buy_price) * self.qty_sold, 2)
            self.pnl_percent = round(
                ((self.sell_price - self.buy_price) / self.buy_price) * 100, 2
            )



def GetOpenOrderList():
    query = select(Position).where(Position.status != PositionStatus.CLOSED.value)
    with orm_session() as session:
        items = session.execute(query).scalars().all()

    if not items:
        return []

    return items