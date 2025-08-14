
# bot/notifier.py
import os
import requests
from typing import Dict
from .utils import swing_levels, atr_levels

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception:
        pass

def format_message(result: Dict, price: float, dfs=None) -> str:
    dir_ = result["direction"]
    checks = result["by_cond"]
    impulse_tf = result.get("impulse_tf", "30m")

    lines = [
        f"<b>Импульс {dir_.upper()}</b>  •  TF импульса: <b>{impulse_tf}</b>",
        f"Текущая цена: <b>{price:,.2f}$</b>"
    ]
    for info in checks:
        cid = info.get("cond", "?")
        if "reason" in info:
            lines.append(f"❌ П.{cid}: {info['reason']}")
        else:
            note = f" — {info.get('note','ок')}" if "note" in info else ""
            lines.append(f"✅ П.{cid}{note}")

    if dfs and "5m" in dfs:
        df5 = dfs["5m"]
        sup, res = swing_levels(df5, 20)
        i = len(df5)-1
        a_sup, a_res = atr_levels(df5, i, 1.0)
        lines += [
            "",
            "<b>Поддержка/Сопротивление</b>",
            f"• Свинги(20):  поддержка ~ <b>{sup:,.2f}$</b>  |  сопротивление ~ <b>{res:,.2f}$</b>",
            f"• ATR14×1:     поддержка ~ <b>{a_sup:,.2f}$</b>  |  сопротивление ~ <b>{a_res:,.2f}$</b>",
        ]
    return "\n".join(lines)
