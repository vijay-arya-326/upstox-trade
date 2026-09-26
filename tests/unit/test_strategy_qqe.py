import pytest
from strategy.qqe import QQEStrategy
from strategy.base import Signal, TrailResult
from core.utils.enums import TransactionType


class TestQQEStrategy:
    def test_initial_state(self):
        strat = QQEStrategy(rsi_len=6, smooth_len=5, factor=3.0)
        assert strat.rsi_len == 6
        assert strat.smooth_len == 5
        assert strat.factor == 3.0

    def test_on_tick_before_warmup_returns_none(self):
        strat = QQEStrategy(rsi_len=6, smooth_len=5, factor=3.0)
        for _ in range(5):
            result = strat.on_tick(25000.0, None)
        assert isinstance(result, Signal)
        assert result.action is None

    def test_signal_generation(self):
        strat = QQEStrategy(rsi_len=3, smooth_len=2, factor=1.0)
        for price in [25000, 25050, 25100, 25150, 25200, 25250, 25300, 25350]:
            result = strat.on_tick(price, None)
        assert isinstance(result, Signal)
        if result.action:
            assert result.action in (TransactionType.BUY, TransactionType.SELL)
            assert result.entry_price is not None
            assert result.initial_sl is not None

    def test_exit_signal(self):
        strat = QQEStrategy(rsi_len=3, smooth_len=2, factor=1.0)
        for price in [25000, 25050, 25100, 25150, 25200, 25250, 25300, 25350, 25400, 25450, 25500, 25550, 25600, 25650, 25700, 25750, 25800]:
            strat.on_tick(price, None)
        
        from core.persistence.models import Position
        from core.utils.enums import PositionStatus
        from datetime import datetime
        
        pos = Position(
            id=1,
            trading_symbol="TEST",
            qty_bought=75,
            qty_sold=0,
            buy_order_id=1001,
            buy_price=25000.0,
            trigger_price=24900.0,
            buy_timestamp=datetime.now(),
            status=PositionStatus.OPEN,
        )
        
        result = strat.on_tick(25400.0, pos)
        assert isinstance(result, TrailResult)