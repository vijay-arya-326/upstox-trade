import numpy as np
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
        
        # RSI EMA state (incremental)
        self._rsi_ema_fast = None
        self._rsi_ema_slow = None
        
        # RSI MA EMA state
        self._rsi_ma_ema_fast = None
        self._rsi_ma_ema_slow = None
        
        # ATR of RSI EMA state
        self._atr_rsi_ema_fast = None
        self._atr_rsi_ema_slow = None
        
        # MA of ATR RSI EMA state
        self._ma_atr_rsi_ema_fast = None
        self._ma_atr_rsi_ema_slow = None
        
        # DAR EMA state
        self._dar_ema_fast = None
        self._dar_ema_slow = None
        
        self._fast_line = 0.0
        self._slow_line = 0.0
        self._fast_hist = 0.0
        self._slow_hist = 0.0
        self._prev_fast_hist = 0.0
        self._prev_slow_hist = 0.0
        self._prev_upper = 0.0
        self._prev_lower = 0.0
        
        self._longband_fast = 0.0
        self._shortband_fast = 0.0
        self._trend_fast = 0
        self._longband_slow = 0.0
        self._shortband_slow = 0.0
        self._trend_slow = 0
        
        # Warmup counters
        self._rsi_count = 0
        self._rsi_ma_count = 0
        self._atr_rsi_count = 0
        self._ma_atr_rsi_count = 0
        self._dar_count = 0

    def _update_rsi(self, close: float):
        if len(self._closes) < 2:
            return
        delta = close - self._closes[-2]
        up = max(delta, 0)
        down = max(-delta, 0)
        
        # Update RSI EMA incrementally
        alpha_rsi = 1 / self.rsi_len
        if self._rsi_ema_fast is None:
            self._rsi_ema_fast = up / (up + down) * 100 if (up + down) > 0 else 50
        else:
            rs = up / down if down > 0 else 1e10
            rsi = 100 - (100 / (1 + rs))
            self._rsi_ema_fast = alpha_rsi * rsi + (1 - alpha_rsi) * self._rsi_ema_fast
        
        alpha_rsi2 = 1 / self.rsi_len2
        if self._rsi_ema_slow is None:
            self._rsi_ema_slow = up / (up + down) * 100 if (up + down) > 0 else 50
        else:
            rs = up / down if down > 0 else 1e10
            rsi = 100 - (100 / (1 + rs))
            self._rsi_ema_slow = alpha_rsi2 * rsi + (1 - alpha_rsi2) * self._rsi_ema_slow
        
        self._rsi_count += 1
        
        # Update RSI MA EMA
        if self._rsi_count >= self.rsi_len:
            alpha_ma = 1 / self.smooth_len
            if self._rsi_ma_ema_fast is None:
                self._rsi_ma_ema_fast = self._rsi_ema_fast
            else:
                self._rsi_ma_ema_fast = alpha_ma * self._rsi_ema_fast + (1 - alpha_ma) * self._rsi_ma_ema_fast
            
            alpha_ma2 = 1 / self.smooth_len2
            if self._rsi_ma_ema_slow is None:
                self._rsi_ma_ema_slow = self._rsi_ema_slow
            else:
                self._rsi_ma_ema_slow = alpha_ma2 * self._rsi_ema_slow + (1 - alpha_ma2) * self._rsi_ma_ema_slow
            
            self._rsi_ma_count += 1

        # Update ATR of RSI
        if self._rsi_ma_ema_fast is not None and self._rsi_ma_ema_fast_prev is not None:
            atr_rsi = abs(self._rsi_ma_ema_fast - self._rsi_ma_ema_fast_prev)
            alpha_atr = 1 / (self.rsi_len * 2 - 1)
            if self._atr_rsi_ema_fast is None:
                self._atr_rsi_ema_fast = atr_rsi
            else:
                self._atr_rsi_ema_fast = alpha_atr * atr_rsi + (1 - alpha_atr) * self._atr_rsi_ema_fast
            
            if self._atr_rsi_ema_fast is not None:
                alpha_ma_atr = 1 / (self.rsi_len * 2 - 1)
                if self._ma_atr_rsi_ema_fast is None:
                    self._ma_atr_rsi_ema_fast = self._atr_rsi_ema_fast
                else:
                    self._ma_atr_rsi_ema_fast = alpha_ma_atr * self._atr_rsi_ema_fast + (1 - alpha_ma_atr) * self._ma_atr_rsi_ema_fast
                
                if self._ma_atr_rsi_ema_fast is not None:
                    if self._dar_ema_fast is None:
                        self._dar_ema_fast = self._ma_atr_rsi_ema_fast
                    else:
                        self._dar_ema_fast = alpha_ma_atr * self._ma_atr_rsi_ema_fast + (1 - alpha_ma_atr) * self._dar_ema_fast
                    
                    dar = self._dar_ema_fast * self.factor
                    self._update_bands_fast(dar)
        
        if self._rsi_ma_ema_slow is not None and self._rsi_ma_ema_slow_prev is not None:
            atr_rsi = abs(self._rsi_ma_ema_slow - self._rsi_ma_ema_slow_prev)
            alpha_atr = 1 / (self.rsi_len2 * 2 - 1)
            if self._atr_rsi_ema_slow is None:
                self._atr_rsi_ema_slow = atr_rsi
            else:
                self._atr_rsi_ema_slow = alpha_atr * atr_rsi + (1 - alpha_atr) * self._atr_rsi_ema_slow
            
            if self._atr_rsi_ema_slow is not None:
                alpha_ma_atr = 1 / (self.rsi_len2 * 2 - 1)
                if self._ma_atr_rsi_ema_slow is None:
                    self._ma_atr_rsi_ema_slow = self._atr_rsi_ema_slow
                else:
                    self._ma_atr_rsi_ema_slow = alpha_ma_atr * self._atr_rsi_ema_slow + (1 - alpha_ma_atr) * self._ma_atr_rsi_ema_slow
                
                if self._ma_atr_rsi_ema_slow is not None:
                    if self._dar_ema_slow is None:
                        self._dar_ema_slow = self._ma_atr_rsi_ema_slow
                    else:
                        self._dar_ema_slow = alpha_ma_atr * self._ma_atr_rsi_ema_slow + (1 - alpha_ma_atr) * self._dar_ema_slow
                    
                    dar = self._dar_ema_slow * self.factor2
                    self._update_bands_slow(dar)
        
        # Store previous values
        self._rsi_ma_ema_fast_prev = self._rsi_ma_ema_fast
        self._rsi_ma_ema_slow_prev = self._rsi_ma_ema_slow

    def _update_bands_fast(self, dar: float):
        if self._rsi_ma_ema_fast is None:
            return
        
        new_long = self._rsi_ma_ema_fast - dar
        new_short = self._rsi_ma_ema_fast + dar
        
        if self._rsi_ma_ema_fast > self._longband_fast and self._rsi_ma_ema_fast > self._longband_fast:
            self._longband_fast = max(self._longband_fast, new_long)
        else:
            self._longband_fast = new_long
        
        if self._rsi_ma_ema_fast < self._shortband_fast and self._rsi_ma_ema_fast < self._shortband_fast:
            self._shortband_fast = min(self._shortband_fast, new_short)
        else:
            self._shortband_fast = new_short
        
        if self._rsi_ma_ema_fast > self._shortband_fast:
            self._trend_fast = 1
        elif self._rsi_ma_ema_fast < self._longband_fast:
            self._trend_fast = -1
        
        self._fast_line = self._longband_fast if self._trend_fast == 1 else self._shortband_fast

    def _update_bands_slow(self, dar: float):
        if self._rsi_ma_ema_slow is None:
            return
        
        new_long = self._rsi_ma_ema_slow - dar
        new_short = self._rsi_ma_ema_slow + dar
        
        if self._rsi_ma_ema_slow > self._longband_slow and self._rsi_ma_ema_slow > self._longband_slow:
            self._longband_slow = max(self._longband_slow, new_long)
        else:
            self._longband_slow = new_long
        
        if self._rsi_ma_ema_slow < self._shortband_slow and self._rsi_ma_ema_slow < self._shortband_slow:
            self._shortband_slow = min(self._shortband_slow, new_short)
        else:
            self._shortband_slow = new_short
        
        if self._rsi_ma_ema_slow > self._shortband_slow:
            self._trend_slow = 1
        elif self._rsi_ma_ema_slow < self._longband_slow:
            self._trend_slow = -1
        
        self._slow_line = self._longband_slow if self._trend_slow == 1 else self._shortband_slow

    def on_tick(self, ltp: float, position: Position | None) -> Signal | TrailResult:
        self._closes.append(ltp)
        self._update_rsi(ltp)
        
        if self._rsi_ma_ema_fast is None or self._rsi_ma_ema_slow is None:
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