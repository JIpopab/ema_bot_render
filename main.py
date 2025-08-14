# main.py
# Главный цикл — теперь явно вызывает cond_1..cond_11 и собирает полный snapshot.
# Замените существующий main.py этим кодом.

import os
import json
import time
import logging
import traceback
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# config & helpers from project
from bot.config import (
    TIMEFRAMES, STATE_FILE, LOG_FILE, BOT_INTERVAL_SEC,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, STRICT_MODE, ENABLED_CONDITIONS
)
from bot.data import get_all_timeframes, get_live_price
from bot.indicators import add_all_indicators
from bot.notifier import send_telegram_message, format_message

# explicit condition imports (call the functions directly)
from bot.conditions.cond_1 import check_cond_1
from bot.conditions.cond_2 import check_cond_2
from bot.conditions.cond_3 import check_cond_3
from bot.conditions.cond_4 import check_cond_4
from bot.conditions.cond_5 import check_cond_5
from bot.conditions.cond_6 import check_cond_6
from bot.conditions.cond_7 import check_cond_7
from bot.conditions.cond_8 import check_cond_8
from bot.conditions.cond_9 import check_cond_9
from bot.conditions.cond_10 import check_cond_10
from bot.conditions.cond_11 import check_cond_11

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ema-bot")

# state file helpers
def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        logger.exception("Failed to load state")
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        logger.exception("Failed to save state")

# build dfs with indicators
def build_dfs():
    raw = get_all_timeframes(TIMEFRAMES)
    dfs = {}
    for tf, df in raw.items():
        dfs[tf] = add_all_indicators(df)
    return dfs

# helper: pretty log one condition entry
def log_cond(idx, entry):
    ok = entry.get("ok", False)
    reason = entry.get("reason") or (entry.get("info", {}) and entry["info"].get("reason"))
    value = entry.get("value") or entry.get("info") or {}
    logger.info("[P%d] %s  reason=%s  values=%s", idx, "✅" if ok else "❌", reason, json.dumps(value, ensure_ascii=False))

