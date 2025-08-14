
# bot/conditions/cond_9.py
from typing import Tuple, Dict
from ..utils import map_index_by_time, last_cross_index

def check_cond_9(df_by_tf, direction: str, start_idx: int) -> Tuple[bool, Dict]:
    df5 = df_by_tf["5m"]
    df1h = df_by_tf["1H"]

    i1h = map_index_by_time(df5, df1h, start_idx)
    if i1h < 3:
        return False, {"cond": 9, "reason": "Недостаточно свечей на 1h"}

    if direction == "long":
        cross_kdj = last_cross_index(df1h["kdj_j"], df1h["kdj_d"], "up", lookback=3)
        ok_order = (df1h["kdj_j"].iloc[i1h] > df1h["kdj_k"].iloc[i1h] > df1h["kdj_d"].iloc[i1h])
    else:
        cross_kdj = last_cross_index(df1h["kdj_j"], df1h["kdj_d"], "down", lookback=3)
        ok_order = (df1h["kdj_j"].iloc[i1h] < df1h["kdj_k"].iloc[i1h] < df1h["kdj_d"].iloc[i1h])
    if cross_kdj is None or not ok_order:
        return False, {"cond": 9, "reason": "1h KDJ условия не выполнены"}

    if direction == "long":
        cross_rsi = last_cross_index(df1h["rsi6"], df1h["rsi21"], "up", lookback=3)
        ok_rsi_ord = df1h["rsi6"].iloc[i1h] > df1h["rsi9"].iloc[i1h] > df1h["rsi21"].iloc[i1h]
    else:
        cross_rsi = last_cross_index(df1h["rsi6"], df1h["rsi21"], "down", lookback=3)
        ok_rsi_ord = df1h["rsi6"].iloc[i1h] < df1h["rsi9"].iloc[i1h] < df1h["rsi21"].iloc[i1h]
    if cross_rsi is None or not ok_rsi_ord:
        return False, {"cond": 9, "reason": "1h RSI условия не выполнены"}

    if direction == "long":
        cross_srsi = last_cross_index(df1h["srsi_k"], df1h["srsi_d"], "up", lookback=3)
        if cross_srsi is None or not (df1h["srsi_k"].iloc[i1h] >= df1h["srsi_d"].iloc[i1h] - 3 and df1h["srsi_d"].iloc[i1h] <= 82):
            return False, {"cond": 9, "reason": "1h StochRSI long не ок"}
    else:
        cross_srsi = last_cross_index(df1h["srsi_k"], df1h["srsi_d"], "down", lookback=3)
        if cross_srsi is None or not (df1h["srsi_k"].iloc[i1h] <= df1h["srsi_d"].iloc[i1h] + 2 and df1h["srsi_d"].iloc[i1h] >= 19):
            return False, {"cond": 9, "reason": "1h StochRSI short не ок"}

    if max(cross_kdj, cross_rsi, cross_srsi) - min(cross_kdj, cross_rsi, cross_srsi) > 2:
        return False, {"cond": 9, "reason": "1h рассинхрон кроссов > 2 свечей"}

    return True, {"cond": 9, "i1h": i1h}
