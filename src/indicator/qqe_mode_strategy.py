"""
QQE Mode Strategy
-----------------
Computes a fast QQE line and a slow QQE line (RSI smoothed + ATR-of-RSI trailing
bands), then trades when the fast histogram crosses above/below the slow
histogram's threshold band around zero.

Usage:
    python qqe_mode_strategy.py data.csv
    python qqe_mode_strategy.py --ticker AAPL --start 2018-01-01   # needs yfinance

CSV must have columns: date, open, high, low, close, volume (case-insensitive).
"""

import argparse
import numpy as np
import pandas as pd


# ---------------------------------------------------------------- indicators
def rsi(series: pd.Series, length: int) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1 / length, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / length, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def qqe(src: pd.Series, rsi_len: int, smooth_len: int, factor: float):
    """Returns (qqe_line, rsi_ma) as numpy arrays."""
    rsi_ma = ema(rsi(src, rsi_len), smooth_len).to_numpy()
    atr_rsi = np.abs(np.diff(rsi_ma, prepend=rsi_ma[0]))
    ma_atr_rsi = pd.Series(atr_rsi).ewm(span=rsi_len * 2 - 1, adjust=False).mean().to_numpy()
    dar = pd.Series(ma_atr_rsi).ewm(span=rsi_len * 2 - 1, adjust=False).mean().to_numpy() * factor

    n = len(src)
    longband = np.zeros(n)
    shortband = np.zeros(n)
    trend = np.zeros(n, dtype=int)
    qqe_line = np.zeros(n)

    for i in range(1, n):
        new_long = rsi_ma[i] - dar[i]
        new_short = rsi_ma[i] + dar[i]

        if rsi_ma[i - 1] > longband[i - 1] and rsi_ma[i] > longband[i - 1]:
            longband[i] = max(longband[i - 1], new_long)
        else:
            longband[i] = new_long

        if rsi_ma[i - 1] < shortband[i - 1] and rsi_ma[i] < shortband[i - 1]:
            shortband[i] = min(shortband[i - 1], new_short)
        else:
            shortband[i] = new_short

        if rsi_ma[i] > shortband[i - 1]:
            trend[i] = 1
        elif rsi_ma[i] < longband[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]

        qqe_line[i] = longband[i] if trend[i] == 1 else shortband[i]

    return qqe_line, rsi_ma


# ------------------------------------------------------------------ signals
def generate_signals(df, rsi_len=6, smooth_len=5, factor=3.0,
                      rsi_len2=6, smooth_len2=5, factor2=1.61,
                      threshold=3.0, long_only=False):
    df = df.copy()
    fast_line, _ = qqe(df["close"], rsi_len, smooth_len, factor)
    slow_line, _ = qqe(df["close"], rsi_len2, smooth_len2, factor2)

    df["fast_hist"] = fast_line - 50
    df["slow_hist"] = slow_line - 50
    upper = df["slow_hist"] + threshold
    lower = df["slow_hist"] - threshold

    long_cond = (df["fast_hist"] > upper) & (df["fast_hist"].shift(1) <= upper.shift(1))
    short_cond = (df["fast_hist"] < lower) & (df["fast_hist"].shift(1) >= lower.shift(1))

    df["signal"] = 0
    df.loc[long_cond, "signal"] = 1
    df.loc[short_cond, "signal"] = -1 if not long_only else 0
    df.loc[short_cond, "exit_long"] = True
    df.loc[long_cond, "exit_short"] = True
    return df


# ------------------------------------------------------------------ backtest
def backtest(df, commission=0.0005):
    position = 0
    entry_price = None
    equity = 1.0
    equity_curve = []
    trades = []

    for i in range(len(df)):
        row = df.iloc[i]
        price = row["close"]

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
        return raw


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv", nargs="?", help="Path to OHLCV CSV file")
    p.add_argument("--ticker", help="Ticker symbol (uses yfinance if no CSV given)")
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--rsi-len", type=int, default=6)
    p.add_argument("--smooth-len", type=int, default=5)
    p.add_argument("--factor", type=float, default=3.0)
    p.add_argument("--rsi-len2", type=int, default=6)
    p.add_argument("--smooth-len2", type=int, default=5)
    p.add_argument("--factor2", type=float, default=1.61)
    p.add_argument("--threshold", type=float, default=3.0)
    p.add_argument("--long-only", action="store_true")
    args = p.parse_args()

    data = load_data(args)
    data = generate_signals(
        data, rsi_len=args.rsi_len, smooth_len=args.smooth_len, factor=args.factor,
        rsi_len2=args.rsi_len2, smooth_len2=args.smooth_len2, factor2=args.factor2,
        threshold=args.threshold, long_only=args.long_only,
    )
    data, trades = backtest(data)
    summarize(trades, data["equity"])
