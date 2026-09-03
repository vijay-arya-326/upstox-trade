from datetime import datetime

from sqlmodel import Field, SQLModel

# Persist / display as YYYY-MM-DD HH:mm:ss


class ApiLog(SQLModel, table=True):
    __tablename__ = "api_logs"

    id: int | None = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    method: str
    url: str
    headers: str | None = None
    payload: str | None = None
    response_status: int | None = None
    response: str | None = None
    created_at: datetime
