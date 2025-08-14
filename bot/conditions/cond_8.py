
# bot/conditions/cond_8.py
from typing import Tuple, Dict
from ..utils import map_index_by_time, last_cross_index, macd_prev_trend_ok

def check_cond_8(df_by_tf, direction: str, start_idx: int) -> Tuple[bool, Dict]:
    df5 = df_by_tf["5m"]
    df30 = df_by_tf["30m"]

    i30 = map_index_by_time(df5, df30, start_idx)
    if i30 < 3:
        return False, {"cond": 8, "reason": "Недостаточно свечей на 30m"}

    j_now, k_now, d_now = df30["kdj_j"].iloc[i30], df30["kdj_k"].iloc[i30], df30["kdj_d"].iloc[i30]
    j_2 = df30["kdj_j"].iloc[i30-2]
    if direction == "long":
        if not (j_now > k_now > d_now and (j_now - j_2) > 20):
            return False, {"cond": 8, "reason": "30m KDJ long: порядок/ΔJ<=20"}
        cross_ago = last_cross_index(df30["kdj_j"], df30["kdj_d"], "up", lookback=2)
        if cross_ago is None:
            return False, {"cond": 8, "reason": "30m KDJ: нет кросса J↑D ≤2 свечей"}
    else:
        if not (j_now < k_now < d_now and (df30['kdj_j'].iloc[i30-2] - j_now) > 20):
            return False, {"cond": 8, "reason": "30m KDJ short: порядок/ΔJ<=20"}
        cross_ago = last_cross_index(df30["kdj_j"], df30["kdj_d"], "down", lookback=2)
        if cross_ago is None:
            return False, {"cond": 8, "reason": "30m KDJ: нет кросса J↓D ≤2 свечей"}

    r6, r9, r21 = df30["rsi6"], df30["rsi9"], df30["rsi21"]
    r6_now, r6_2 = r6.iloc[i30], r6.iloc[i30-2]
    if direction == "long":
        if not (r6.iloc[i30] > r9.iloc[i30] and r9.iloc[i30] >= r21.iloc[i30]-1):
            return False, {"cond": 8, "reason": "30m RSI long: порядок не ок"}
        if not ((r6_now - r6_2) > 10):
            return False, {"cond": 8, "reason": "30m RSI long: ΔRSI6 ≤ 10"}
        cross_ago_rsi = last_cross_index(r6, r21, "up", lookback=2)
        if cross_ago_rsi is None:
            return False, {"cond": 8, "reason": "30m RSI: нет кросса RSI6↑RSI21 ≤2 свечей"}
    else:
        if not (r6.iloc[i30] < r9.iloc[i30] and r9.iloc[i30] <= r21.iloc[i30]+1):
            return False, {"cond": 8, "reason": "30m RSI short: порядок не ок"}
        if not ((r6.iloc[i30-2] - r6_now) > 10):
            return False, {"cond": 8, "reason": "30m RSI short: ΔRSI6 ≤ 10"}
        cross_ago_rsi = last_cross_index(r6, r21, "down", lookback=2)
        if cross_ago_rsi is None:
            return False, {"cond": 8, "reason": "30m RSI: нет кросса RSI6↓RSI21 ≤2 свечей"}

    if abs(cross_ago - cross_ago_rsi) > 2:
        return False, {"cond": 8, "reason": "30m рассинхрон кроссов KDJ vs RSI > 2 свечей"}

    if not macd_prev_trend_ok(df30, direction, min_bars=4):
        return False, {"cond": 8, "reason": "30m предыдущий тренд по MACD < 4 баров"}

    return True, {"cond": 8, "i30": i30}
