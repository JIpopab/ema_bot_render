# bot/conditions/cond_1.py
from typing import Tuple, Dict
import pandas as pd
import json, os
from ..utils import last_cross_index

STATE_FILE = "cond1_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def check_cond_1(df_by_tf, direction: str) -> Tuple[bool, Dict]:
    """
    Условие:
    1) EMA10 пересекает EMA21 вслед за EMA5 (EMA5 пересекла не позже 4 свечей назад).
    2) Касания игнорируются (нужно реальное пересечение).
    3) Сигнал даётся сразу после закрытия свечи с пересечением EMA10/21.
    4) Повторные сигналы для того же пересечения не отправляются.
    """
    df5: pd.DataFrame = df_by_tf["5m"]
    ema5, ema10, ema21 = df5["ema5"], df5["ema10"], df5["ema21"]

    cross_type = "up" if direction == "long" else "down"

    # Находим последнее пересечение EMA5 и EMA21 (по закрытым свечам)
    cross5 = last_cross_index(ema5[:-1], ema21[:-1], cross_type, lookback=50)
    if cross5 is None:
        return False, {"cond": 1, "reason": "Нет пересечения EMA5/21"}

    idx5 = len(df5) - 1 - cross5  # индекс последней EMA5/21 свечи

    # Проверяем EMA10/21 в окне до 4 свечей после EMA5
    crossed_idx = None
    for i in range(idx5, min(idx5 + 5, len(df5))):
        prev_ema10, prev_ema21 = ema10.iloc[i - 1], ema21.iloc[i - 1]
        curr_ema10, curr_ema21 = ema10.iloc[i], ema21.iloc[i]

        # Реальное пересечение на закрытии свечи
        real_cross = (
            (cross_type == "up" and prev_ema10 < prev_ema21 and curr_ema10 > curr_ema21) or
            (cross_type == "down" and prev_ema10 > prev_ema21 and curr_ema10 < curr_ema21)
        )

        # Касание (игнорируем)
        touch = (curr_ema10 == curr_ema21)

        if real_cross:
            crossed_idx = i
            break  # нашли пересечение, больше свечи не проверяем
        elif touch:
            continue  # ждем следующей свечи

    if crossed_idx is None:
        return False, {"cond": 1, "reason": "EMA10 не пересекла EMA21 в пределах 4 свечей после EMA5"}

    # Проверка состояния для предотвращения дублирования сигнала
    state = load_state()
    last_cross = state.get("last_cross")
    last_idx = state.get("last_idx")

    if last_cross == cross_type and last_idx == crossed_idx:
        return False, {"cond": 1, "reason": "Сигнал уже был (persist)"}

    # Сохраняем новое состояние
    state["last_cross"] = cross_type
    state["last_idx"] = crossed_idx
    save_state(state)

    # Сигнал шлём сразу после закрытия свечи с пересечением
    return True, {"cond": 1, "start_index": crossed_idx}