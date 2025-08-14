# main.py
# Production-ready orchestrator: downloads 5m/15m/30m/1H/2H candles from OKX,
# computes indicators via bot.indicators.add_all_indicators, runs run_checks,
# logs per-condition details, stores snapshot, and notifies via Telegram.

import os
import time
import json
import logging
import traceback
from threading import Thread
from datetime import datetime
from flask import Flask, jsonify, request

import requests
import pandas as pd

# project modules
from bot.config import (
    TIMEFRAMES, CANDLES_LIMIT, STATE_FILE, LOG_FILE, BOT_INTERVAL_SEC,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, STRICT_MODE, ENABLED_CONDITIONS, EXCHANGE, INSTRUMENT_ID
)
from bot.indicators import add_all_indicators
from bot.checker import run_checks
from bot.notifier import send_telegram_message, format_message

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ema-bot-prod")

OKX_BASE = "https://www.okx.com"

# -----------------------------
# OKX candles helper
# -----------------------------
OKX_TF_MAP = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1H",
    "2H": "2H",
}

def get_okx_candles(instId: str, bar: str, limit: int = 200, since: int = None):
    """
    Request OKX candlesticks.
    Returns list of candles as returned by OKX API (most recent first).
    """
    url = f"{OKX_BASE}/api/v5/market/candles"
    params = {"instId": instId, "bar": bar, "limit": min(limit, 200)}
    # OKX supports limit up to 200 by default; if CANDLES_LIMIT > 200 we fetch in pages (below)
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.exception("OKX candles request failed: %s %s", instId, e)
        raise

    # OKX v5 response: data is dict with "data" list or code/message
    # some accounts return {"code": "0", "data": [...]}
    if isinstance(data, dict) and data.get("code") not in (None, "0", 0):
        raise Exception(f"OKX API error: {data}")
    if "data" in data:
        return data["data"]
    # some endpoints return list directly
    if isinstance(data, list):
        return data
    raise Exception(f"Unexpected OKX response format: {data}")

def fetch_candles_all_tf(inst_id: str, timeframes: list, limit: int):
    """
    Fetch candles for all TFs and return dict tf->DataFrame with columns:
    time (int seconds), open, high, low, close, volume
    """
    results = {}
    for tf in timeframes:
        bar = OKX_TF_MAP.get(tf, tf)
        # OKX returns newest first; we'll request up to limit (<=200)
        # If limit > 200, implement paging (not implemented here because config default <=300)
        # We'll do two-page fetch if requested limit > 200 (simple implementation)
        needed = limit
        all_rows = []
        to_fetch = min(needed, 200)
        try:
            rows = get_okx_candles(inst_id, bar, to_fetch)
            all_rows.extend(rows)
            # if needed more than 200, try second page using since parameter from last item
            if needed > 200 and len(rows) == 200:
                # rows are most recent first; the oldest (in this batch) is rows[-1][0] time string
                last_ts = int(rows[-1][0])  # OKX candle format: [ts, open, high, low, close, vol]
                more = get_okx_candles(inst_id, bar, min(needed - 200, 200))
                all_rows.extend(more)
        except Exception as e:
            logger.exception("Failed to fetch candles for %s %s: %s", inst_id, tf, e)
            raise

        # transform OKX candle format -> DataFrame
        # OKX: each candle: [ts, open, high, low, close, vol] where ts is milliseconds or seconds? OKX v5 returns ISO? Usually epoch ms
        # From experience: OKX returns string timestamp in milliseconds.
        df_rows = []
        for c in reversed(all_rows):  # reverse so oldest first
            try:
                ts = int(c[0])
                # if ts looks like ms ( > 1e12 ), convert to seconds
                if ts > 3_000_000_000:
                    ts = ts // 1000
                o = float(c[1])
                h = float(c[2])
                l = float(c[3])
                cl = float(c[4])
                vol = float(c[5])
                df_rows.append([ts, o, h, l, cl, vol])
            except Exception:
                # skip malformed
                continue
        df = pd.DataFrame(df_rows, columns=["time", "open", "high", "low", "close", "volume"])
        # ensure sorted by time ascending
        df = df.sort_values("time").reset_index(drop=True)
        results[tf] = df
        # small polite pause to avoid hammering API
        time.sleep(0.15)
    return results

# -----------------------------
# Build dfs with indicators
# -----------------------------
def build_dfs():
    """
    Fetch candles for all required TFs and compute indicators for each dataframe
    """
    dfs = fetch_candles_all_tf(INSTRUMENT_ID, TIMEFRAMES, CANDLES_LIMIT)
    # compute indicators
    for tf, df in dfs.items():
        try:
            dfs[tf] = add_all_indicators(df.copy())
        except Exception as e:
            logger.exception("add_all_indicators failed for %s: %s", tf, e)
            # still keep original DF so checks can handle missing values
            dfs[tf] = df
    return dfs

# -----------------------------
# State helpers
# -----------------------------
def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        logger.exception("Failed to load state")
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        logger.exception("Failed to save state")

