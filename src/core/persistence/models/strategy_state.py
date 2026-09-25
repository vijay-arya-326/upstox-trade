from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class StrategyState(SQLModel, table=True):
    __tablename__ = "strategy_state"

    id: int | None = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    strategy_name: str = Field(index=True, unique=True)
    state_json: str
    updated_at: datetime