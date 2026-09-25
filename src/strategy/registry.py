import os
import json
from typing import List

from strategy.base import Strategy, Signal, TrailResult
from strategy.ut_bot import UTBotStrategy
from strategy.qqe import QQEStrategy
from strategy.hma import HMAStrategy
from core.utils.enums import TransactionType


STRATEGIES = {
    "UT_BOT": UTBotStrategy,
    "QQE": QQEStrategy,
    "HMA": HMAStrategy,
}


class CombinationMode(str):
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    ANY = "any"


class CompositeStrategy(Strategy):
    def __init__(
        self,
        strategies: List[Strategy],
        mode: str = CombinationMode.MAJORITY,
        weights: dict[str, float] | None = None,
        entry_threshold: float = 0.5,
    ):
        self.strategies = strategies
        self.mode = mode
        self.weights = weights or {s.__class__.__name__: 1.0 for s in strategies}
        self.entry_threshold = entry_threshold

    def on_tick(self, ltp: float, position) -> Signal | TrailResult:
        if position is None:
            return self._combine_entries(ltp)
        else:
            return self._combine_trails(ltp, position)

    def _combine_entries(self, ltp: float) -> Signal:
        signals = [s.on_tick(ltp, None) for s in self.strategies]
        valid = [s for s in signals if s.action is not None]
        
        if not valid:
            return Signal(action=None, entry_price=None, initial_sl=None, metadata={})

        if self.mode == CombinationMode.UNANIMOUS:
            if all(s.action == valid[0].action for s in valid):
                return self._merge_signals(valid)
        elif self.mode == CombinationMode.MAJORITY:
            buys = sum(1 for s in valid if s.action == TransactionType.BUY)
            sells = len(valid) - buys
            if buys > sells:
                return self._merge_signals([s for s in valid if s.action == TransactionType.BUY])
            elif sells > buys:
                return self._merge_signals([s for s in valid if s.action == TransactionType.SELL])
        elif self.mode == CombinationMode.WEIGHTED:
            score = sum(
                self.weights.get(s.__class__.__name__, 1.0) * (1 if s.action == TransactionType.BUY else -1)
                for s in valid
            )
            if abs(score) >= self.entry_threshold:
                action = TransactionType.BUY if score > 0 else TransactionType.SELL
                return self._merge_signals([s for s in valid if s.action == action])
        elif self.mode == CombinationMode.ANY:
            return valid[0]
        
        return Signal(action=None, entry_price=None, initial_sl=None, metadata={})

    def _combine_trails(self, ltp: float, position) -> TrailResult:
        results = [s.on_tick(ltp, position) for s in self.strategies]
        valid = [r for r in results if r.new_sl is not None]
        if not valid:
            return TrailResult(new_sl=None, exit_signal=False)
        
        is_long = getattr(position, 'qty_bought', 0) > 0
        if is_long:
            tightest = min(r.new_sl for r in valid)
            exit_any = any(r.exit_signal for r in valid)
            return TrailResult(new_sl=tightest, exit_signal=exit_any)
        else:
            loosest = max(r.new_sl for r in valid)
            exit_any = any(r.exit_signal for r in valid)
            return TrailResult(new_sl=loosest, exit_signal=exit_any)

    def _merge_signals(self, signals) -> Signal:
        return Signal(
            action=signals[0].action,
            entry_price=sum(s.entry_price for s in signals) / len(signals),
            initial_sl=sum(s.initial_sl for s in signals) / len(signals),
            metadata={s.__class__.__name__: s.metadata for s in signals}
        )

    def on_order_filled(self, order, position):
        for s in self.strategies:
            s.on_order_filled(order, position)


def build_composite() -> Strategy:
    names_str = os.getenv("STRATEGIES", "UT_BOT")
    names = [n.strip().upper() for n in names_str.split(",")]
    strategies = [STRATEGIES[n]() for n in names]
    
    if len(strategies) == 1:
        return strategies[0]
    
    mode = os.getenv("STRATEGY_MODE", CombinationMode.MAJORITY)
    weights = json.loads(os.getenv("STRATEGY_WEIGHTS", "{}"))
    threshold = float(os.getenv("STRATEGY_ENTRY_THRESHOLD", "0.5"))
    
    return CompositeStrategy(strategies, mode, weights, threshold)