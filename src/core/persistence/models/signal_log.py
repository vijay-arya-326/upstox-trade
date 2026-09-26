from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel
from core.utils.enums import TransactionType


class SignalLog(SQLModel, table=True):
    __tablename__ = "signal_logs"

    id: int | None = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    strategy_name: str = Field(index=True)
    action: str
    entry_price: float | None = None
    initial_sl: float | None = None
    signal_metadata: str | None = None
    created_at: datetime