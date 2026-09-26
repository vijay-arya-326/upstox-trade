import numpy as np
import pandas as pd
from collections import deque
from typing import Optional
from strategy.base import Strategy, Signal, TrailResult
from core.utils.enums import TransactionType
from core.persistence.models import Position, OrderDetail


class HMAStrategy(Strategy):
    def __init__(
        self,
        hma_len: int = 55,
        slope_lookback: int = 2,
        require_slope: bool = True,
        history_length: int = 200,
    ):
        self.hma_len = hma_len
        self.slope_lookback = slope_lookback
        self.require_slope = require_slope
        self.history_length = history_length
        
        self._closes = deque(maxlen=history_length)
        self._hma_values = deque(maxlen=history_length)
        
        self._prev_hma = 0.0
        self._prev_close = 0.0

    def _wma(self, series: list, length: int) -> float:
        if len(series) < length:
            return np.nan
        weights = np.arange(1, length + 1)
        vals = np.array(series[-length:])
        return np.dot(vals, weights) / weights.sum()

    def _hma(self, close: float) -> float:
        half = max(int(self.hma_len / 2), 1)
        sqrt_len = max(int(np.sqrt(self.hma_len)), 1)
        
        wma_half = self._wma(list(self._closes), half)
        wma_full = self._wma(list(self._closes), self.hma_len)
        
        if np.isnan(wma_half) or np.isnan(wma_full):
            return np.nan
        
        raw = 2 * wma_half - wma_full
        return self._wma([raw] * sqrt_len, sqrt_len)

    def on_tick(self, ltp: float, position: Position | None) -> Signal | TrailResult:
        self._closes.append(ltp)
        hma_val = self._hma(ltp)
        
        if np.isnan(hma_val):
            return Signal(action=None, entry_price=None, initial_sl=None, metadata={})
        
        self._hma_values.append(hma_val)
        self._prev_close = self._closes[-2] if len(self._closes) > 1 else ltp
        self._prev_hma = self._hma_values[-2] if len(self._hma_values) > 1 else hma_val
        
        hma_up = hma_val > self._prev_hma
        hma_down = hma_val < self._prev_hma
        
        cross_up = (ltp > hma_val) and (self._prev_close <= self._prev_hma)
        cross_down = (ltp < hma_val) and (self._prev_close >= self._prev_hma)
        
        long_cond = cross_up and (hma_up if self.require_slope else True)
        short_cond = cross_down and (hma_down if self.require_slope else True)
        
        metadata = {
            "hma": hma_val,
            "close": ltp,
            "hma_up": hma_up,
            "hma_down": hma_down,
        }
        
        if position is None:
            if long_cond:
                return Signal(
                    action=TransactionType.BUY,
                    entry_price=ltp,
                    initial_sl=ltp * 0.98,
                    metadata=metadata,
                )
            elif short_cond:
                return Signal(
                    action=TransactionType.SELL,
                    entry_price=ltp,
                    initial_sl=ltp * 1.02,
                    metadata=metadata,
                )
            return Signal(action=None, entry_price=None, initial_sl=None, metadata=metadata)
        else:
            exit_signal = False
            is_long = position.qty_bought > 0
            
            if is_long and cross_down:
                exit_signal = True
            elif not is_long and cross_up:
                exit_signal = True
            
            return TrailResult(new_sl=None, exit_signal=exit_signal)

    def on_order_filled(self, order: OrderDetail, position: Position) -> None:
        pass