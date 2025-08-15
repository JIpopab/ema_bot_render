# bot/conditions/cond_1.py
from typing import Tuple, Dict
import pandas as pd
import json, os
import logging
from ..utils import last_cross_index

logger = logging.getLogger(__name__)
STATE_FILE = "cond1_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    # Конвертируем numpy int/float в обычные Python типы для json
    safe_state = {}
    for k, v in state.items():
        if hasattr(v, "item"):
            safe_state[k] = v.item()
        else:
            safe_state[k] = v
    with open(STATE_FILE, "w") as f:
        json.dump(safe_state, f)

def check_cond_1(df_by_tf, direction: str) -> Tuple[bool, Dict]:
    """
    Условие:
    1) EMA10 пересекает EMA21 вслед за EMA5 (EMA5 пересекла не позже 4 свечей назад).
    2) Касания игнорируются (нужно реальное пересечение).
    3) Сигнал даётся сразу после закрытия свечи с подтверждённым пересечением EMA10/21.
    4) Повторные сигналы для того же пересечения не отправляются.
    """
    df5: pd.DataFrame = df_by_tf["5m"]
    ema5, ema10, ema21 = df5["ema5"], df5["ema10"], df5["ema21"]

    cross_type = "up" if direction == "long" else "down"

    # Находим последнее пересечение EMA5/21
    cross5 = last_cross_index(ema5[:-1], ema21[:-1], cross_type, lookback=50)
    if cross5 is None:
        reason = "Нет пересечения EMA5/21"
        ok_flag = False
        info = {"cond": 1, "reason": reason}
        logger.info("[P1] %s reason=%s values=%s", "✅" if ok_flag else "❌", reason, json.dumps(info, ensure_ascii=False))
        return False, info

    idx5 = len(df5) - 1 - cross5  # индекс последнего пересечения EMA5

    # Диапазон свечей для проверки EMA10: максимум 4 свечи после EMA5
    lookback_range = range(idx5 + 1, min(idx5 + 5, len(df5)))

    crossed_idx = None
    for i in lookback_range:
        prev_ema10, prev_ema21 = ema10.iloc[i - 1], ema21.iloc[i - 1]
        curr_ema10, curr_ema21 = ema10.iloc[i], ema21.iloc[i]

        # Реальное пересечение EMA10/21
        real_cross = (
            (cross_type == "up" and prev_ema10 < prev_ema21 and curr_ema10 > curr_ema21) or
            (cross_type == "down" and prev_ema10 > prev_ema21 and curr_ema10 < curr_ema21)
        )
        # Касание EMA10/21
        touch = (cross_type == "up" and curr_ema10 == curr_ema21) or \
                (cross_type == "down" and curr_ema10 == curr_ema21)

        # Проверяем только последнюю закрытую свечу
        if i == len(df5) - 1:
            if real_cross:
                crossed_idx = i
                break  # сигнал готов
            elif touch:
                reason = "EMA10 коснулась EMA21, ждем следующей свечи"
                ok_flag = False
                info = {"cond": 1, "reason": reason}
                logger.info("[P1] %s reason=%s values=%s", "✅" if ok_flag else "❌", reason, json.dumps(info, ensure_ascii=False))
                return False, info

    if crossed_idx is None:
        reason = "Нет подтвержденного пересечения EMA10/21 в допустимом диапазоне"
        ok_flag = False
        info = {"cond": 1, "reason": reason}
        logger.info("[P1] %s reason=%s values=%s", "✅" if ok_flag else "❌", reason, json.dumps(info, ensure_ascii=False))
        return False, info

    # Проверка состояния, чтобы не дублировать сигнал
    state = load_state()
    last_cross = state.get("last_cross")
    last_idx = state.get("last_idx")

    if last_cross == cross_type and last_idx == int(crossed_idx):
        reason = "Сигнал уже был (persist)"
        ok_flag = False
        info = {"cond": 1, "reason": reason}
        logger.info("[P1] %s reason=%s values=%s", "✅" if ok_flag else "❌", reason, json.dumps(info, ensure_ascii=False))
        return False, info

    # Сохраняем новое состояние
    state["last_cross"] = cross_type
    state["last_idx"] = int(crossed_idx)
    save_state(state)

    reason = "EMA10 пересекла EMA21, сигнал готов"
    ok_flag = True
    info = {"cond": 1, "start_index": crossed_idx}
    logger.info("[P1] %s reason=%s values=%s", "✅" if ok_flag else "❌", reason, json.dumps(info, ensure_ascii=False))

    return True, info