# main bot loop
def bot_loop():
    logger.info("🚀 EMA-bot loop started (interval %s sec)", BOT_INTERVAL_SEC)
    state = load_state()
    last_start_key = state.get("last_start_key")
    last_signal_key = (state.get("last_direction"), state.get("last_signal_ts"))

    while True:
        try:
            dfs = build_dfs()
        except Exception as e:
            logger.exception("Failed building dfs: %s", e)
            time.sleep(BOT_INTERVAL_SEC)
            continue

        # snapshot container
        snapshot = {"by_cond": {}, "summary": None, "impulse_tf": None, "direction": None, "timestamp": int(time.time())}
        df5 = dfs.get("5m")

        # ---------- P1: detect start (try both directions) ----------
        try:
            ok1_long, info1_long = check_cond_1(dfs, "long")
        except Exception as e:
            logger.exception("check_cond_1(long) error: %s", e)
            ok1_long, info1_long = False, {"cond":1, "reason": str(e)}
        try:
            ok1_short, info1_short = check_cond_1(dfs, "short")
        except Exception as e:
            logger.exception("check_cond_1(short) error: %s", e)
            ok1_short, info1_short = False, {"cond":1, "reason": str(e)}

        # put both variants into snapshot for full transparency
        snapshot["by_cond"][1] = {"ok_long": ok1_long, "info_long": info1_long,
                                 "ok_short": ok1_short, "info_short": info1_short}

        # determine direction / start_index
        direction = None
        start_index = None
        if ok1_long and not ok1_short:
            direction = "long"
            start_index = info1_long.get("start_index")
        elif ok1_short and not ok1_long:
            direction = "short"
            start_index = info1_short.get("start_index")
        elif ok1_long and ok1_short:
            # both - pick the most recent cross (smaller bars_ago -> larger start_index)
            si_long = info1_long.get("start_index", -1)
            si_short = info1_short.get("start_index", -1)
            if si_long >= si_short:
                direction = "long"
                start_index = si_long
            else:
                direction = "short"
                start_index = si_short
        else:
            # no start — store snapshot and continue
            snapshot["summary"] = "no_start"
            # ensure last_snapshot saved for /status
            state["last_snapshot"] = snapshot
            save_state(state)
            # log P1 details and go next tick
            log_cond(1, {"ok": False, "reason": "Нет стартовой свечи (P1 failed)", "info_long": info1_long, "info_short": info1_short})
            logger.info("ℹ️ Итог: %s", snapshot["summary"])
            time.sleep(BOT_INTERVAL_SEC)
            continue

        snapshot["start_index"] = start_index
        snapshot["direction"] = direction

        # ---------- P2..P6 (mandatory) ----------
        # p2
        try:
            ok2, info2 = check_cond_2(dfs, direction)
        except Exception as e:
            logger.exception("check_cond_2 error: %s", e)
            ok2, info2 = False, {"cond":2, "reason": str(e)}
        snapshot["by_cond"][2] = {"ok": ok2, "info": info2}

        # p3
        try:
            ok3, info3 = check_cond_3(dfs, direction, start_index)
        except Exception as e:
            logger.exception("check_cond_3 error: %s", e)
            ok3, info3 = False, {"cond":3, "reason": str(e)}
        snapshot["by_cond"][3] = {"ok": ok3, "info": info3}

        # p4
        try:
            ok4, info4 = check_cond_4(dfs, direction, start_index)
        except Exception as e:
            logger.exception("check_cond_4 error: %s", e)
            ok4, info4 = False, {"cond":4, "reason": str(e)}
        snapshot["by_cond"][4] = {"ok": ok4, "info": info4}

        # p5
        try:
            ok5, info5 = check_cond_5(dfs, direction, start_index)
        except Exception as e:
            logger.exception("check_cond_5 error: %s", e)
            ok5, info5 = False, {"cond":5, "reason": str(e)}
        snapshot["by_cond"][5] = {"ok": ok5, "info": info5}

        # p6
        try:
            ok6, info6 = check_cond_6(dfs, direction, start_index)
        except Exception as e:
            logger.exception("check_cond_6 error: %s", e)
            ok6, info6 = False, {"cond":6, "reason": str(e)}
        snapshot["by_cond"][6] = {"ok": ok6, "info": info6}

        # mandatory decision
        mandatory_ok = all(snapshot["by_cond"][i]["ok"] for i in (2,3,4,5,6))
        # note: P1 satisfied if we got here
        if not mandatory_ok:
            snapshot["summary"] = "failed_mandatory_1_6"
            # log readable output
            log_cond(1, {"ok": True, "reason": f"start_index={start_index}", "info": snapshot["by_cond"][1]})
            for i in range(2,7):
                log_cond(i, snapshot["by_cond"][i])
            logger.info("ℹ️ Итог: %s", snapshot["summary"])
            state["last_snapshot"] = snapshot
            save_state(state)
            time.sleep(BOT_INTERVAL_SEC)
            continue

        # ---------- P7..P11 (higher TF checks) ----------
        # call checks explicitly so snapshot contains all P1..P11
        try:
            ok7, info7 = check_cond_7(dfs, direction)
        except Exception as e:
            logger.exception("check_cond_7 error: %s", e)
            ok7, info7 = False, {"cond":7, "reason": str(e)}
        snapshot["by_cond"][7] = {"ok": ok7, "info": info7}

        try:
            ok8, info8 = check_cond_8(dfs, direction, start_index)
        except Exception as e:
            logger.exception("check_cond_8 error: %s", e)
            ok8, info8 = False, {"cond":8, "reason": str(e)}
        snapshot["by_cond"][8] = {"ok": ok8, "info": info8}

        try:
            ok9, info9 = check_cond_9(dfs, direction, start_index)
        except Exception as e:
            logger.exception("check_cond_9 error: %s", e)
            ok9, info9 = False, {"cond":9, "reason": str(e)}
        snapshot["by_cond"][9] = {"ok": ok9, "info": info9}

        try:
            ok10, info10 = check_cond_10(dfs, direction, start_index)
        except Exception as e:
            logger.exception("check_cond_10 error: %s", e)
            ok10, info10 = False, {"cond":10, "reason": str(e)}
        snapshot["by_cond"][10] = {"ok": ok10, "info": info10}

        try:
            ok11, info11 = check_cond_11(dfs, direction, start_index)
        except Exception as e:
            logger.exception("check_cond_11 error: %s", e)
            ok11, info11 = False, {"cond":11, "reason": str(e)}
        snapshot["by_cond"][11] = {"ok": ok11, "info": info11}

        # ---------- decision logic (branching) ----------
        # If STRICT_MODE -> require all ENABLED_CONDITIONS to be ok
        if STRICT_MODE:
            all_ok = True
            for cond in ENABLED_CONDITIONS:
                ent = snapshot["by_cond"].get(cond)
                if not ent or not ent.get("ok"):
                    all_ok = False
                    break
            if all_ok:
                snapshot["summary"] = "ok_strict_all"
                snapshot["impulse_tf"] = "strict_all"
                ok_final = True
            else:
                snapshot["summary"] = "failed_strict"
                ok_final = False
        else:
            # non-strict: 1-6 mandatory already passed; now branch:
            if ok8 and ok9:
                snapshot["summary"] = "ok_30m_branch"
                snapshot["impulse_tf"] = "30m"
                ok_final = True
            elif ok10 and ok11:
                snapshot["summary"] = "ok_1h2h_branch"
                snapshot["impulse_tf"] = info10.get("impulse_tf") or "1h/2h"
                ok_final = True
            else:
                snapshot["summary"] = "failed_higher_tf"
                ok_final = False

        # log all conditions P1..P11 nicely
        # P1 has both long/short info -> present it compactly
        log_cond(1, {"ok": True, "reason": f"start_index={start_index}", "info": snapshot["by_cond"][1]})
        for i in range(2,12):
            e = snapshot["by_cond"].get(i, {"ok": False, "info": {"cond": i, "reason": "missing"}})
            # normalize structure which sometimes returns (ok, info) with info inside dict
            if isinstance(e.get("info"), dict) and "reason" not in e["info"]:
                # leave as-is
                pass
            log_cond(i, e)

        logger.info("ℹ️ Decision summary=%s impulse_tf=%s direction=%s", snapshot["summary"], snapshot.get("impulse_tf"), direction)

        # save snapshot
        state["last_snapshot"] = snapshot
        save_state(state)

        # Telegram: debug report at new start candle
        # Unique key by direction+start_timestamp (5m time of start_index)
        try:
            ts = int(df5["time"].iloc[start_index])
        except Exception:
            ts = int(time.time())
        start_key = f"{direction}|{ts}"
        if start_key != last_start_key:
            try:
                price = None
                try:
                    price = get_live_price()
                except Exception:
                    price = None
                msg = format_message(snapshot, price or 0.0, dfs)
                sent = send_telegram_message(msg)
                logger.info("Telegram debug report sent: %s", sent)
            except Exception:
                logger.exception("Telegram debug send failed")
            last_start_key = start_key
            state["last_start_key"] = last_start_key
            save_state(state)

        # Telegram: final signal send (unique by direction+start_ts)
        if ok_final:
            signal_key = (direction, ts)
            if signal_key != last_signal_key:
                try:
                    price = None
                    try:
                        price = get_live_price()
                    except Exception:
                        price = None
                    msg = format_message(snapshot, price or 0.0, dfs)
                    send_telegram_message(msg)
                    logger.info("✅ Final signal message sent")
                except Exception:
                    logger.exception("Failed to send final Telegram")
                last_signal_key = signal_key
                state["last_signal_ts"] = ts
                state["last_direction"] = direction
                save_state(state)
            else:
                logger.info("ℹ️ Duplicate final signal suppressed.")
        else:
            logger.info("ℹ️ No final signal this tick (summary=%s).", snapshot["summary"])

        time.sleep(BOT_INTERVAL_SEC)


# Flask endpoints
@app.route("/")
def home():
    return "✅ EMA-бот (full checks) active."

@app.route("/test")
def test_telegram():
    ok = send_telegram_message("✅ Тестовое уведомление от EMA-бота (full checks).")
    return f"Telegram test sent: {ok}"

@app.route("/status")
def status():
    state = load_state()
    return jsonify({
        "last_signal_ts": state.get("last_signal_ts", "-"),
        "last_direction": state.get("last_direction", "-"),
        "last_start_key": state.get("last_start_key"),
        "last_snapshot": state.get("last_snapshot", {})
    })

if __name__ == "__main__":
    logger.info("Starting main thread + bot_loop")
    t = Thread(target=bot_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
