
# bot/conditions/cond_7.py
from typing import Tuple, Dict
def check_cond_7(df_by_tf, direction: str) -> Tuple[bool, Dict]:
    """
    7) 15m: дублирует пункт 5 (RSI «свободное пространство») на 15m стартовой проекции.
    """
    from ..utils import map_index_by_time
    df5 = df_by_tf["5m"]; df15 = df_by_tf["15m"]
    i15 = map_index_by_time(df5, df15, len(df5)-1)
    r6, r9, r21 = df15["rsi6"].iloc[i15], df15["rsi9"].iloc[i15], df15["rsi21"].iloc[i15]
    if direction == "long":
        if not ( (r6 < 70 or (r6 >= 70 and (r6 - r9) >= 4)) and (r21 < 70) ):
            return False, {"cond": 7, "reason": "15m RSI long: нет свободного пространства"}
    else:
        if not ( (r6 > 30 or (r6 <= 30 and (r9 - r6) >= 4)) and (r21 > 30) ):
            return False, {"cond": 7, "reason": "15m RSI short: нет свободного пространства"}
    return True, {"cond": 7}
