import os
import time
import json
import threading
import requests
import pandas as pd
from flask import Flask

app = Flask(__name__)
STATE_FILE = "ema_state.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        print("❌ Ошибка отправки Telegram-сообщения:", e)

def get_price_history():
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "interval": "5",  # 5-minute candles
        "limit": 100
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    # Возвращаем список цен закрытия свечей
    return [float(item[4]) for item in data["result"]["list"]]  # item[4] = close

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def check_ema_cross():
    try:
        closes = get_price_history()
    except Exception as e:
        print("❌ Ошибка при получении истории свечей:", e)
        return

    if len(closes) < 21:
        print(f"Недостаточно данных для EMA (только {len(closes)} точек)")
        return

    df = pd.DataFrame(closes, columns=["close"])
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

    print(f"[DEBUG] EMA10: {last_10:.2f}, EMA21: {last_21:.2f}")
    print(f"[DEBUG] Предыдущее пересечение: {last_cross}, Новое: {crossed}")

    if crossed and crossed != last_cross:
        emoji = "▲" if crossed == "up" else "▼"
        send_telegram_message(f"📊 EMA пересечение: {crossed.upper()} {emoji}")
        state["cross"] = crossed
        save_state(state)
    else:
        print("Нет нового пересечения.")

def run_bot():
    print("Запуск EMA бота с Bybit (5m TF)...")
    while True:
        try:
            check_ema_cross()
        except Exception as e:
            print("❌ Ошибка в боте:", e)
        time.sleep(300)  # каждые 5 минут

@app.route("/")
def home():
    return "✅ EMA-бот активен (Bybit Perpetual BTCUSDT, 5m)."

@app.route("/test")
def test_telegram():
    send_telegram_message("✅ Тестовое уведомление от EMA-бота.")
    return "Тестовое уведомление отправлено!"

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
