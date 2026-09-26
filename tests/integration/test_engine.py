import pytest
from engine import StrategyEngine
from strategy.registry import build_composite


class TestEngineIntegration:
    def test_engine_initializes(self):
        strategy = build_composite()
        engine = StrategyEngine(strategy, instrument_key="NSE_FO|TEST")
        assert engine.strategy == strategy
        assert engine.instrument_key == "NSE_FO|TEST"
        assert engine.position is None

    def test_build_composite_returns_single_strategy(self):
        import os
        os.environ["STRATEGIES"] = "UT_BOT"
        strategy = build_composite()
        assert strategy.__class__.__name__ == "UTBotStrategy"

    def test_build_composite_returns_composite(self):
        import os
        os.environ["STRATEGIES"] = "UT_BOT,QQE"
        os.environ["STRATEGY_MODE"] = "MAJORITY"
        strategy = build_composite()
        assert strategy.__class__.__name__ == "CompositeStrategy"
        assert len(strategy.strategies) == 2