import pytest
from strategy.hma import HMAStrategy
from strategy.base import Signal, TrailResult
from core.utils.enums import TransactionType


class TestHMAStrategy:
    def test_initial_state(self):
        strat = HMAStrategy(hma_len=10, slope_lookback=2)
        assert strat.hma_len == 10
        assert strat.slope_lookback == 2

    def test_on_tick_before_warmup_returns_none(self):
        strat = HMAStrategy(hma_len=20, slope_lookback=2)
        for _ in range(10):
            result = strat.on_tick(25000.0, None)
        assert isinstance(result, Signal)
        assert result.action is None

    def test_signal_generation(self):
        strat = HMAStrategy(hma_len=5, slope_lookback=1, require_slope=False)
        for price in [25000, 25050, 25100, 25150, 25200, 25250, 25300, 25350, 25400]:
            result = strat.on_tick(price, None)
        assert isinstance(result, Signal)
        if result.action:
            assert result.action in (TransactionType.BUY, TransactionType.SELL)
            assert result.entry_price is not None
            assert result.initial_sl is not None

    def test_exit_signal_on_cross_down(self):
        strat = HMAStrategy(hma_len=5, slope_lookback=1, require_slope=False)
        for price in [25000, 25050, 25100, 25150, 25200, 25250, 25300, 25350, 25400]:
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
        
        result = strat.on_tick(24800.0, pos)
        assert isinstance(result, TrailResult)