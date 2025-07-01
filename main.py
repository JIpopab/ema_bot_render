import os
import json
import time
import threading
import logging
import requests
import pandas as pd
from datetime import datetime
from flask import Flask

app = Flask(__name__)
STATE_FILE = "ema_state.json"
LOG_FILE = "ema_bot.log"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 🔧 Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        logging.info(f"✅ Отправлено в Telegram: {text}")
    except Exception as e:
        logging.error(f"❌ Ошибка отправки Telegram-сообщения: {e}")

def get_candlestick_data():
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": "BTC-USDT-SWAP", "bar": "5m", "limit": 100}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data.get("code") != "0":
        raise Exception(f"OKX API error: {data.get('msg')}")

    closes = [float(candle[4]) for candle in data["data"]]
    closes.reverse()
    return closes

def get_live_price():
    url = "https://www.okx.com/api/v5/market/ticker"
    params = {"instId": "BTC-USDT-SWAP"}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data.get("code") != "0":
        raise Exception(f"OKX API ticker error: {data.get('msg')}")

    return float(data["data"][0]["last"])

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def check_ema_realtime():
    closes = get_candlestick_data()
    live_price = get_live_price()

    closes[-1] = live_price

    if len(closes) >= 21:
        df = pd.DataFrame(closes, columns=["close"])
        ema10 = df["close"].ewm(span=10, adjust=False).mean()
        ema21 = df["close"].ewm(span=21, adjust=False).mean()

        last_10 = ema10.iloc[-1]
        last_21 = ema21.iloc[-1]

        state = load_state()
        last_event = state.get("event")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"🕒 [{now}] Цена: {live_price:.2f} | EMA10: {last_10:.2f}, EMA21: {last_21:.2f}")

        crossed = None
        if last_10 > last_21:
            crossed = "up"
        elif last_10 < last_21:
            crossed = "down"
        elif abs(last_10 - last_21) < 0.5:
            crossed = "touch"

        logging.info(f"🔄 Обнаружено событие: {crossed}")

        price_str = f"{live_price:,.2f} $"

        if crossed == "touch":
            send_telegram_message(f"⚡ EMA касание: EMA10 ≈ EMA21 по цене {price_str}")
            # не записываем в state, чтобы касания могли повторяться
        elif crossed != last_event:
            if crossed == "up":
                send_telegram_message(f"📈 EMA пересечение: ВВЕРХ ▲ по цене {price_str}")
            elif crossed == "down":
                send_telegram_message(f"📉 EMA пересечение: ВНИЗ ▼ по цене {price_str}")
            state["event"] = crossed
            save_state(state)
        else:
            logging.info("ℹ️ Нет изменений EMA. Просто наблюдаем.")
    else:
        logging.warning(f"⚠️ Недостаточно данных: {len(closes)} / 21")

def run_bot():
    logging.info("🚀 EMA-бот запущен. Мониторим каждые 60 секунд...")
    while True:
        try:
            check_ema_realtime()
        except Exception as e:
            logging.error(f"❌ Ошибка в боте: {e}")
        logging.info("⏳ Следующая проверка через 1 минуту...\n")
        time.sleep(60)

# 🌐 Flask routes
@app.route("/")
def home():
    return "✅ EMA-бот активен (OKX BTCUSDT, 5m TF, реальное время)."

@app.route("/test")
def test_telegram():
    send_telegram_message("✅ Тестовое уведомление от EMA-бота (реальное время).")
    return "Тестовое уведомление отправлено!"

@app.route("/status")
def status():
    state = load_state()
    return f"📊 Последнее EMA-событие: {state.get('event', 'неизвестно')}"

# 🧠 Фоновый запуск (для Render и других хостингов)
threading.Thread(target=run_bot, daemon=True).start()

# ✅ Flask app run (с поддержкой PORT из окружения)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)