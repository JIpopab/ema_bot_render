
# bot/utils.py
import numpy as np
import pandas as pd
from typing import Optional, Tuple

def crossed_over(a_prev, b_prev, a_curr, b_curr) -> bool:
    return a_prev < b_prev and a_curr > b_curr

def crossed_under(a_prev, b_prev, a_curr, b_curr) -> bool:
    return a_prev > b_prev and a_curr < b_curr

def last_cross_index(series_a: pd.Series, series_b: pd.Series, dir_: str, lookback: int):
    a = series_a.values
    b = series_b.values
    n = len(a)
    for i in range(1, min(lookback+2, n)):
        a_prev, b_prev = a[-i-1], b[-i-1]
        a_curr, b_curr = a[-i],   b[-i]
        if dir_ == "up" and crossed_over(a_prev, b_prev, a_curr, b_curr):
            return i-1
        if dir_ == "down" and crossed_under(a_prev, b_prev, a_curr, b_curr):
            return i-1
    return None

def map_index_by_time(src_df: pd.DataFrame, dst_df: pd.DataFrame, src_idx: int) -> int:
    t = src_df["time"].iloc[src_idx]
    pos = dst_df["time"].searchsorted(t, side="right") - 1
    return max(0, min(pos, len(dst_df)-1))

def within(value: float, target: float, tol: float) -> bool:
    return abs(value - target) <= tol

def swing_levels(df: pd.DataFrame, lookback:int=20) -> Tuple[float,float]:
    recent = df.tail(lookback)
    return recent["low"].min(), recent["high"].max()

def atr_levels(df: pd.DataFrame, idx: int, mul: float = 1.0) -> Tuple[float,float]:
    c = df["close"].iloc[idx]
    a = df["atr14"].iloc[idx]
    return c - mul*a, c + mul*a

def last_cross_within(series_a: pd.Series, series_b: pd.Series, dir_: str, max_bars:int) -> bool:
    x = last_cross_index(series_a, series_b, dir_, lookback=max_bars)
    return x is not None and x <= max_bars

def candle_color(df: pd.DataFrame, i:int) -> str:
    try:
        return "green" if df["close"].iloc[i] >= df["open"].iloc[i] else "red"
    except Exception:
        return "green"

def macd_prev_trend_ok(df: pd.DataFrame, direction: str, min_bars:int=4) -> bool:
    dif = df["macd_dif"].values
    dea = df["macd_dea"].values
    hist = df["macd_hist"].values
    vol = df["volume"].values
    vma = df["vol_ma10"].values

    want = "up" if direction == "long" else "down"
    cross_ago = last_cross_index(pd.Series(dif), pd.Series(dea), want, lookback=100)
    if cross_ago is None:
        return False
    start = len(df) - cross_ago - 1

    need_sign = -1 if direction == "long" else 1
    count = 0
    i = start - 1
    while i >= 0 and count < min_bars:
        h = hist[i]
        ok_bar = (h * need_sign) > 0
        if ok_bar:
            count += 1
        else:
            low_vol = vol[i] < vma[i] if not np.isnan(vma[i]) else False
            bad_color = (direction == "long" and candle_color(df, i) == "green") or \
                        (direction == "short" and candle_color(df, i) == "red")
            if not (low_vol and bad_color):
                break
        i -= 1
    return count >= min_bars
