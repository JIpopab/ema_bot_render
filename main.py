import os
import pandas as pd
import requests
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

app = Flask(__name__)
scheduler = BackgroundScheduler()
last_cross = None  # отслеживание последнего сигнала

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            print("❌ Ошибка Telegram:", r.text)
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def fetch_and_check_ema():
    global last_cross

    print("🔄 Получение данных с Bybit...")
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "interval": "5",
        "limit": 100
    }
    headers = {
        "User-Agent": "EMA-Bot/1.0"
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        if not response.text:
            print("⚠️ Пустой ответ от Bybit")
            return

        data = response.json()
        if "result" not in data or "list" not in data["result"]:
            print("⚠️ Странный ответ:", data)
            return

        candles = data["result"]["list"]
        closes = [float(c[4]) for c in candles][::-1]

        price = closes[-1]
        ema10 = pd.Series(closes).ewm(span=10).mean().iloc[-1]
        ema21 = pd.Series(closes).ewm(span=21).mean().iloc[-1]

        print(f"📊 Цена: {price:.2f} | EMA10: {ema10:.2f} | EMA21: {ema21:.2f}")

        if ema10 > ema21 and last_cross != "up":
            send_telegram_message(f"🟢 EMA10 ({ema10:.2f}) пересек EMA21 ({ema21:.2f}) вверх\nЦена: {price:.2f}")
            last_cross = "up"
        elif ema10 < ema21 and last_cross != "down":
            send_telegram_message(f"🔴 EMA10 ({ema10:.2f}) пересек EMA21 ({ema21:.2f}) вниз\nЦена: {price:.2f}")
            last_cross = "down"
        else:
            print("⏸️ Нет нового пересечения")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

@app.route("/")
def index():
    return "✅ EMA Bot работает"

# стартуем задачу каждую минуту
scheduler.add_job(fetch_and_check_ema, "interval", minutes=1)
scheduler.start()

if __name__ == "__main__":
    print("🚀 Запуск EMA бота с Bybit...")
    fetch_and_check_ema()  # первый запуск вручную
    app.run(host="0.0.0.0", port=5000)
