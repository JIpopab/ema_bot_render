# bot/conditions/cond_1.py
from typing import Tuple, Dict
import pandas as pd
from ..utils import last_cross_index

def check_cond_1(df_by_tf, direction: str) -> Tuple[bool, Dict]:
    """
    1) 5m: EMA10 пересекает EMA21 вслед за EMA5 и не позже, чем через 4 свечи после пересечения EMA5 через EMA21.
       Возвращаем start_index = индекс стартовой свечи (первая после кросса EMA10/21).
       
    Примечание по offset'ам:
    - last_cross_index возвращает offset: 0 = последняя свеча, 1 = предпоследняя и т.д.
    - Для явного и понятного сравнения переводим offset -> индекс в df (0..len-1),
      где индекс 0 = первая свеча в df, индекс len-1 = последняя свеча.
    """
    df5: pd.DataFrame = df_by_tf["5m"]
    ema5, ema10, ema21 = df5["ema5"], df5["ema10"], df5["ema21"]

    # ищем последние кроссы (offset: 0 = последняя св.)
    cross5 = last_cross_index(ema5, ema21, "up" if direction == "long" else "down", lookback=50)
    cross10 = last_cross_index(ema10, ema21, "up" if direction == "long" else "down", lookback=50)

    if cross5 is None or cross10 is None:
        return False, {"cond": 1, "reason": "Нет кроссов EMA5/21 или EMA10/21"}

    # переводим offset -> индекс в датасете (0..len-1)
    # offset 0 -> idx = len-1 (последняя свеча)
    idx5 = len(df5) - 1 - cross5
    idx10 = len(df5) - 1 - cross10

    # Требование: EMA10 пересекла В ПОЗДНЕМ времени относительно EMA5 (т.е. idx10 >= idx5)
    # и не позже, чем через 4 свечи (idx10 - idx5 <= 4).
    if not (idx10 >= idx5 and (idx10 - idx5) <= 4):
        return False, {"cond": 1, "reason": "EMA10 пересекла не вслед за EMA5 ≤4 свеч"}

    # Стартовая свеча — первая свеча ПОСЛЕ пересечения EMA10/21
    # Если кросс был на последней свече, start_index будет за пределами, поэтому кладём в len-1.
    start_index = min(idx10 + 1, len(df5) - 1)

    return True, {"cond": 1, "start_index": start_index}