
# bot/conditions/cond_6.py
from typing import Tuple, Dict
def check_cond_6(df_by_tf, direction: str, start_idx: int) -> Tuple[bool, Dict]:
    """
    6) 15m: StochRSI, RSI (динамика + порядок на стартовой), KDJ (динамика + порядок), MACD DEA порог.
    Погрешности как в ТЗ.
    """
    from ..utils import map_index_by_time
    df5 = df_by_tf["5m"]; df15 = df_by_tf["15m"]
    i15 = map_index_by_time(df5, df15, start_idx)
    if i15 < 2:
        return False, {"cond": 6, "reason": "Недостаточно свечей на 15m"}

    # 6.1 Stoch RSI
    sK, sD = df15["srsi_k"].iloc[i15], df15["srsi_d"].iloc[i15]
    if direction == "long":
        if not (sK >= sD - 3 and sD <= 82):
            return False, {"cond": 6, "reason": "15m StochRSI long не ок"}
    else:
        if not (sK <= sD + 2 and sD >= 19):
            return False, {"cond": 6, "reason": "15m StochRSI short не ок"}

    # 6.2 RSI динамика от i-2 -> i (допуск 6.5) + порядок на стартовой
    r6, r9, r21 = df15["rsi6"], df15["rsi9"], df15["rsi21"]
    base = i15 - 2
    if direction == "long":
        if not (r6.iloc[i15] >= r6.iloc[base] - 6.5):  # растёт/ровно
            return False, {"cond": 6, "reason": "15m RSI long: динамика r6 не ок"}
        if not (r6.iloc[i15] > r9.iloc[i15] > r21.iloc[i15]):
            return False, {"cond": 6, "reason": "15m RSI long: порядок r6>r9>r21 не ок"}
    else:
        if not (r6.iloc[i15] <= r6.iloc[base] + 6.5):  # падает/ровно
            return False, {"cond": 6, "reason": "15m RSI short: динамика r6 не ок"}
        if not (r6.iloc[i15] < r9.iloc[i15] < r21.iloc[i15]):
            return False, {"cond": 6, "reason": "15m RSI short: порядок r6<r9<r21 не ок"}

    # 6.3 KDJ динамика от i-2 -> i (допуск 5) + порядок
    j,k,d = df15["kdj_j"], df15["kdj_k"], df15["kdj_d"]
    if direction == "long":
        if not (j.iloc[i15] >= j.iloc[i15-2] - 5 and k.iloc[i15] >= k.iloc[i15-2] - 5 and d.iloc[i15] >= d.iloc[i15-2] - 5):
            return False, {"cond": 6, "reason": "15m KDJ long: динамика не ок"}
        if not (j.iloc[i15] > k.iloc[i15] > d.iloc[i15] and (d.iloc[i15] < 60 or (j.iloc[i15]-d.iloc[i15]) >= 20) and j.iloc[i15] < 100):
            return False, {"cond": 6, "reason": "15m KDJ long: порядок/границы не ок"}
    else:
        if not (j.iloc[i15] <= j.iloc[i15-2] + 5 and k.iloc[i15] <= k.iloc[i15-2] + 5 and d.iloc[i15] <= d.iloc[i15-2] + 5):
            return False, {"cond": 6, "reason": "15m KDJ short: динамика не ок"}
        if not (j.iloc[i15] < k.iloc[i15] < d.iloc[i15] and (d.iloc[i15] > 40 or (d.iloc[i15]-j.iloc[i15]) >= 20) and j.iloc[i15] > 0):
            return False, {"cond": 6, "reason": "15m KDJ short: порядок/границы не ок"}

    # 6.4 MACD(DEA) пределы
    dea = df15["macd_dea"].iloc[i15]
    if direction == "long":
        if not (dea < 150):
            return False, {"cond": 6, "reason": f"15m MACD DEA long: {dea:.1f} ≥ 150"}
    else:
        if not (dea > -150):
            return False, {"cond": 6, "reason": f"15m MACD DEA short: {dea:.1f} ≤ -150"}
    return True, {"cond": 6}
