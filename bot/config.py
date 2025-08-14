
# bot/config.py

# === Exchange & symbol ===
EXCHANGE = "OKX"
INSTRUMENT_ID = "BTC-USDT-SWAP"

# === Timeframes we use ===
TIMEFRAMES = ["5m", "15m", "30m", "1H", "2H"]

# === Indicator parameters ===
# EMA
EMA_FAST = 5
EMA_MED  = 10
EMA_SLOW = 21
EMA50    = 50
EMA200   = 200

# MACD (strength & direction): 9,22,6
MACD_FAST   = 9
MACD_SLOW   = 22
MACD_SIGNAL = 6

# RSI strength: 21,6,9
RSI21 = 21
RSI6  = 6
RSI9  = 9

# KDJ: 9,3,3
KDJ_N = 9
KDJ_K = 3
KDJ_D = 3

# Stochastic RSI: 9,8,3,3 (rsi_len, stoch_len, k, d)
SRSI_RSI_LEN   = 9
SRSI_STOCH_LEN = 8
SRSI_K = 3
SRSI_D = 3

# Volume MAs for tolerance on previous trend
VOL_MA1 = 5
VOL_MA2 = 10

# === Logic toggles ===
# Enable which conditions (1..11)
ENABLED_CONDITIONS = [1,2,3,4,5,6,7,8,9,10,11]

# Strict mode = require ALL enabled conditions to be True simultaneously.
STRICT_MODE = True  # if False, uses branching logic (8&9) OR (10&11)

# How many candles to download per TF
CANDLES_LIMIT = 300

# Bot loop interval seconds
BOT_INTERVAL_SEC = 60

# State file & log file names
STATE_FILE = "ema_state.json"
LOG_FILE   = "ema_bot.log"

# Telegram
import os
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
