
# bot/conditions/cond_1.py
from typing import Tuple, Dict
import pandas as pd
from ..utils import last_cross_index

def check_cond_1(df_by_tf, direction: str) -> Tuple[bool, Dict]:
    """
    1) 5m: EMA10 пересекает EMA21 вслед за EMA5 и не позже, чем через 4 свечи после пересечения EMA5 через EMA21.
       Возвращаем start_index = индекс стартовой свечи (первая после кросса EMA10/21).
    """
    df5 = df_by_tf["5m"]
    ema5, ema10, ema21 = df5["ema5"], df5["ema10"], df5["ema21"]

    cross5 = last_cross_index(ema5, ema21, "up" if direction=="long" else "down", lookback=50)
    cross10 = last_cross_index(ema10, ema21, "up" if direction=="long" else "down", lookback=50)
    if cross5 is None or cross10 is None:
        return False, {"cond": 1, "reason": "Нет кроссов EMA5/21 или EMA10/21"}

    # cross_index — сколько свеч назад произошёл кросс; «вслед» означает cross10 <= cross5 + 4 (по времени)
    # и кросс10 НЕ раньше кросса5
    if not (cross10 >= cross5 and (cross10 - cross5) <= 4):
        return False, {"cond": 1, "reason": "EMA10 пересекла не вслед за EMA5 ≤4 свеч"}

    # Стартовая свеча — первая свеча ПОСЛЕ пересечения EMA10/21
    start_index = len(df5) - cross10  # текущая свеча индекс len-1, кросс_ago=0 -> start=len
    start_index = min(start_index, len(df5)-1)
    return True, {"cond": 1, "start_index": start_index}
