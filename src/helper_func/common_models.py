from enum import Enum


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"

class ProductType(str, Enum):
    INTRADAY = "I"
    DELIVERY = "D"
    MTF = "MTF"

class Product(str, Enum):
    D = "D"       # Delivery
    I = "I"       # Intraday
    CO = "CO"     # Cover Order
    MTF = "MTF"   # Margin Trading Facility


class Validity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"  # Stop Loss Limit
    SL_M = "SL-M"  # Stop Loss Market

class Variety(str, Enum):
    SIMPLE = "SIMPLE"
    AMO = "AMO"
    CO = "CO"
    OCO = "OCO"

class OrderStatus(str, Enum):
    COMPLETE = "complete"
    OPEN = "open"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PENDING = "pending"
    TRIGGER_PENDING = "trigger pending"