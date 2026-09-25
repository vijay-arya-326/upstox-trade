# Upstox-Trade Strategy Engine - Full Planning Conversation

## Project Context
This is a Python CLI tool for placing and managing Upstox orders with automated OAuth token management, SQLite persistence, and trailing stop-loss logic.

**Current Stack**: Python 3.12+, uv, pydantic, requests, rich, sqlmodel, alembic, dotenv

---

## Original Request
> "create a plan, designing new flow where indicator give buy indicator depending on trader and defined login trailing stop loss will be updated and triggers"

---

## Phase 1: Single Strategy Architecture

### Strategy Interface (`src/strategy/base.py`)
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from helper_func.common_models import TransactionType

@dataclass
class Signal:
    action: TransactionType | None      # BUY / SELL / None
    entry_price: float | None
    initial_sl: float | None
    metadata: dict                      # indicator values for logging

@dataclass
class TrailResult:
    new_sl: float | None                # None = don't update
    exit_signal: bool                   # True = close position

class Strategy(ABC):
    @abstractmethod
    def on_tick(self, ltp: float, position: Position | None) -> Signal | TrailResult:
        """Called on every market tick. Returns entry signal or trail update."""
        pass

    @abstractmethod
    def on_order_filled(self, order: OrderDetail, position: Position) -> None:
        """Called when entry order fills - initialize trailing state."""
        pass
```

### Concrete Strategies (`src/strategy/`)
| File | Logic |
|------|-------|
| `ut_bot.py` | UT Bot (ATR trailing) - long when close > trail, short when close < trail |
| `qqe.py` | QQE Mod - RSI smoothed + Fast/Slow cross |
| `hma.py` | HMA Trend - slope change + candle confirmation |
| `composite.py` | Multi-indicator vote (configurable weights) |

### Strategy Registry (`src/strategy/registry.py`)
```python
STRATEGIES = {
    "UT_BOT": UTBotStrategy,
    "QQE": QQEStrategy,
    "HMA": HMAStrategy,
}
# Loaded from env: STRATEGY_NAME=UT_BOT
# Optional: STRATEGY_PARAMS_JSON='{"atr_period":14,"mult":2.5}'
```

### Engine (`src/engine.py`)
```python
class StrategyEngine:
    def __init__(self, strategy: Strategy, instrument_key: str):
        self.strategy = strategy
        self.instrument_key = instrument_key
        self.position: Position | None = None

    def run(self):
        while True:
            ltp = getMarketData(self.instrument_key)
            
            if self.position is None:
                signal = self.strategy.on_tick(ltp, None)
                if signal.action:
                    self._place_entry_order(signal)
            else:
                result = self.strategy.on_tick(ltp, self.position)
                if result.exit_signal:
                    self._close_position()
                elif result.new_sl:
                    self._update_sl(result.new_sl)
            
            sleep(1)
```

### Position State Machine
```
FLAT → (Signal.BUY) → ENTRY_PENDING → (fill) → IN_POSITION 
                                                          ↓
                                              (TrailResult.new_sl) → modify SL
                                                          ↓
                                              (TrailResult.exit_signal / opposite Signal) → EXIT_PENDING → FLAT
```

---

## Phase 2: Multi-Strategy Combination (User Request)

### Combination Modes (`src/strategy/combination.py`)
```python
class CombinationMode(str, Enum):
    UNANIMOUS = "unanimous"       # All must agree
    MAJORITY = "majority"         # >50% agree
    WEIGHTED = "weighted"         # Sum(weight * signal) > threshold
    SEQUENTIAL = "sequential"     # Strategy A entry → Strategy B manages SL
    ANY = "any"                   # First signal wins
