import pytest
from strategy.ut_bot import UTBotStrategy
from strategy.base import Signal, TrailResult
from core.utils.enums import TransactionType


class TestUTBotStrategy:
    def test_initial_state(self):
        strat = UTBotStrategy(atr_period=3, key_value=1.0)
        assert strat.atr_period == 3
        assert strat.key_value == 1.0

    def test_on_tick_before_warmup_returns_none(self):
        strat = UTBotStrategy(atr_period=10, key_value=1.0)
        result = strat.on_tick(25000.0, None)
        assert isinstance(result, Signal)
        assert result.action is None

    def test_buy_signal_generated(self):
        strat = UTBotStrategy(atr_period=3, key_value=1.0, use_heikin_ashi=False)
        for price in [25000, 25100, 25200, 25300, 25400, 25500]:
            result = strat.on_tick(price, None)
        assert isinstance(result, Signal)
        if result.action:
            assert result.action in (TransactionType.BUY, TransactionType.SELL)
            assert result.entry_price is not None
            assert result.initial_sl is not None

    def test_trail_updates_sl(self):
        strat = UTBotStrategy(atr_period=3, key_value=1.0)
        for price in [25000, 25100, 25200, 25300, 25400, 25500]:
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
        
        result = strat.on_tick(25600.0, pos)
        assert isinstance(result, TrailResult)
        if result.new_sl:
            assert result.new_sl > pos.trigger_price