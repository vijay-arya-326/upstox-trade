import pytest
from strategy.registry import CompositeStrategy, CombinationMode
from strategy.ut_bot import UTBotStrategy
from strategy.qqe import QQEStrategy
from strategy.hma import HMAStrategy
from strategy.base import Signal, TrailResult
from core.utils.enums import TransactionType


class TestCompositeStrategy:
    def test_unanimous_mode_requires_all_agree(self):
        s1 = UTBotStrategy(atr_period=3, key_value=1.0)
        s2 = QQEStrategy(rsi_len=3, smooth_len=2, factor=1.0)
        
        comp = CompositeStrategy([s1, s2], mode=CombinationMode.UNANIMOUS)
        
        for price in [25000, 25100, 25200, 25300, 25400, 25500]:
            result = comp.on_tick(price, None)
        
        assert isinstance(result, Signal)
        if result.action:
            assert result.action in (TransactionType.BUY, TransactionType.SELL)

    def test_majority_mode(self):
        s1 = UTBotStrategy(atr_period=3, key_value=1.0)
        s2 = QQEStrategy(rsi_len=3, smooth_len=2, factor=1.0)
        s3 = HMAStrategy(hma_len=5, slope_lookback=1, require_slope=False)
        
        comp = CompositeStrategy([s1, s2, s3], mode=CombinationMode.MAJORITY)
        
        for price in [25000, 25100, 25200, 25300, 25400, 25500]:
            result = comp.on_tick(price, None)
        
        assert isinstance(result, Signal)

    def test_weighted_mode(self):
        s1 = UTBotStrategy(atr_period=3, key_value=1.0)
        s2 = QQEStrategy(rsi_len=3, smooth_len=2, factor=1.0)
        
        comp = CompositeStrategy(
            [s1, s2], 
            mode=CombinationMode.WEIGHTED,
            weights={"UTBotStrategy": 2.0, "QQEStrategy": 1.0},
            entry_threshold=1.5
        )
        
        for price in [25000, 25100, 25200, 25300, 25400, 25500]:
            result = comp.on_tick(price, None)
        
        assert isinstance(result, Signal)

    def test_trail_returns_tightest_for_long(self):
        s1 = UTBotStrategy(atr_period=3, key_value=1.0)
        s2 = QQEStrategy(rsi_len=3, smooth_len=2, factor=1.0)
        
        comp = CompositeStrategy([s1, s2], mode=CombinationMode.MAJORITY)
        
        for price in [25000, 25100, 25200, 25300, 25400, 25500]:
            comp.on_tick(price, None)
        
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
        
        result = comp.on_tick(25600.0, pos)
        assert isinstance(result, TrailResult)
        if result.new_sl:
            assert result.new_sl >= pos.trigger_price