import pandas as pd
import numpy as np
from collections import deque
from typing import Optional
from strategy.base import Strategy, Signal, TrailResult
from core.utils.enums import TransactionType
from core.persistence.models import Position, OrderDetail


class UTBotStrategy(Strategy):
    def __init__(
        self,
        atr_period: int = 10,
        key_value: float = 1.0,
        use_heikin_ashi: bool = False,
        history_length: int = 200,
    ):
        self.atr_period = atr_period
        self.key_value = key_value
        self.use_heikin_ashi = use_heikin_ashi
        self.history_length = history_length
        
        self._closes = deque(maxlen=history_length)
        self._highs = deque(maxlen=history_length)
        self._lows = deque(maxlen=history_length)
        self._opens = deque(maxlen=history_length)
        
        self._trailing_stop = 0.0
        self._prev_pos = 0
        self._prev_src = 0.0
        self._prev_stop = 0.0

    def _heikin_ashi(self, o, h, l, c):
        ha_close = (o + h + l + c) / 4
        ha_open = (self._prev_ha_open + self._prev_ha_close) / 2 if hasattr(self, '_prev_ha_open') else (o + c) / 2
        ha_high = max(h, ha_open, ha_close)
        ha_low = min(l, ha_open, ha_close)
        self._prev_ha_open = ha_open
        self._prev_ha_close = ha_close
        return ha_open, ha_high, ha_low, ha_close

    def _atr(self, high, low, close, prev_close):
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        if not hasattr(self, '_atr_values'):
            self._atr_values = deque(maxlen=self.atr_period)
        self._atr_values.append(tr)
        if len(self._atr_values) < self.atr_period:
            return np.nan
        alpha = 1 / self.atr_period
        atr_val = self._atr_values[0]
        for v in self._atr_values[1:]:
            atr_val = alpha * v + (1 - alpha) * atr_val
        return atr_val

    def on_tick(self, ltp: float, position: Position | None) -> Signal | TrailResult:
        self._closes.append(ltp)
        self._highs.append(ltp)
        self._lows.append(ltp)
        self._opens.append(ltp)
        
        if len(self._closes) < self.atr_period + 1:
            return Signal(action=None, entry_price=None, initial_sl=None, metadata={})
        
        o = self._opens[-1]
        h = self._highs[-1]
        l = self._lows[-1]
        c = self._closes[-1]
        
        if self.use_heikin_ashi:
            src_o, src_h, src_l, src_c = self._heikin_ashi(o, h, l, c)
            src = src_c
            atr_h, atr_l, atr_c = src_h, src_l, src_c
        else:
            src = c
            atr_h, atr_l, atr_c = h, l, c
        
        prev_close = self._closes[-2]
        xATR = self._atr(atr_h, atr_l, atr_c, prev_close)
        if np.isnan(xATR):
            return Signal(action=None, entry_price=None, initial_sl=None, metadata={})
        
        nLoss = self.key_value * xATR
        
        if self._prev_stop == 0:
            self._trailing_stop = src - nLoss if src > self._trailing_stop else src + nLoss
        else:
            prev_stop = self._trailing_stop
            prev_src = self._prev_src
            cur_src = src
            
            if cur_src > prev_stop and prev_src > prev_stop:
                self._trailing_stop = max(prev_stop, cur_src - nLoss)
            elif cur_src < prev_stop and prev_src < prev_stop:
                self._trailing_stop = min(prev_stop, cur_src + nLoss)
            else:
                if cur_src > prev_stop:
                    self._trailing_stop = cur_src - nLoss
                else:
                    self._trailing_stop = cur_src + nLoss
        
        self._prev_src = src
        self._prev_stop = self._trailing_stop
        
        pos = 0
        if self._prev_src < self._prev_stop and src > self._trailing_stop:
            pos = 1
        elif self._prev_src > self._prev_stop and src < self._trailing_stop:
            pos = -1
        else:
            pos = self._prev_pos
        
        ema = src
        above = (self._prev_src <= self._prev_stop) and (src > self._trailing_stop)
        below = (self._prev_stop <= self._prev_src) and (self._trailing_stop > src)
        
        buy_signal = (src > self._trailing_stop) and above
        sell_signal = (src < self._trailing_stop) and below
        
        metadata = {
            "trailing_stop": self._trailing_stop,
            "pos": pos,
            "src": src,
            "atr": xATR,
        }
        
        if position is None:
            if buy_signal:
                return Signal(
                    action=TransactionType.BUY,
                    entry_price=src,
                    initial_sl=self._trailing_stop,
                    metadata=metadata,
                )
            elif sell_signal:
                return Signal(
                    action=TransactionType.SELL,
                    entry_price=src,
                    initial_sl=self._trailing_stop,
                    metadata=metadata,
                )
            return Signal(action=None, entry_price=None, initial_sl=None, metadata=metadata)
        else:
            exit_signal = False
            is_long = position.qty_bought > 0
            
            if is_long and sell_signal:
                exit_signal = True
            elif not is_long and buy_signal:
                exit_signal = True
            
            new_sl = self._trailing_stop if (is_long and self._trailing_stop > position.trigger_price) or \
                                           (not is_long and self._trailing_stop < position.trigger_price) else None
            
            return TrailResult(new_sl=new_sl, exit_signal=exit_signal)

    def on_order_filled(self, order: OrderDetail, position: Position) -> None:
        self._trailing_stop = position.trigger_price
        self._prev_pos = 1 if position.qty_bought > 0 else -1