```

### Composite Strategy (`src/strategy/composite.py`)
```python
class CompositeStrategy(Strategy):
    def __init__(
        self,
        strategies: List[Strategy],
        mode: CombinationMode = CombinationMode.MAJORITY,
        weights: dict[str, float] | None = None,
        entry_threshold: float = 0.5,
    ):
        self.strategies = strategies
        self.mode = mode
        self.weights = weights or {s.name: 1.0 for s in strategies}
        self.entry_threshold = entry_threshold

    def on_tick(self, ltp: float, position: Position | None) -> Signal | TrailResult:
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
                self.weights[s.__class__.__name__] * (1 if s.action == TransactionType.BUY else -1)
                for s in valid
            )
            if abs(score) >= self.entry_threshold:
                action = TransactionType.BUY if score > 0 else TransactionType.SELL
                return self._merge_signals([s for s in valid if s.action == action])
        elif self.mode == CombinationMode.ANY:
            return valid[0]
        
        return Signal(action=None, entry_price=None, initial_sl=None, metadata={})

    def _combine_trails(self, ltp: float, position: Position) -> TrailResult:
        results = [s.on_tick(ltp, position) for s in self.strategies]
        valid = [r for r in results if r.new_sl is not None]
        if not valid:
            return TrailResult(new_sl=None, exit_signal=False)
        
        if position.is_long:
            tightest = min(r.new_sl for r in valid)
            exit_any = any(r.exit_signal for r in valid)
            return TrailResult(new_sl=tightest, exit_signal=exit_any)
        else:
            loosest = max(r.new_sl for r in valid)
            exit_any = any(r.exit_signal for r in valid)
            return TrailResult(new_sl=loosest, exit_signal=exit_any)
```

### Registry Update
```python
# Env format:
# STRATEGIES=UT_BOT,QQE,HMA
# STRATEGY_MODE=WEIGHTED
# STRATEGY_WEIGHTS='{"UTBotStrategy":2.0,"QQEStrategy":1.0,"HMAStrategy":1.5}'
# STRATEGY_ENTRY_THRESHOLD=1.5

def build_composite() -> Strategy:
    names = os.getenv("STRATEGIES", "UT_BOT").split(",")
    strategies = [STRATEGIES[n.strip().upper()]() for n in names]
    
    if len(strategies) == 1:
        return strategies[0]
    
    mode = CombinationMode(os.getenv("STRATEGY_MODE", "MAJORITY"))
    weights = json.loads(os.getenv("STRATEGY_WEIGHTS", "{}"))
    threshold = float(os.getenv("STRATEGY_ENTRY_THRESHOLD", "0.5"))
    
    return CompositeStrategy(strategies, mode, weights, threshold)
```

### Position Management Rules
| Scenario | Behavior |
|----------|----------|
| **Entry** | Composite returns single `Signal` → one entry order |
| **Trailing SL** | Composite returns tightest (long) / loosest (short) SL across all strategies |
| **Exit** | Any strategy signals exit → close position |
| **Opposite signal while in position** | Treated as exit signal (close + reverse if new composite signal) |

### Example Configs
```bash
# Conservative: all must agree
STRATEGIES=UT_BOT,QQE,HMA
STRATEGY_MODE=UNANIMOUS

# Balanced: majority vote
STRATEGIES=UT_BOT,QQE,HMA
STRATEGY_MODE=MAJORITY

# Weighted: UT Bot 2x, others 1x, need net > 1.5
STRATEGIES=UT_BOT,QQE,HMA
STRATEGY_MODE=WEIGHTED
STRATEGY_WEIGHTS='{"UTBotStrategy":2.0,"QQEStrategy":1.0,"HMAStrategy":1.0}'
STRATEGY_ENTRY_THRESHOLD=1.5

