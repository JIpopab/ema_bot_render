# bot/conditions/cond_1.py
from typing import Tuple, Dict
import pandas as pd
from ..utils import last_cross_index

def check_cond_1(df_by_tf, direction: str) -> Tuple[bool, Dict]:
    """
    1) 5m: EMA10 пересекает EMA21 вслед за EMA5 и не позже, чем через 4 свечи после пересечения EMA5 через EMA21.
       Триггер ОДНОРАЗОВЫЙ: только на ПЕРВОЙ свече ПОСЛЕ кросса EMA10/21.
       Возвращаем start_index = индекс стартовой свечи (эта самая первая свеча после кросса).
    """
    df5: pd.DataFrame = df_by_tf["5m"]
    # нужна минимум 3 свечи, чтобы "предыдущая" и "текущая" корректно определялись
    if len(df5) < 3:
        return False, {"cond": 1, "reason": "Недостаточно данных (<3 свечей)"}

    # проверяем наличие нужных колонок
    for col in ("ema5", "ema10", "ema21"):
        if col not in df5.columns:
            return False, {"cond": 1, "reason": f"Нет колонки {col}"}

    ema5, ema10, ema21 = df5["ema5"], df5["ema10"], df5["ema21"]
    cross_type = "up" if direction == "long" else "down"

    # Находим последние пересечения линий EMA5/21 и EMA10/21
    cross5 = last_cross_index(ema5, ema21, cross_type, lookback=50)
    cross10 = last_cross_index(ema10, ema21, cross_type, lookback=50)

    if cross5 is None or cross10 is None:
        return False, {"cond": 1, "reason": "Нет реальных пересечений EMA5/21 или EMA10/21"}

    # offset -> индекс (0..len-1), где len-1 = самая свежая свеча
    idx5 = len(df5) - 1 - cross5
    idx10 = len(df5) - 1 - cross10

    # 1) EMA10 пересекла EMA21 ПОСЛЕ EMA5 и не позже, чем через 4 свечи
    if not (idx10 >= idx5 and (idx10 - idx5) <= 4):
        return False, {"cond": 1, "reason": "EMA10 пересекла не вслед за EMA5 ≤4 свеч"}

    # 2) Одноразовость: cond_1 истинно ТОЛЬКО когда сейчас идет ПЕРВАЯ свеча после кросса EMA10/21.
    #    Кросс должен быть на предыдущей свече (len-2), а стартовая = текущая (len-1).
    if idx10 != len(df5) - 2:
        return False, {"cond": 1, "reason": "Сейчас не первая свеча после кросса EMA10/21"}

    # (необязательно, но полезно) верифицируем сам факт кросса на закрытых свечах
    prev10, prev21 = ema10.iloc[idx10 - 1], ema21.iloc[idx10 - 1]
    curr10, curr21 = ema10.iloc[idx10], ema21.iloc[idx10]
    if direction == "long":
        real_cross = (prev10 < prev21) and (curr10 > curr21)
    else:
        real_cross = (prev10 > prev21) and (curr10 < curr21)
    if not real_cross:
        return False, {"cond": 1, "reason": "EMA10/21 не дали смену стороны на закрытых свечах"}

    # Стартовая свеча — РОВНО текущая (первая после кросса)
    start_index = idx10 + 1  # это будет len(df5) - 1

    return True, {"cond": 1, "start_index": start_index}