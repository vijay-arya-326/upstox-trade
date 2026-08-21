import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------- Enums for constrained string fields ----------

class ProductType(str, Enum):
    INTRADAY = "I"
    DELIVERY = "D"
    MTF = "MTF"


class Validity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"  # Stop Loss Limit
    SL_M = "SL-M"  # Stop Loss Market


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


# ---------- Main Order model ----------

class OrderModel(BaseModel):
    quantity: int = Field(
        ...,
        gt=0,
        description=(
            "Quantity with which the order is to be placed. "
            "For commodity - number of lots. "
            "For other F&O and equities - number of units, in multiples of tick size."
        ),
    )
    product: ProductType = Field(
        ..., description="Signifies if the order is Intraday, Delivery, or MTF."
    )
    validity: Validity = Field(
        default=Validity.DAY, description="Order validity: DAY (default) or IOC."
    )
    price: float | int = Field(
        ..., ge=0, description="Price at which the order will be placed."
    )
    tag: Optional[str] = Field(
        default=None, max_length=20, description="Tag for a particular order."
    )
    instrument_token: str = Field(
        ..., description="Key of the instrument."
    )
    order_type: OrderType = Field(
        ..., description="Type of order: MARKET, LIMIT, SL, or SL-M."
    )
    transaction_type: TransactionType = Field(
        ..., description="Indicates whether it's a BUY or SELL order."
    )
    disclosed_quantity: int = Field(
        ..., ge=0, description="Quantity to be disclosed in the market depth."
    )
    trigger_price: float = Field(
        ..., ge=0, description="Trigger price to be set for stop loss orders."
    )
    is_amo: Optional[bool] = Field(
        default=False, description="Signifies if the order is an After Market Order."
    )
    slice: Optional[bool] = Field(
        default=False,
        description=(
            "When true, the order is auto-sliced into smaller parts based on the "
            "exchange freeze quantity for the instrument."
        ),
    )
    market_protection: Optional[int] = Field(
        default=-1,
        ge=-1,
        le=25,
        description=(
            "-1 = automatic market protection. 1-25 = custom protection percentage. "
            "0 = no market protection. Applicable only for MARKET / SL-M orders."
        ),
    )

    # --- Validators ---

    @field_validator("instrument_token")
    @classmethod
    def validate_instrument_token(cls, v: str) -> str:
            # Adjust this pattern to match the actual Field Pattern Appendix regex,
        # e.g. "NSE_EQ|INE848E01016" style keys.
        pattern = r"^[A-Za-z]+_[A-Za-z]+\|[A-Za-z0-9]+$"
        if not re.match(pattern, v):
            raise ValueError(
                "instrument_token must match the expected pattern, e.g. "
                "'NSE_EQ|INE848E01016'"
            )
        return v

    @model_validator(mode="after")
    def validate_price_and_trigger(self) -> "Order":
        # Price is required to be 0 for MARKET / SL-M orders by most broker APIs
        if self.order_type in (OrderType.MARKET, OrderType.SL_M) and self.price != 0:
            raise ValueError(
                f"price must be 0 for order_type '{self.order_type.value}'"
            )

        # LIMIT / SL orders require a positive price
        if self.order_type in (OrderType.LIMIT, OrderType.SL) and self.price <= 0:
            raise ValueError(
                f"price must be greater than 0 for order_type '{self.order_type.value}'"
            )

        # trigger_price required (> 0) for stop-loss order types
        if self.order_type in (OrderType.SL, OrderType.SL_M) and self.trigger_price <= 0:
            raise ValueError(
                f"trigger_price must be greater than 0 for order_type '{self.order_type.value}'"
            )

        # trigger_price should be 0 for non stop-loss orders
        if self.order_type in (OrderType.MARKET, OrderType.LIMIT) and self.trigger_price != 0:
            raise ValueError(
                f"trigger_price must be 0 for order_type '{self.order_type.value}'"
            )

        return self

    @model_validator(mode="after")
    def validate_market_protection(self) -> "Order":
        # market_protection only applies to MARKET and SL-M orders
        if (
                self.order_type not in (OrderType.MARKET, OrderType.SL_M)
                and self.market_protection not in (None, -1)
        ):
            raise ValueError(
                "market_protection is only applicable for MARKET or SL-M orders"
            )
        return self

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "quantity": 1,
                "product": "D",
                "validity": "DAY",
                "price": 0,
                "tag": "my-order-1",
                "instrument_token": "NSE_EQ|INE848E01016",
                "order_type": "MARKET",
                "transaction_type": "BUY",
                "disclosed_quantity": 0,
                "trigger_price": 0,
                "is_amo": False,
                "slice": False,
                "market_protection": -1,
            }
        }