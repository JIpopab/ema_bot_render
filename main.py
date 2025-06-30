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


def get_candlestick_data():
    url = "https://www.okx.com/api/v5/market/candles"
    params = {
        "instId": "BTC-USDT-SWAP",
        "bar": "5m",
        "limit": 100
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data.get("code") != "0":
        raise Exception(f"OKX API error: {data.get('msg')}")

    closes = [float(candle[4]) for candle in reversed(data["data"])]  # ⬅️ reverse to chronological order
    return closes


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def check_ema_cross():
    closes = get_candlestick_data()

    if len(closes) >= 21:
        df = pd.DataFrame(closes, columns=["close"])
        ema10 = df["close"].ewm(span=10, adjust=False).mean()
        ema21 = df["close"].ewm(span=21, adjust=False).mean()

        prev_10 = ema10.iloc[-2]
        prev_21 = ema21.iloc[-2]
        last_10 = ema10.iloc[-1]
        last_21 = ema21.iloc[-1]
        last_price = closes[-1]

        crossed = None
        if prev_10 < prev_21 and last_10 > last_21:
            crossed = "up"
        elif prev_10 > prev_21 and last_10 < last_21:
            crossed = "down"

        state = load_state()
        last_cross = state.get("cross")

        now = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n🕒 [{now}]")
        print(f"📈 Цена: {last_price:.2f}")
        print(f"EMA10: {last_10:.2f}, EMA21: {last_21:.2f}")
        print(f"🔄 Пересечение: {'↑ up' if crossed == 'up' else '↓ down' if crossed == 'down' else '– нет'}")
        print(f"💾 Сохранённое предыдущее: {last_cross}")

        if crossed and crossed != last_cross:
            emoji = "▲" if crossed == "up" else "▼"
            send_telegram_message(f"📊 EMA пересечение: {crossed.upper()} {emoji}")
            state["cross"] = crossed
            save_state(state)
        else:
            print("ℹ️ Нового пересечения нет.")
    else:
        print(f"⚠️ Недостаточно данных: {len(closes)} / 21")


def run_bot():
    print("🚀 EMA-бот запущен. Ожидаем первого срабатывания...")

    while True:
        try:
            check_ema_cross()
        except Exception as e:
            print("❌ Ошибка в боте:", e)

        # ⏱ Ждать до ближайшего ровного 5-минутного таймстемпа
        now = time.localtime()
        sleep_seconds = (300 - (now.tm_min % 5) * 60 - now.tm_sec)
        next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + sleep_seconds))
        print(f"⏳ Следующая проверка в {next_run} (через {sleep_seconds} секунд)\n")
        time.sleep(sleep_seconds)


# ✅ Запуск бота на старте импорта (нужно для Render)
threading.Thread(target=run_bot, daemon=True).start()


# 🌐 Flask API
@app.route("/")
def home():
    return "✅ EMA-бот активен (OKX Perpetual BTCUSDT, 5m TF)."


@app.route("/test")
def test_telegram():
    send_telegram_message("✅ Тестовое уведомление от EMA-бота.")
    return "Тестовое уведомление отправлено!"
