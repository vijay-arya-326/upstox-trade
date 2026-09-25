import numpy as np
import pandas as pd
from collections import deque
from typing import Optional
from strategy.base import Strategy, Signal, TrailResult
from core.utils.enums import TransactionType
from core.persistence.models import Position, OrderDetail


class QQEStrategy(Strategy):
    def __init__(
        self,
        rsi_len: int = 6,
        smooth_len: int = 5,
        factor: float = 3.0,
        rsi_len2: int = 6,
        smooth_len2: int = 5,
        factor2: float = 1.61,
        threshold: float = 3.0,
        history_length: int = 200,
    ):
        self.rsi_len = rsi_len
        self.smooth_len = smooth_len
        self.factor = factor
        self.rsi_len2 = rsi_len2
        self.smooth_len2 = smooth_len2
        self.factor2 = factor2
        self.threshold = threshold
        self.history_length = history_length
        
        self._closes = deque(maxlen=history_length)
        
        self._fast_rsi_ma = None
        self._slow_rsi_ma = None
        self._fast_line = 0.0
        self._slow_line = 0.0
        self._fast_hist = 0.0
        self._slow_hist = 0.0
        self._prev_fast_hist = 0.0
        self._prev_slow_hist = 0.0
        self._prev_upper = 0.0
        self._prev_lower = 0.0
        
        self._rsi_up = deque(maxlen=rsi_len)
        self._rsi_down = deque(maxlen=rsi_len)
        self._rsi_ma_fast = deque(maxlen=smooth_len)
        self._atr_rsi_fast = deque(maxlen=rsi_len * 2 - 1)
        self._ma_atr_rsi_fast = deque(maxlen=rsi_len * 2 - 1)
        self._dar_fast = deque(maxlen=rsi_len * 2 - 1)
        
        self._rsi_up2 = deque(maxlen=rsi_len2)
        self._rsi_down2 = deque(maxlen=rsi_len2)
        self._rsi_ma_slow = deque(maxlen=smooth_len2)
        self._atr_rsi_slow = deque(maxlen=rsi_len2 * 2 - 1)
        self._ma_atr_rsi_slow = deque(maxlen=rsi_len2 * 2 - 1)
        self._dar_slow = deque(maxlen=rsi_len2 * 2 - 1)
        
        self._longband_fast = 0.0
        self._shortband_fast = 0.0
        self._trend_fast = 0
        self._longband_slow = 0.0
        self._shortband_slow = 0.0
        self._trend_slow = 0

    def _update_rsi(self, close: float):
        if len(self._closes) < 2:
            return
        delta = close - self._closes[-2]
        up = max(delta, 0)
        down = max(-delta, 0)
        
        self._rsi_up.append(up)
        self._rsi_down.append(down)
        self._rsi_up2.append(up)
        self._rsi_down2.append(down)
        
        if len(self._rsi_up) >= self.rsi_len:
            alpha = 1 / self.rsi_len
            roll_up = self._rsi_up[0]
            for v in self._rsi_up[1:]:
                roll_up = alpha * v + (1 - alpha) * roll_up
            roll_down = self._rsi_down[0]
            for v in self._rsi_down[1:]:
                roll_down = alpha * v + (1 - alpha) * roll_down
            rs = roll_up / roll_down if roll_down != 0 else np.nan
            rsi = 100 - (100 / (1 + rs)) if not np.isnan(rs) else 50
            self._rsi_ma_fast.append(rsi)
        
        if len(self._rsi_up2) >= self.rsi_len2:
            alpha = 1 / self.rsi_len2
            roll_up = self._rsi_up2[0]
            for v in self._rsi_up2[1:]:
                roll_up = alpha * v + (1 - alpha) * roll_up
            roll_down = self._rsi_down2[0]
            for v in self._rsi_down2[1:]:
                roll_down = alpha * v + (1 - alpha) * roll_down
            rs = roll_up / roll_down if roll_down != 0 else np.nan
            rsi = 100 - (100 / (1 + rs)) if not np.isnan(rs) else 50
            self._rsi_ma_slow.append(rsi)

    def _update_qqe_fast(self):
        if len(self._rsi_ma_fast) < 2:
            return
        rsi_ma = list(self._rsi_ma_fast)
        atr_rsi = abs(rsi_ma[-1] - rsi_ma[-2])
        self._atr_rsi_fast.append(atr_rsi)
        
        if len(self._atr_rsi_fast) >= self.rsi_len * 2 - 1:
            alpha = 1 / (self.rsi_len * 2 - 1)
            ma_atr = self._atr_rsi_fast[0]
            for v in self._atr_rsi_fast[1:]:
                ma_atr = alpha * v + (1 - alpha) * ma_atr
            self._ma_atr_rsi_fast.append(ma_atr)
            
            if len(self._ma_atr_rsi_fast) >= self.rsi_len * 2 - 1:
                dar_ma = self._ma_atr_rsi_fast[0]
                for v in self._ma_atr_rsi_fast[1:]:
                    dar_ma = alpha * v + (1 - alpha) * dar_ma
                dar = dar_ma * self.factor
                self._dar_fast.append(dar)
                
                new_long = rsi_ma[-1] - dar
                new_short = rsi_ma[-1] + dar
                
                if rsi_ma[-2] > self._longband_fast and rsi_ma[-1] > self._longband_fast:
                    self._longband_fast = max(self._longband_fast, new_long)
                else:
                    self._longband_fast = new_long
                
                if rsi_ma[-2] < self._shortband_fast and rsi_ma[-1] < self._shortband_fast:
                    self._shortband_fast = min(self._shortband_fast, new_short)
                else:
                    self._shortband_fast = new_short
                
                if rsi_ma[-1] > self._shortband_fast:
                    self._trend_fast = 1
                elif rsi_ma[-1] < self._longband_fast:
                    self._trend_fast = -1
                
                self._fast_line = self._longband_fast if self._trend_fast == 1 else self._shortband_fast

    def _update_qqe_slow(self):
        if len(self._rsi_ma_slow) < 2:
            return
        rsi_ma = list(self._rsi_ma_slow)
        atr_rsi = abs(rsi_ma[-1] - rsi_ma[-2])
        self._atr_rsi_slow.append(atr_rsi)
        
        if len(self._atr_rsi_slow) >= self.rsi_len2 * 2 - 1:
            alpha = 1 / (self.rsi_len2 * 2 - 1)
            ma_atr = self._atr_rsi_slow[0]
            for v in self._atr_rsi_slow[1:]:
                ma_atr = alpha * v + (1 - alpha) * ma_atr
            self._ma_atr_rsi_slow.append(ma_atr)
            
            if len(self._ma_atr_rsi_slow) >= self.rsi_len2 * 2 - 1:
                dar_ma = self._ma_atr_rsi_slow[0]
                for v in self._ma_atr_rsi_slow[1:]:
                    dar_ma = alpha * v + (1 - alpha) * dar_ma
                dar = dar_ma * self.factor2
                self._dar_slow.append(dar)
                
                new_long = rsi_ma[-1] - dar
                new_short = rsi_ma[-1] + dar
                
                if rsi_ma[-2] > self._longband_slow and rsi_ma[-1] > self._longband_slow:
                    self._longband_slow = max(self._longband_slow, new_long)
                else:
                    self._longband_slow = new_long
                
                if rsi_ma[-2] < self._shortband_slow and rsi_ma[-1] < self._shortband_slow:
                    self._shortband_slow = min(self._shortband_slow, new_short)
                else:
                    self._shortband_slow = new_short
                
                if rsi_ma[-1] > self._shortband_slow:
                    self._trend_slow = 1
                elif rsi_ma[-1] < self._longband_slow:
                    self._trend_slow = -1
                
                self._slow_line = self._longband_slow if self._trend_slow == 1 else self._shortband_slow

    def on_tick(self, ltp: float, position: Position | None) -> Signal | TrailResult:
        self._closes.append(ltp)
        self._update_rsi(ltp)
        self._update_qqe_fast()
        self._update_qqe_slow()
        
        if len(self._closes) < max(self.rsi_len + self.smooth_len, self.rsi_len2 + self.smooth_len2) + 10:
            return Signal(action=None, entry_price=None, initial_sl=None, metadata={})
        
        self._prev_fast_hist = self._fast_hist
        self._prev_slow_hist = self._slow_hist
        self._fast_hist = self._fast_line - 50
        self._slow_hist = self._slow_line - 50
        upper = self._slow_hist + self.threshold
        lower = self._slow_hist - self.threshold
        
        long_cond = (self._fast_hist > upper) and (self._prev_fast_hist <= self._prev_upper)
        short_cond = (self._fast_hist < lower) and (self._prev_fast_hist >= self._prev_lower)
        
        self._prev_upper = upper
        self._prev_lower = lower
        
        metadata = {
            "fast_hist": self._fast_hist,
            "slow_hist": self._slow_hist,
            "upper": upper,
            "lower": lower,
            "fast_line": self._fast_line,
            "slow_line": self._slow_line,
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
            
            if is_long and short_cond:
                exit_signal = True
            elif not is_long and long_cond:
                exit_signal = True
            
            return TrailResult(new_sl=None, exit_signal=exit_signal)

    def on_order_filled(self, order: OrderDetail, position: Position) -> None:
        pass