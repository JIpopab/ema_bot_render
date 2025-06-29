import os
import time
import json
import threading
import requests
import pandas as pd
from flask import Flask

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
        print("❌ Ошибка отправки Telegram-сообщения:", e)

def fetch_historical_prices(days=3):
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": days}
    headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        prices = data.get("prices", [])
        filtered_prices = []
        last_time = 0
        for ts, price in prices:
            t_min = ts // (5 * 60 * 1000)
            if t_min != last_time:
                filtered_prices.append(price)
                last_time = t_min
        return filtered_prices
    except Exception as e:
        print("❌ Ошибка загрузки истории:", e)
        return []

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def fetch_current_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "bitcoin", "vs_currencies": "usd"}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data["bitcoin"]["usd"]
    except Exception as e:
        print("❌ Ошибка при получении текущей цены:", e)
        return None

def check_ema_cross():
    global price_history
    price = fetch_current_price()
    if price is None:
        return
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

        print(f"[DEBUG] Цена: {price:.2f}, EMA10: {last_10:.2f}, EMA21: {last_21:.2f}")
        print(f"[DEBUG] Предыдущее пересечение: {last_cross}, Новое: {crossed}")

        if crossed and crossed != last_cross:
            emoji = "▲" if crossed == "up" else "▼"
            send_telegram_message(f"📊 EMA пересечение: {crossed.upper()} {emoji}")
            state["cross"] = crossed
            save_state(state)
        else:
            print("Нет нового пересечения.")
    else:
        print(f"Собрано цен: {len(price_history)} / 21")

def run_bot():
    global price_history
    print("Загружаем исторические цены...")
    price_history = fetch_historical_prices(days=3)
    print(f"Загружено {len(price_history)} исторических цен.")

    while True:
        try:
            check_ema_cross()
        except Exception as e:
            print("❌ Ошибка в боте:", e)
        time.sleep(300)

@app.route("/")
def home():
    return "✅ CoinGecko EMA бот активен."

@app.route("/test")
def test_telegram():
    send_telegram_message("✅ Тестовое уведомление от EMA-бота.")
    return "Тестовое уведомление отправлено!"

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
