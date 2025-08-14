# bot/config.py
# Конфигурация + все допуски (tolerances) для условий 1..11.
# Поменяй значения при желании — они вынесены в константы для удобного тюнинга.

import os

# === Exchange & symbol ===
EXCHANGE = "OKX"
INSTRUMENT_ID = "BTC-USDT-SWAP"

# === Timeframes we use (must match fetcher and conditions) ===
# Note: capitalization must match other modules that use TIMEFRAMES
TIMEFRAMES = ["5m", "15m", "30m", "1H", "2H"]

# === Indicator parameters (as you specified) ===
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

# === Runtime & I/O ===
# How many candles to download per TF (increase if you need longer history)
CANDLES_LIMIT = 300

# Bot loop interval seconds
BOT_INTERVAL_SEC = int(os.getenv("BOT_INTERVAL_SEC", "60"))

# State file & log file names
STATE_FILE = os.getenv("STATE_FILE", "ema_state.json")
LOG_FILE   = os.getenv("LOG_FILE", "ema_bot.log")

# Telegram (from env)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

# Debug trigger (optional)
ALLOW_DEBUG_TRIGGER = os.getenv("ALLOW_DEBUG_TRIGGER", "0") == "1"

# === Logic toggles ===
# Enable which conditions (1..11)
ENABLED_CONDITIONS = [1,2,3,4,5,6,7,8,9,10,11]

# Strict mode = require ALL enabled conditions to be True simultaneously.
# If False -> branching logic: 1..7 mandatory, then (8&9) OR (10&11).
STRICT_MODE = os.getenv("STRICT_MODE", "False").lower() in ("1", "true", "yes")

# === OKX / networking ===
OKX_API_BASE = "https://www.okx.com"
# request timeouts
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10.0"))

# polite pause between OKX requests (seconds)
OKX_REQUEST_PAUSE = float(os.getenv("OKX_REQUEST_PAUSE", "0.15"))

# === TOLERANCES / THRESHOLDS (explicitly mapped to spec) ===
# -------------------------
# 1) EMA timing (5m)
EMA10_AFTER_EMA5_MAX_BARS = 4   # "не позднее четырех свеч"

# -------------------------
# 2) MACD (5m)
MACD_LAST_CROSS_MAX_BARS = 11   # последнее пересечение не позднее 11 свеч
MACD_DIF_DEA_MAX_DIFF = 70.0    # |DIF - DEA| <= 70 после пересечения

# -------------------------
# 3) Momentum changes tolerance (5m)
P3_TOL = 5.0                    # погрешность 5 ед. между t-2 и t
P3_MAX_ALLOWED_FAILS = 1        # допускается единичное расхождение среди параметров

# -------------------------
# 4) KDJ & RSI on 5m (free space)
KDJ_JD_DIFF_MIN = 6.0           # (J - D) >= 6 для long (или D - J >=6 для short)
RSI_P4_TOL = 5.0                # RSI tolerance for p4 (3-candle check)

# -------------------------
# 5) RSI6/RSI9/RSI21 on start (5m)
RSI6_LONG_UPPER_LIMIT = 70.0    # preferably RSI6 < 70 for long
RSI6_SHORT_LOWER_LIMIT = 30.0   # preferably RSI6 > 30 for short
RSI6_RSI9_DIFF_MIN = 4.0        # when RSI6>70 then rsi6-rsi9 >=4; or rsi9-rsi6 >=4 for short
RSI21_MAX_LONG = 70.0
RSI21_MIN_SHORT = 30.0

# -------------------------
# 6) 15m checks (stoch RSI / RSI ordering / KDJ / DEA)
# Stoch RSI tolerances
SRSI_KD_TOL_LONG = 3.0          # K >= D - tol (long)
SRSI_KD_TOL_SHORT = 2.0         # K <= D + tol (short)
SRSI_D_MAX_LONG = 82.0
SRSI_D_MIN_SHORT = 19.0

# RSI tolerances on 15m
RSI_15_TOL = 6.5                # tolerance for rsi6 dynamics
# required ordering on start candle (15m)
# no numeric constant here — checks in code compare rsi6>rsi9>rsi21 etc.

# KDJ (15m) tolerances
KDJ_15_TOL = 5.0                # allowed per-parameter drift (i-2 -> i)
KDJ_15_D_THRESHOLD = 60.0       # prefer D < 60 for long; if D>60 then require (J-D)>=20
KDJ_15_D_ALT_THRESHOLD = 40.0   # for short branch
KDJ_15_J_UPPER_LIMIT = 100.0    # J<100 generally expected on long

# MACD DEA (15m)
DEA_LIMIT_LONG = 150.0
DEA_LIMIT_SHORT = -150.0

