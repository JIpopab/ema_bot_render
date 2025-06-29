import os
import time
import json
import requests
import pandas as pd
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
STATE_FILE = "ema_state.json"
price_history = []

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        print("❌ Ошибка отправки Telegram-сообщения:", e, flush=True)

def get_bybit_futures_price():
    url = "https://api.bybit.com/v5/market/tickers"
    params = {
        "category": "linear",
        "symbol": "BTCUSDT"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return float(data["result"]["list"][0]["lastPrice"])

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def check_ema_cross():
    global price_history
    try:
        price = get_bybit_futures_price()
        price_history.append(price)
        if len(price_history) > 100:
            price_history = price_history[-100:]

        if len(price_history) >= 21:
            df = pd.DataFrame(price_history, columns=["close"])
            ema10 = df["close"].ewm(span=10, adjust=False).mean()
            ema21 = df["close"].ewm(span=21, adjust=False).mean()

            prev_10 = ema10.iloc[-2]
            prev_21 = ema21.iloc[-2]
            last_10 = ema10.iloc[-1]
            last_21 = ema21.iloc[-1]

            crossed = None
            if prev_10 < prev_21 and last_10 > last_21:
                crossed = "up"
            elif prev_10 > prev_21 and last_10 < last_21:
                crossed = "down"

            state = load_state()
            last_cross = state.get("cross")

            print(f"[DEBUG] Цена: {price:.2f}, EMA10: {last_10:.2f}, EMA21: {last_21:.2f}", flush=True)
            print(f"[DEBUG] Предыдущее пересечение: {last_cross}, Новое: {crossed}", flush=True)

            if crossed and crossed != last_cross:
                emoji = "▲" if crossed == "up" else "▼"
                send_telegram_message(f"📊 EMA пересечение: {crossed.upper()} {emoji}")
                state["cross"] = crossed
                save_state(state)
            else:
                print("Нет нового пересечения.", flush=True)
        else:
            print(f"Собрано цен: {len(price_history)} / 21", flush=True)
    except Exception as e:
        print("❌ Ошибка в check_ema_cross:", e, flush=True)

@app.route("/")
def home():
    return "✅ EMA-бот активен (Bybit Perpetual BTCUSDT)."

@app.route("/test")
def test_telegram():
    send_telegram_message("✅ Тестовое уведомление от EMA-бота.")
    return "Тестовое уведомление отправлено!"

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_ema_cross, 'interval', minutes=5)
    scheduler.start()

    import atexit
    atexit.register(lambda: scheduler.shutdown())

    print("Запуск EMA бота с Bybit...", flush=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), use_reloader=False)
