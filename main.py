import os
import requests
import pandas as pd
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Telegram credentials from environment
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Global state to track previous EMA values
last_ema10 = None
last_ema21 = None

current_price = None
current_ema10 = None
current_ema21 = None
last_signal = None

def send_telegram_message(text):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text
        }
        requests.post(url, data=payload)

def fetch_and_check_ema():
    global last_ema10, last_ema21
    global current_price, current_ema10, current_ema21, last_signal

    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "interval": "5",
        "limit": 50
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "result" not in data or "list" not in data["result"]:
        print("❌ Ошибка получения данных")
        return

    df = pd.DataFrame(data["result"]["list"])
    df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
    df["close"] = pd.to_numeric(df["close"])

    # Calculate EMAs
    df["ema10"] = df["close"].ewm(span=10).mean()
    df["ema21"] = df["close"].ewm(span=21).mean()

    current_price = df["close"].iloc[-1]
    current_ema10 = df["ema10"].iloc[-1]
    current_ema21 = df["ema21"].iloc[-1]

    prev_ema10 = df["ema10"].iloc[-2]
    prev_ema21 = df["ema21"].iloc[-2]

    signal = None
    if prev_ema10 < prev_ema21 and current_ema10 > current_ema21:
        signal = "📈 EMA10 пересек EMA21 снизу вверх — возможный сигнал на покупку!"
    elif prev_ema10 > prev_ema21 and current_ema10 < current_ema21:
        signal = "📉 EMA10 пересек EMA21 сверху вниз — возможный сигнал на продажу!"

    if signal and signal != last_signal:
        send_telegram_message(signal)
        last_signal = signal

    print(f"[OK] Цена: {current_price}, EMA10: {current_ema10}, EMA21: {current_ema21}")

@app.route("/")
def home():
    return f"""
    <h1>📊 EMA Бот</h1>
    <p>Текущая цена BTCUSDT: <strong>{current_price}</strong></p>
    <p>EMA10: <strong>{current_ema10}</strong></p>
    <p>EMA21: <strong>{current_ema21}</strong></p>
    <p>Последний сигнал: <strong>{last_signal}</strong></p>
    """

@app.route("/test")
def test():
    send_telegram_message("✅ Тестовое сообщение от EMA бота.")
    return "Сообщение отправлено в Telegram."

if __name__ == "__main__":
    print("🚀 Запуск EMA бота с Bybit...")
    fetch_and_check_ema()

    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_check_ema, "interval", minutes=5)
    scheduler.start()

    app.run(host="0.0.0.0", port=10000)