# -------------------------
# 7) 15m: RSI6/RSI9 free space on potential start (same logic as p5 but on 15m)
RSI6_LIMIT_15_LONG = 70.0
RSI6_LIMIT_15_SHORT = 30.0
RSI6_RSI9_MIN_DIFF_15 = 4.0
RSI21_LIMIT_15_LONG = 70.0
RSI21_LIMIT_15_SHORT = 30.0

# -------------------------
# 8) 30m TF specifics (p8.1 - p8.3)
KDJ_30_J_DIFF_MIN = 20.0        # J(start) - J(prev) > 20 for long (or reverse for short)
KDJ_30_CROSS_MAX_BARS = 2       # J through D should have happened not later than 2 bars ago (30m)
MACD_PREV_TREND_MIN_BARS_30 = 4 # previous trend must have at least these macd bars
MACD_PREV_TREND_MIN_VOL_MA = VOL_MA2  # use vol MA to filter small-volume candles (already in code)
# K/D/K thresholds to validate previous trend (min/max)
K_30_LONG_MAX = 33.0
D_30_LONG_MAX = 43.0
K_30_LONG_MIN = 14.0
K_30_SHORT_MIN = 82.0
D_30_SHORT_MIN = 73.0
K_30_SHORT_MAX = 98.0

# 8.2 RSI thresholds on 30m
RSI6_RSI9_RSI21_DIFF_MIN_30 = 10.0
RSI30_PREV_TREND_RSI6_MAX_LONG = 45.0
RSI30_PREV_TREND_RSI9_MAX_LONG = 50.0
RSI30_PREV_TREND_RSI21_MAX_LONG = 60.0
RSI30_PREV_TREND_RSI6_MIN_SHORT = 65.0
RSI30_PREV_TREND_RSI9_MIN_SHORT = 60.0
RSI30_PREV_TREND_RSI21_MIN_SHORT = 52.0

# 8.3 max allowable difference in timing of RSI & KDJ crossings (30m)
MAX_CROSS_TIMING_DIFF_30 = 2

# -------------------------
# 9) 1H TF specifics (p9.1..p9.4)
# max allowed bars back for crossings on 1H
MAX_CROSS_BACK_1H = 3
KDJ_1H_TOL = 5.0                # j>k>d at start with 5 unit tolerance checks
RSI_1H_ORDER_STRICT = True      # ordering on rsi6>rsi9>rsi21 must be strict (no tolerance)
STOCHRSI_1H_KD_TOL_LONG = 3.0
STOCHRSI_1H_KD_TOL_SHORT = 2.0
STOCHRSI_1H_D_MAX_LONG = 82.0
STOCHRSI_1H_D_MIN_SHORT = 19.0
# allowed timing mismatch among 1H subchecks
MAX_CROSS_TIMING_DIFF_1H = 2

# -------------------------
# 10) Transfer logic (apply p8->1H or p9->2H)
# No numeric constants here: handled by cond_10 implementation which references the p8/p9 thresholds above.

# -------------------------
# 11) Weakened 30m conditions used when impulse seen on 1H/2H (p11)
# 11.1 RSI relaxed thresholds on 30m start
RSI11_A_RSI21_MAX_1 = 63.0
RSI11_A_RSI21_MAX_2 = 58.0
RSI11_RSI6_RSI9_EQ_TOL = 2.0    # rsi6 == rsi9 tolerance
RSI11_RSI9_RSI21_EQ_TOL = 2.5

RSI11_B_RSI21_MIN_1 = 37.0
RSI11_B_RSI9_EQ_TOL = 1.0
RSI11_B_RSI9_EQ_TOL_ALT = 6.0

# 11.2 KDJ relaxed tolerances
KDJ11_LONG_D_MAX = 82.0
KDJ11_LONG_JK_EQ_TOL = 10.0
KDJ11_LONG_KD_EQ_TOL = 4.0
KDJ11_SHORT_D_MIN = 30.0
KDJ11_SHORT_JK_EQ_TOL = 8.0
KDJ11_SHORT_KD_EQ_TOL = 5.0
KDJ11_RETROSPECTIVE_BARS = 12   # check J<K<D condition in previous bars

# 11.3 Stoch RSI relaxed tolerances
SRSI11_LONG_D_MAX = 89.5
SRSI11_LONG_KD_TOL = 7.0
SRSI11_SHORT_D_MIN = 23.0
SRSI11_SHORT_KD_TOL = 8.0

# -------------------------
# Safety / limits
# Max requests per run to avoid accidental DoS
MAX_OKX_CALLS_PER_LOOP = 10

# -------------------------
# End of config
