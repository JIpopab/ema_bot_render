
# bot/conditions/cond_4.py
from typing import Tuple, Dict
def check_cond_4(df_by_tf, direction: str, start_idx: int) -> Tuple[bool, Dict]:
    """
    4) 5m: KDJ и RSI «свободное пространство» + порядок без разворота.
       KDJ: long j>k>d и (J-D) >= 6; short j<k<d и (D-J) >= 6 (без погрешности).
       RSI: тренд от t-3 до t (допуск 5 ед).
    """
    df5 = df_by_tf["5m"]
    i = start_idx
    j, k, d = df5["kdj_j"].iloc[i], df5["kdj_k"].iloc[i], df5["kdj_d"].iloc[i]
    if direction == "long":
        if not (j > k > d and (j - d) >= 6):
            return False, {"cond": 4, "reason": "5m KDJ long: порядок/J-D<6"}
    else:
        if not (j < k < d and (d - j) >= 6):
            return False, {"cond": 4, "reason": "5m KDJ short: порядок/D-J<6"}

    i0 = max(0, i-3)
    r0, r1 = df5["rsi6"].iloc[i0], df5["rsi6"].iloc[i]
    up = (direction=="long")
    if up and not (r1 >= r0 - 5):
        return False, {"cond": 4, "reason": "5m RSI long: не растёт (t-3→t)"}
    if (not up) and not (r1 <= r0 + 5):
        return False, {"cond": 4, "reason": "5m RSI short: не падает (t-3→t)"}
    return True, {"cond": 4}
