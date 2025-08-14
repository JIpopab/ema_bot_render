# bot/notifier.py (updated)
import os
import requests
from typing import Dict
from .utils import swing_levels, atr_levels

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.ok
    except Exception:
        return False

def summarise_per_cond(by_cond: Dict) -> str:
    lines = []
    for cid in sorted(by_cond.keys()):
        entry = by_cond[cid]
        ok = entry.get("ok", False)
        info = entry.get("info", {})
        status = "✅" if ok else "❌"
        # try to produce short note
        note = ""
        if isinstance(info, dict):
            note = info.get("reason") or info.get("note") or ""
        else:
            note = str(info)
        lines.append(f"P{cid}: {status} {note}")
    return "\n".join(lines)

def format_message(result: Dict, price: float, dfs=None) -> str:
    dir_ = result.get("direction", "?") or "?"
    impulse_tf = result.get("impulse_tf", "?") or "?"
    by_cond = result.get("by_cond", {})
    lines = [
        f"<b>🔔 Импульс {dir_.upper()}</b>  •  TF импульса: <b>{impulse_tf}</b>",
        f"Текущая цена: <b>{price:,.2f}$</b>",
        "",
        "<b>Проверка условий (1..11)</b>:",
        summarise_per_cond(by_cond),
        "",
    ]
    if dfs and "5m" in dfs:
        df5 = dfs["5m"]
        sup, res = swing_levels(df5, 20)
        i = len(df5)-1
        a_sup, a_res = atr_levels(df5, i, 1.0)
        lines += [
            "<b>Поддержка/Сопротивление</b>",
            f"• Свинги(20):  поддержка ~ <b>{sup:,.2f}$</b>  |  сопротивление ~ <b>{res:,.2f}$</b>",
            f"• ATR14×1:     поддержка ~ <b>{a_sup:,.2f}$</b>  |  сопротивление ~ <b>{a_res:,.2f}$</b>",
        ]
    return "\n".join(lines)
