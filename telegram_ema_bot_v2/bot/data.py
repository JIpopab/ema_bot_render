
# bot/data.py
import requests
import pandas as pd
from .config import INSTRUMENT_ID, CANDLES_LIMIT

OKX_BASE = "https://www.okx.com"

TF_MAP = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1H",
    "2H": "2H",
}

def _okx_candles(tf: str, limit: int = CANDLES_LIMIT):
    url = f"{OKX_BASE}/api/v5/market/candles"
    params = {"instId": INSTRUMENT_ID, "bar": TF_MAP[tf], "limit": limit}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != "0":
        raise RuntimeError(f"OKX API error: {data.get('msg')}")
    arr = data["data"]  # most-recent first
    arr.reverse()
    # columns: ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm, ... (OKX docs)
    rows = []
    for it in arr:
        ts = int(it[0])
        open_, high, low, close = map(float, it[1:5])
        vol = float(it[6]) if len(it) > 6 else float(it[5])
        rows.append([ts, open_, high, low, close, vol])
    df = pd.DataFrame(rows, columns=["time_ms","open","high","low","close","volume"])
    df["time"] = (df["time_ms"] // 1000).astype(int)
    return df[["time","open","high","low","close","volume"]]

def get_all_timeframes(tfs):
    return {tf: _okx_candles(tf) for tf in tfs}

def get_live_price():
    url = f"{OKX_BASE}/api/v5/market/ticker"
    params = {"instId": INSTRUMENT_ID}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != "0":
        raise RuntimeError(f"OKX ticker error: {data.get('msg')}")
    return float(data["data"][0]["last"])
