from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from core.utils.enums import TransactionType
from core.persistence.models import Position
from core.persistence.models import OrderDetail


@dataclass
class Signal:
    action: TransactionType | None
    entry_price: float | None
    initial_sl: float | None
    metadata: dict


@dataclass
class TrailResult:
    new_sl: float | None
    exit_signal: bool


class Strategy(ABC):
    @abstractmethod
    def on_tick(self, ltp: float, position: Position | None) -> Signal | TrailResult:
        """Called on every market tick. Returns entry signal or trail update."""
        pass

    @abstractmethod
    def on_order_filled(self, order: OrderDetail, position: Position) -> None:
        """Called when entry order fills - initialize trailing state."""
        pass