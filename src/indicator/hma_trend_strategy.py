"""
HMA Trend Strategy
------------------
Rules:
  - Long when close crosses above the Hull MA (optionally only if HMA is sloping up)
  - Short when close crosses below the Hull MA (optionally only if HMA is sloping down)
  - Optional % stop loss / take profit
  - Flat on opposite HMA cross

Usage:
    python hma_trend_strategy.py data.csv
    python hma_trend_strategy.py --ticker AAPL --start 2018-01-01   # needs yfinance

CSV must have columns: date, open, high, low, close, volume (case-insensitive).
"""

import argparse
import numpy as np
import pandas as pd


# ---------------------------------------------------------------- indicators
def wma(series: pd.Series, length: int) -> pd.Series:
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def hma(series: pd.Series, length: int) -> pd.Series:
    half = max(int(length / 2), 1)
    sqrt_len = max(int(np.sqrt(length)), 1)
    raw = 2 * wma(series, half) - wma(series, length)
    return wma(raw, sqrt_len)


# ------------------------------------------------------------------ signals
def generate_signals(df: pd.DataFrame, hma_len=55, slope_lookback=2,
                      require_slope=True, long_only=False) -> pd.DataFrame:
    df = df.copy()
    df["hma"] = hma(df["close"], hma_len)

    hma_up = df["hma"] > df["hma"].shift(slope_lookback)
    hma_down = df["hma"] < df["hma"].shift(slope_lookback)

    cross_up = (df["close"] > df["hma"]) & (df["close"].shift(1) <= df["hma"].shift(1))
    cross_down = (df["close"] < df["hma"]) & (df["close"].shift(1) >= df["hma"].shift(1))

    long_cond = cross_up & (hma_up if require_slope else True)
    short_cond = cross_down & (hma_down if require_slope else True)

    df["signal"] = 0
    df.loc[long_cond, "signal"] = 1
    df.loc[short_cond, "signal"] = -1 if not long_only else 0
    df.loc[cross_down, "exit_long"] = True
    df.loc[cross_up, "exit_short"] = True
    return df


# ------------------------------------------------------------------ backtest
def backtest(df: pd.DataFrame, sl_pct=0.02, tp_pct=0.04, use_sltp=True,
             commission=0.0005) -> pd.DataFrame:
    position = 0          # -1, 0, 1
    entry_price = None
    equity = 1.0
    equity_curve = []
    trades = []

    for i in range(len(df)):
        row = df.iloc[i]
        price = row["close"]

        # manage open position: SL/TP + exit signals
        if position != 0 and use_sltp and entry_price is not None:
            change = (price - entry_price) / entry_price * position
            if change <= -sl_pct or change >= tp_pct:
                equity *= (1 + change - commission)
                trades.append(change - commission)
                position = 0
                entry_price = None

        if position == 1 and row.get("exit_long", False):
            change = (price - entry_price) / entry_price
            equity *= (1 + change - commission)
            trades.append(change - commission)
            position, entry_price = 0, None

        if position == -1 and row.get("exit_short", False):
            change = (entry_price - price) / entry_price
            equity *= (1 + change - commission)
            trades.append(change - commission)
            position, entry_price = 0, None

        # new entries
        if position == 0 and row["signal"] != 0:
            position = row["signal"]
            entry_price = price
            equity *= (1 - commission)

        equity_curve.append(equity)

    df["equity"] = equity_curve
    return df, trades


def summarize(trades, equity_curve: pd.Series):
    if not trades:
        print("No trades taken.")
        return
    trades = np.array(trades)
    total_return = equity_curve.iloc[-1] - 1
    win_rate = (trades > 0).mean()
    print(f"Trades:        {len(trades)}")
    print(f"Win rate:      {win_rate:.1%}")
    print(f"Total return:  {total_return:.1%}")
    print(f"Avg trade:     {trades.mean():.2%}")
    running_max = equity_curve.cummax()
    dd = (equity_curve / running_max - 1).min()
    print(f"Max drawdown:  {dd:.1%}")


# ---------------------------------------------------------------------- main
def load_data(args) -> pd.DataFrame:
    if args.csv:
        df = pd.read_csv(args.csv)
        df.columns = [c.lower() for c in df.columns]
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df
    else:
        import yfinance as yf
        raw = yf.download(args.ticker, start=args.start, progress=False)
        raw = raw.rename(columns=str.lower).reset_index()
        raw = raw.rename(columns={"date": "date", "adj close": "adj_close"})
        return raw


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv", nargs="?", help="Path to OHLCV CSV file")
    p.add_argument("--ticker", help="Ticker symbol (uses yfinance if no CSV given)")
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--hma-len", type=int, default=55)
    p.add_argument("--slope-lookback", type=int, default=2)
    p.add_argument("--no-slope-filter", action="store_true")
    p.add_argument("--long-only", action="store_true")
    p.add_argument("--sl", type=float, default=0.02)
    p.add_argument("--tp", type=float, default=0.04)
    p.add_argument("--no-sltp", action="store_true")
    args = p.parse_args()

    data = load_data(args)
    data = generate_signals(
        data, hma_len=args.hma_len, slope_lookback=args.slope_lookback,
        require_slope=not args.no_slope_filter, long_only=args.long_only,
    )
    data, trades = backtest(
        data, sl_pct=args.sl, tp_pct=args.tp, use_sltp=not args.no_sltp,
    )
    summarize(trades, data["equity"])
