
import os
import json
import time
import threading
import logging
from datetime import datetime
from flask import Flask

from bot.config import (
    TIMEFRAMES, STATE_FILE, LOG_FILE, BOT_INTERVAL_SEC,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
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
    last_signal_ts = state.get("last_signal_ts", 0)
    last_direction = state.get("last_direction", None)

    while True:
        try:
            dfs = build_dfs()
            ok, result = run_checks(dfs)
            price = get_live_price()

            if ok:
                # уникальность по «стартовой свече» (timestamp 5m)
                start_idx = result["start_index"]
                ts = int(dfs["5m"]["time"].iloc[start_idx])
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
                logging.info("ℹ️ Условия не выполнены: %s", result.get("reason", "см. детали"))

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
    return f"📊 last_signal_ts: {state.get('last_signal_ts','-')}, last_direction: {state.get('last_direction','-')}"

# background
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