# Fast entry: first signal wins
STRATEGIES=UT_BOT,QQE
STRATEGY_MODE=ANY
```

---

## Files to Create

### New Files
| File | Purpose |
|------|---------|
| `src/strategy/__init__.py` | Package marker |
| `src/strategy/base.py` | Abstract `Strategy`, `Signal`, `TrailResult` |
| `src/strategy/registry.py` | Strategy factory, config loading from env |
| `src/strategy/ut_bot.py` | UT Bot strategy (port from `ut_bot_indicator.py`) |
| `src/strategy/qqe.py` | QQE Mod strategy (port from `qqe_mode_strategy.py`) |
| `src/strategy/hma.py` | HMA Trend strategy (port from `hma_trend_strategy.py`) |
| `src/strategy/combination.py` | `CombinationMode` enum |
| `src/strategy/composite.py` | `CompositeStrategy` implementing combination logic |
| `src/engine.py` | `StrategyEngine` main loop replacing `main.py` sample code |
| `src/db/models/strategy_state.py` | SQLModel table for persisting indicator state |
| `src/db/models/signal_log.py` | SQLModel table for logging every signal/trail decision |
| `alembic/versions/XXXX_add_strategy_tables.py` | Migration for the two new tables |

### Files to Modify
| File | Change |
|------|--------|
| `src/main.py` | Replace sample order loop → instantiate `StrategyEngine` from registry |
| `src/helper_func/config.py` | Add `STRATEGY_NAME`, `STRATEGY_PARAMS`, `MAX_POSITION_SIZE`, `DAILY_LOSS_LIMIT`, `STRATEGIES`, `STRATEGY_MODE`, `STRATEGY_WEIGHTS`, `STRATEGY_ENTRY_THRESHOLD` |
| `src/helper_func/order_helper.py` | Ensure `update_sl_for` only moves SL favorably (add guard) |
| `src/db/models/__init__.py` | Export new models |

### Files to Deprecate/Remove
| File | Reason |
|------|--------|
| `src/indicator/ut_bot_indicator.py` | Logic moves to `src/strategy/ut_bot.py` |
| `src/indicator/qqe_mode_strategy.py` | Logic moves to `src/strategy/qqe.py` |
| `src/indicator/hma_trend_strategy.py` | Logic moves to `src/strategy/hma.py` |
| `src/indicator/` | Entire directory can be removed after migration |

---

## Why Move `src/indicator/` → `src/strategy/`

| Reason | Detail |
|--------|--------|
| **Semantic clarity** | "Indicators" compute values (ATR, RSI, HMA). "Strategies" make **decisions** (entry/exit/trail) using those values. |
| **Unified interface** | All strategies implement `Strategy.on_tick()` returning `Signal | TrailResult`. Old indicator files have no common interface. |
| **State encapsulation** | Strategies need persistent internal state (trail level, previous RSI, HMA slope). Indicators are typically stateless functions. |
| **Config-driven selection** | Registry loads `STRATEGY_NAME` from env. Single `strategy/` package makes dynamic import clean. |
| **Testability** | Each strategy can be unit-tested with synthetic tick sequences against expected `Signal`/`TrailResult` outputs. |
| **Extensibility** | Adding a new strategy = one file in `strategy/` implementing the ABC. No changes to engine or main. |
| **Separation of concerns** | `engine.py` knows only `Strategy` interface. It doesn't care about ATR vs RSI vs HMA internals. |

---

## Implementation Order

1. `src/strategy/base.py` - abstract interface
2. `src/strategy/combination.py` - `CombinationMode` enum
3. `src/strategy/composite.py` - `CompositeStrategy` 
4. `src/strategy/registry.py` - factory + config loading (updated for multi-strategy)
5. Port existing indicators to `src/strategy/` implementing `Strategy`
6. `src/engine.py` - main loop replacing `main.py` sample code
7. Update `main.py` → instantiate engine from registry
8. Add `strategy_state` + `signals` models + alembic migration
9. Update `config.py` with new env vars
10. Unit tests for each strategy's `on_tick()` with synthetic ticks

---

## Safety Guards

- Max position size per strategy (env)
- Daily loss limit (env) → engine stops
- SL must move only in favorable direction (enforced in `order_helper.update_sl_for`)
- Idempotent order placement (client order tag = strategy + timestamp)

---

## Persistence Additions

- `strategy_state` table: persist indicator state across restarts (JSON blob per strategy)
- `signals` table: log every Signal/TrailResult for backtest/analysis

---

## Configuration (env)
```bash
# Single strategy (legacy)
STRATEGY_NAME=UT_BOT
STRATEGY_PARAMS='{"atr_period":14,"mult":2.5,"use_heikin_ashi":true}'

# Multi-strategy (new)
STRATEGIES=UT_BOT,QQE,HMA
STRATEGY_MODE=WEIGHTED
STRATEGY_WEIGHTS='{"UTBotStrategy":2.0,"QQEStrategy":1.0,"HMAStrategy":1.0}'
STRATEGY_ENTRY_THRESHOLD=1.5

# Common
INSTRUMENT_KEY=NSE_FO|115242
LOTS=75
MAX_POSITION_SIZE=1000
DAILY_LOSS_LIMIT=5000
```