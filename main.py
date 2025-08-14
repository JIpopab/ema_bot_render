# main.py (updated)
import os
import json
import time
import threading
import logging
from flask import Flask, jsonify

from bot.config import (
    TIMEFRAMES, STATE_FILE, LOG_FILE, BOT_INTERVAL_SEC,
)
from bot.data import get_all_timeframes, get_live_price
from bot.indicators import add_all_indicators
from bot.checker import run_checks
from bot.notifier import send_telegram_message, format_message

app = Flask(__name__)

# logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def build_dfs():
    raw = get_all_timeframes(TIMEFRAMES)
    dfs = {}
    for tf, df in raw.items():
        dfs[tf] = add_all_indicators(df)
    return dfs

def bot_loop():
    logging.info("🚀 Бот запущен. Мониторинг каждые %s сек.", BOT_INTERVAL_SEC)
    state = load_state()
    last_start_key = state.get("last_start_key")
    last_signal_ts = state.get("last_signal_ts", 0)
    last_direction = state.get("last_direction", None)

    while True:
        try:
            dfs = build_dfs()
            ok, result = run_checks(dfs)
            price = get_live_price()

            # Detailed logging per condition
            for cid, entry in sorted(result.get("by_cond", {}).items()):
                ok_flag = entry.get("ok", False)
                info = entry.get("info", {})
                if ok_flag:
                    logging.info(f"[P{cid}] ✅ {info}")
                else:
                    logging.info(f"[P{cid}] ❌ {info}")

            # Save snapshot for /status
            try:
                state['last_snapshot'] = result
                save_state(state)
            except Exception:
                logging.exception("can't save snapshot")

            # send telegram when we detect a new start candle evaluation (cond1 exists)
            start_idx = result.get("start_index")
            if start_idx is not None:
                # unique key by direction+start ts
                try:
                    ts = int(dfs["5m"]["time"].iloc[start_idx])
                except Exception:
                    ts = start_idx
                start_key = f"{result.get('direction')}|{ts}"
                if start_key != last_start_key:
                    # send a report (for debugging) to Telegram
                    msg = format_message(result, price, dfs)
                    sent = send_telegram_message(msg)
                    logging.info("Telegram report sent for start candle: %s", sent)
                    last_start_key = start_key
                    state['last_start_key'] = last_start_key
                    save_state(state)

            if ok:
                # unique by start ts & direction => send final signal (avoid duplicates)
                start_idx = result["start_index"]
                try:
                    ts = int(dfs["5m"]["time"].iloc[start_idx])
                except Exception:
                    ts = start_idx
                if ts != last_signal_ts or result["direction"] != last_direction:
                    msg = format_message(result, price, dfs)
                    send_telegram_message(msg)
                    last_signal_ts = ts
                    last_direction = result["direction"]
                    state["last_signal_ts"] = ts
                    state["last_direction"] = last_direction
                    save_state(state)
                    logging.info("✅ Сигнал отправлен. dir=%s ts=%s", last_direction, ts)
                else:
                    logging.info("ℹ️ Сигнал уже отправлялся для этой стартовой свечи.")
            else:
                logging.info("ℹ️ Полный набор условий не выполнен: %s", result.get("summary"))

        except Exception as e:
            logging.exception("❌ Ошибка в боте: %s", e)

        time.sleep(BOT_INTERVAL_SEC)

@app.route("/")
def home():
    return "✅ EMA-бот v2 активен (OKX BTCUSDT)."

@app.route("/test")
def test_telegram():
    send_telegram_message("✅ Тестовое уведомление от EMA-бота v2.")
    return "Тестовое уведомление отправлено!"

@app.route("/status")
def status():
    state = load_state()
    last_signal_ts = state.get('last_signal_ts', '-')
    last_direction = state.get('last_direction', '-')
    last_start_key = state.get('last_start_key', None)
    snapshot = state.get('last_snapshot', {})
    return jsonify({
        'last_signal_ts': last_signal_ts,
        'last_direction': last_direction,
        'last_start_key': last_start_key,
        'last_snapshot': snapshot
    })

# background
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
