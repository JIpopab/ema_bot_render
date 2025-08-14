# bot/conditions/cond_1.py
from typing import Tuple, Dict
import pandas as pd
from ..utils import last_cross_index

def check_cond_1(df_by_tf, direction: str) -> Tuple[bool, Dict]:
    """
    1) 5m: EMA10 пересекает EMA21 вслед за EMA5 и не позже, чем через 4 свечи после пересечения EMA5 через EMA21.
       Возвращаем start_index = индекс стартовой свечи (первая после кросса EMA10/21).

    Проверка реального пересечения линий (не учитываем цену свечи).
    """
    df5: pd.DataFrame = df_by_tf["5m"]
    ema5, ema10, ema21 = df5["ema5"], df5["ema10"], df5["ema21"]

    # определяем направление пересечения
    cross_type = "up" if direction == "long" else "down"

    # ищем последние кроссы EMA5/21 и EMA10/21
    cross5 = last_cross_index(ema5, ema21, cross_type, lookback=50)
    cross10 = last_cross_index(ema10, ema21, cross_type, lookback=50)

    if cross5 is None or cross10 is None:
        return False, {"cond": 1, "reason": "Нет реальных пересечений EMA5/21 или EMA10/21"}

    # переводим offset -> индекс в df (0..len-1)
    idx5 = len(df5) - 1 - cross5
    idx10 = len(df5) - 1 - cross10

    # проверяем условие: EMA10 пересекла EMA21 после EMA5, не позже 4 свечей
    if not (idx10 >= idx5 and (idx10 - idx5) <= 4):
        return False, {"cond": 1, "reason": "EMA10 пересекла не вслед за EMA5 ≤4 свеч"}

    # стартовая свеча — первая после пересечения EMA10/21
    start_index = min(idx10 + 1, len(df5) - 1)

    return True, {"cond": 1, "start_index": start_index}