# -----------------------------
# Bot loop
# -----------------------------
def bot_loop():
    logger.info("🚀 EMA-Bot (prod) started. Interval %s sec. TFs: %s", BOT_INTERVAL_SEC, TIMEFRAMES)
    state = load_state()
    last_start_key = state.get("last_start_key")
    last_signal = (state.get("last_direction"), state.get("last_signal_ts"))

    while True:
        try:
            dfs = build_dfs()
        except Exception as e:
            logger.exception("Failed to build dfs: %s", e)
            time.sleep(BOT_INTERVAL_SEC)
            continue

        # run centralized checks (bot.checker.run_checks expects df_by_tf mapping)
        try:
            ok, result = run_checks(dfs)
        except Exception as e:
            logger.exception("run_checks error: %s\n%s", e, traceback.format_exc())
            # save last_snapshot with error
            s = {"error": str(e)}
            state["last_snapshot"] = s
            save_state(state)
            time.sleep(BOT_INTERVAL_SEC)
            continue

        # pretty log per condition (run_checks returns dict with "by_cond")
        try:
            by_cond = result.get("by_cond", {})
            for k in sorted(by_cond.keys(), key=lambda x: int(x) if str(x).isdigit() else 999):
                ent = by_cond[k]
                ok_flag = ent.get("ok", False)
                info = ent.get("info", {}) or ent.get("value", {}) or {}
                reason = ""
                if isinstance(info, dict):
                    reason = info.get("reason") or info.get("note") or ""
                logger.info("[P%s] %s reason=%s values=%s", k, "✅" if ok_flag else "❌", reason, json.dumps(info, ensure_ascii=False))
            logger.info("SUMMARY: %s | impulse_tf=%s | direction=%s", result.get("summary"), result.get("impulse_tf"), result.get("direction"))
        except Exception:
            logger.exception("Failed pretty log result")

        # persist snapshot
        state["last_snapshot"] = result
        save_state(state)

        # determine start ts if present to make keys unique
        start_idx = result.get("start_index")
        df5 = dfs.get("5m")
        start_ts = None
        if start_idx is not None and df5 is not None and len(df5) > start_idx:
            try:
                start_ts = int(df5["time"].iloc[start_idx])
            except Exception:
                start_ts = int(time.time())

        # send debug Telegram report on first time we see this start candle
        if start_ts is not None:
            start_key = f"{result.get('direction')}|{start_ts}"
            if start_key != last_start_key:
                try:
                    price = None
                    try:
                        price = float(dfs["5m"]["close"].iloc[-1])
                    except Exception:
                        price = None
                    msg = format_message(result, price or 0.0, dfs)
                    sent = send_telegram_message(msg)
                    logger.info("Telegram debug report sent: %s", sent)
                except Exception:
                    logger.exception("Telegram debug error")
                last_start_key = start_key
                state["last_start_key"] = last_start_key
                save_state(state)

        # final signal notification uniqueness & sending
        if ok:
            # create signal key
            signal_key = (result.get("direction"), start_ts)
            if signal_key != last_signal:
                try:
                    price = None
                    try:
                        price = float(dfs["5m"]["close"].iloc[-1])
                    except Exception:
                        price = None
                    msg = format_message(result, price or 0.0, dfs)
                    send_telegram_message(msg)
                    logger.info("✅ Final signal sent via Telegram (direction=%s start_ts=%s)", result.get("direction"), start_ts)
                except Exception:
                    logger.exception("Failed to send final telegram")
                last_signal = signal_key
                state["last_signal_ts"] = start_ts
                state["last_direction"] = result.get("direction")
                save_state(state)
            else:
                logger.info("Duplicate final signal suppressed")
        else:
            logger.info("No final signal this cycle: %s", result.get("summary"))

        time.sleep(BOT_INTERVAL_SEC)

# -----------------------------
# HTTP endpoints
# -----------------------------
@app.route("/")
def home():
    return "✅ EMA-Bot (production) active."

@app.route("/test")
def test_telegram():
    ok = send_telegram_message("✅ EMA-Bot (prod) test message.")
    return f"Telegram test sent: {ok}"

@app.route("/status")
def status():
    state = load_state()
    return jsonify({
        "last_signal_ts": state.get("last_signal_ts", "-"),
        "last_direction": state.get("last_direction", "-"),
        "last_start_key": state.get("last_start_key"),
        "last_snapshot": state.get("last_snapshot", {})
    })

@app.route("/debug/trigger", methods=["POST"])
def debug_trigger():
    allow = os.getenv("ALLOW_DEBUG_TRIGGER", "0") == "1"
    if not allow:
        return "disabled", 403
    try:
        dfs = build_dfs()
        ok, result = run_checks(dfs)
        # store snapshot
        state = load_state()
        state["last_snapshot"] = result
        save_state(state)
        return jsonify({"ok": ok, "result": result})
    except Exception as e:
        logger.exception("debug trigger failure: %s", e)
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Start service
# -----------------------------
if __name__ == "__main__":
    logger.info("Starting EMA-Bot (production) main")
    t = Thread(target=bot_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
