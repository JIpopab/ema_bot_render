
# bot/conditions/cond_11.py
from typing import Tuple, Dict
from ..utils import map_index_by_time

def check_cond_11(df_by_tf, direction: str, start_idx: int) -> Tuple[bool, Dict]:
    df5 = df_by_tf["5m"]
    df30 = df_by_tf["30m"]
    i30 = map_index_by_time(df5, df30, start_idx)
    if i30 < 6:
        return False, {"cond": 11, "reason": "Недостаточно свечей на 30m"}

    r6, r9, r21 = df30["rsi6"].iloc[i30], df30["rsi9"].iloc[i30], df30["rsi21"].iloc[i30]
    j, k, d = df30["kdj_j"].iloc[i30], df30["kdj_k"].iloc[i30], df30["kdj_d"].iloc[i30]
    sK, sD = df30["srsi_k"].iloc[i30], df30["srsi_d"].iloc[i30]

    if direction == "long":
        ok_rsi = (r21 < 63 and r6 > r9 > r21) or (r21 < 58 and r6 > r9 and r9 >= r21 - 5)
        prev = df30.iloc[max(0, i30-5):i30]
        cond_prev = ((prev["rsi6"] <= prev["rsi9"]+2) & (prev["rsi9"] <= prev["rsi21"]+2.5)).any()
        if not (ok_rsi and cond_prev):
            return False, {"cond": 11, "reason": "30m RSI (ослабл.) long не ок"}

        ok_kdj = (d < 82 and j > k > d) or (d < 82 and abs(j-k) <= 10 and abs(k-d) <= 4)
        prev_kdj = df30.iloc[max(0, i30-12):i30]
        cond_prev_kdj = ((prev_kdj["kdj_j"] < prev_kdj["kdj_k"]) & (prev_kdj["kdj_k"] < prev_kdj["kdj_d"])).any()
        if not (ok_kdj and cond_prev_kdj):
            return False, {"cond": 11, "reason": "30m KDJ (ослабл.) long не ок"}

        if not (sD < 89.5 and sK >= sD - 7):
            return False, {"cond": 11, "reason": "30m StochRSI (ослабл.) long не ок"}
    else:
        ok_rsi = (r21 > 37 and r6 < r9 < r21) or \
                 (r21 > 37 and r6 <= r9 and r9 < r21) or \
                 (r21 > 48 and r6 < r9 and r9 <= r21 + 6)
        prev = df30.iloc[max(0, i30-5):i30]
        cond_prev = ((prev["rsi6"] >= prev["rsi9"]-1) & (prev["rsi9"] >= prev["rsi21"]-1)).any()
        if not (ok_rsi and cond_prev):
            return False, {"cond": 11, "reason": "30m RSI (ослабл.) short не ок"}

        ok_kdj = (d > 30 and j < k < d) or (d > 30 and abs(j-k) <= 8 and abs(k-d) <= 5)
        prev_kdj = df30.iloc[max(0, i30-11):i30]
        cond_prev_kdj = ((prev_kdj["kdj_j"] > prev_kdj["kdj_k"]) & (prev_kdj["kdj_k"] > prev_kdj["kdj_d"])).any()
        if not (ok_kdj and cond_prev_kdj):
            return False, {"cond": 11, "reason": "30m KDJ (ослабл.) short не ок"}

        if not (sD > 23 and sK <= sD + 8):
            return False, {"cond": 11, "reason": "30m StochRSI (ослабл.) short не ок"}

    return True, {"cond": 11, "i30": i30}
