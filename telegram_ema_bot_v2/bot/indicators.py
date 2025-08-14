
# bot/indicators.py
import numpy as np
import pandas as pd
from .config import (
    EMA_FAST, EMA_MED, EMA_SLOW, EMA50, EMA200,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    RSI6, RSI9, RSI21,
    KDJ_N, KDJ_K, KDJ_D,
    SRSI_RSI_LEN, SRSI_STOCH_LEN, SRSI_K, SRSI_D,
    VOL_MA1, VOL_MA2,
)

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def macd(series: pd.Series, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = (dif - dea) * 2.0
    return dif, dea, macd_hist

def kdj(df: pd.DataFrame, n=KDJ_N, k=KDJ_K, d=KDJ_D):
    low_min = df["low"].rolling(n).min()
    high_max = df["high"].rolling(n).max()
    rsv = (df["close"] - low_min) / (high_max - low_min + 1e-9) * 100
    K = rsv.ewm(alpha=1/k, adjust=False).mean()
    D = K.ewm(alpha=1/d, adjust=False).mean()
    J = 3*K - 2*D
    return K, D, J

def stoch_rsi(series: pd.Series, rsi_len=SRSI_RSI_LEN, stoch_len=SRSI_STOCH_LEN, k=SRSI_K, d=SRSI_D):
    base = rsi(series, rsi_len)
    minr = base.rolling(stoch_len).min()
    maxr = base.rolling(stoch_len).max()
    stoch = (base - minr) / (maxr - minr + 1e-9) * 100
    K = stoch.ewm(alpha=1/k, adjust=False).mean()
    D = K.ewm(alpha=1/d, adjust=False).mean()
    return K, D

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([
        (h - l),
        (h - prev_c).abs(),
        (l - prev_c).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema5"]  = ema(out["close"], EMA_FAST)
    out["ema10"] = ema(out["close"], EMA_MED)
    out["ema21"] = ema(out["close"], EMA_SLOW)
    out["ema50"] = ema(out["close"], EMA50)
    out["ema200"]= ema(out["close"], EMA200)

    dif, dea, hist = macd(out["close"])
    out["macd_dif"] = dif
    out["macd_dea"] = dea
    out["macd_hist"]= hist

    out["rsi6"]  = rsi(out["close"], RSI6)
    out["rsi9"]  = rsi(out["close"], RSI9)
    out["rsi21"] = rsi(out["close"], RSI21)

    K, D, J = kdj(out)
    out["kdj_k"], out["kdj_d"], out["kdj_j"] = K, D, J

    sK, sD = stoch_rsi(out["close"])
    out["srsi_k"], out["srsi_d"] = sK, sD

    out["vol_ma5"]  = out["volume"].rolling(VOL_MA1).mean()
    out["vol_ma10"] = out["volume"].rolling(VOL_MA2).mean()

    out["atr14"] = atr(out, 14)
    return out
