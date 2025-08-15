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
    3) Сигнал даётся только на следующей свече после пересечения EMA10/EMA21.
    4) Повторные сигналы для того же пересечения не отправляются.
    """
    df5: pd.DataFrame = df_by_tf["5m"]
    ema5, ema10, ema21 = df5["ema5"], df5["ema10"], df5["ema21"]

    cross_type = "up" if direction == "long" else "down"

    # Находим пересечения EMA5 и EMA10 с EMA21 (по закрытым свечам, без текущей)
    cross5 = last_cross_index(ema5[:-1], ema21[:-1], cross_type, lookback=50)
    cross10 = last_cross_index(ema10[:-1], ema21[:-1], cross_type, lookback=50)

    if cross5 is None or cross10 is None:
        return False, {"cond": 1, "reason": "Нет пересечений EMA5/21 или EMA10/21"}

    # Индексы пересечений относительно начала DataFrame
    idx5 = len(df5) - 1 - cross5
    idx10 = len(df5) - 1 - cross10

    # EMA10 пересекла EMA21 не позже 4 свечей после EMA5
    if not (idx10 >= idx5 and (idx10 - idx5) <= 4):
        return False, {"cond": 1, "reason": "EMA10 пересекла не вслед за EMA5 ≤4 свеч"}

    # Проверка, что пересечение было реальным (не касание)
    prev_ema10, prev_ema21 = ema10.iloc[idx10 - 1], ema21.iloc[idx10 - 1]
    curr_ema10, curr_ema21 = ema10.iloc[idx10], ema21.iloc[idx10]
    crossed_real = (
        (cross_type == "up" and prev_ema10 < prev_ema21 and curr_ema10 > curr_ema21) or
        (cross_type == "down" and prev_ema10 > prev_ema21 and curr_ema10 < curr_ema21)
    )
    if not crossed_real:
        return False, {"cond": 1, "reason": "Касание или пересечения нет"}

    # Сигнал даём только на следующей свече после пересечения
    start_index = idx10 + 1
    if start_index != len(df5) - 1:
        return False, {"cond": 1, "reason": "Ещё не наступила свеча после пересечения"}

    # Читаем состояние, чтобы не дублировать сигнал
    state = load_state()
    last_cross = state.get("last_cross")
    last_idx = state.get("last_idx")

    if last_cross == cross_type and last_idx == idx10:
        return False, {"cond": 1, "reason": "Сигнал уже был (persist)"}

    # Сохраняем новое состояние
    state["last_cross"] = cross_type
    state["last_idx"] = idx10
    save_state(state)

    return True, {"cond": 1, "start_index": start_index}