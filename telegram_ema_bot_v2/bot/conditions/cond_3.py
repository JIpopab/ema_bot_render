
# bot/conditions/cond_3.py
from typing import Tuple, Dict
def check_cond_3(df_by_tf, direction: str, start_idx: int) -> Tuple[bool, Dict]:
    """
    3) 5m: macd, rsi, kdj, stoch rsi — растут (long) или падают (short) или стабильны
       Точка отсчёта: вторая свеча позади от стартовой; промежуточная: предпоследняя; конечная: стартовая.
       Допуск 5 ед.
    """
    import numpy as np
    df5 = df_by_tf["5m"]
    i0 = max(0, start_idx-2)   # точка отсчёта
    i1 = max(0, start_idx-1)   # предпоследняя
    i2 = start_idx             # конечная

    def trend_ok(a0, a1, a2, up=True, tol=5.0):
        d = a2 - a0
        if up:
            return d >= -tol  # растёт или почти не падает
        else:
            return d <= tol   # падает или почти не растёт

    up = (direction == "long")

    ok = True
    names = []
    for col in ["macd_dif", "macd_dea", "rsi6", "rsi9", "rsi21", "kdj_j", "kdj_k", "kdj_d", "srsi_k", "srsi_d"]:
        a0, a1_, a2 = df5[col].iloc[i0], df5[col].iloc[i1], df5[col].iloc[i2]
        good = trend_ok(a0, a1_, a2, up=up, tol=5.0)
        names.append((col, good))
        ok = ok and good

    if not ok:
        bad = [n for n,g in names if not g]
        return False, {"cond": 3, "reason": "Индикаторы 5m не в нужном направлении", "bad": bad}
    return True, {"cond": 3}
