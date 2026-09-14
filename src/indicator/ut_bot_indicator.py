import pandas as pd
import numpy as np

def heikin_ashi(df):
    ha = pd.DataFrame(index=df.index)
    ha['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [(df['open'].iloc[0] + df['close'].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i - 1] + ha['close'].iloc[i - 1]) / 2)
    ha['open'] = ha_open
    ha['high'] = pd.concat([df['high'], ha['open'], ha['close']], axis=1).max(axis=1)
    ha['low']  = pd.concat([df['low'],  ha['open'], ha['close']], axis=1).min(axis=1)
    return ha


def atr(df, period=10):
    high, low, close = df['high'], df['low'], df['close']
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    # Pine's atr() uses RMA (Wilder's smoothing), not SMA
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def ut_bot_alerts(df, key_value=1.0, atr_period=10, use_heikin_ashi=False):
    """
    df: DataFrame with columns ['open','high','low','close'], datetime index, ascending order.
    Returns df with added columns: xATRTrailingStop, pos, buy, sell, barbuy, barsell
    """
    df = df.copy()

    src_df = heikin_ashi(df) if use_heikin_ashi else df
    src = src_df['close']

    xATR = atr(src_df if use_heikin_ashi else df, atr_period)
    nLoss = key_value * xATR

    n = len(df)
    trailing_stop = np.zeros(n)
    src_vals = src.values
    nLoss_vals = nLoss.values

    for i in range(n):
        if i == 0 or np.isnan(nLoss_vals[i]):
            trailing_stop[i] = 0.0
            continue

        prev_stop = trailing_stop[i - 1]
        prev_src = src_vals[i - 1]
        cur_src = src_vals[i]

        if cur_src > prev_stop and prev_src > prev_stop:
            trailing_stop[i] = max(prev_stop, cur_src - nLoss_vals[i])
        elif cur_src < prev_stop and prev_src < prev_stop:
            trailing_stop[i] = min(prev_stop, cur_src + nLoss_vals[i])
        else:
            if cur_src > prev_stop:
                trailing_stop[i] = cur_src - nLoss_vals[i]
            else:
                trailing_stop[i] = cur_src + nLoss_vals[i]

    df['xATRTrailingStop'] = trailing_stop

    # pos state machine
    pos = np.zeros(n)
    for i in range(1, n):
        prev_src = src_vals[i - 1]
        cur_src = src_vals[i]
        prev_stop = trailing_stop[i - 1]
        cur_stop = trailing_stop[i]

        if prev_src < prev_stop and cur_src > cur_stop:
            pos[i] = 1
        elif prev_src > prev_stop and cur_src < cur_stop:
            pos[i] = -1
        else:
            pos[i] = pos[i - 1]

    df['pos'] = pos

    # ema with length 1 == src itself, so "ema" = src
    ema = src.copy()

    # crossover(ema, stop) -> ema crosses above stop
    above = (ema.shift(1) <= pd.Series(trailing_stop, index=df.index).shift(1)) & (ema > trailing_stop)
    # crossover(stop, ema) -> stop crosses above ema
    below = (pd.Series(trailing_stop, index=df.index).shift(1) <= ema.shift(1)) & (trailing_stop > ema)

    df['buy']  = (src > df['xATRTrailingStop']) & above
    df['sell'] = (src < df['xATRTrailingStop']) & below

    df['barbuy']  = src > df['xATRTrailingStop']
    df['barsell'] = src < df['xATRTrailingStop']

    return df