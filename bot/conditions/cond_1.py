import logging
import time
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# параметры точности
EPS_ABS = 1e-8
EPS_REL = 1e-5


def _eps(a: float, b: float) -> float:
    """Адаптивная точность: комбинация абсолютной и относительной"""
    return max(EPS_ABS, EPS_REL * max(abs(a), abs(b)))


def _is_touch(a: float, b: float) -> bool:
    """Почти равны (с учётом eps)"""
    return abs(a - b) <= _eps(a, b)


def _is_real_cross(prev_a: float, prev_b: float, curr_a: float, curr_b: float, cross_type: str) -> bool:
    """Фиксируем только настоящее пересечение (а не дрожание вокруг нуля)"""
    # если слишком близко — считаем "touch", а не кросс
    if _is_touch(curr_a, curr_b) or _is_touch(prev_a, prev_b):
        return False

    prev_diff = prev_a - prev_b
    curr_diff = curr_a - curr_b

    # если пересеклись реально (знак поменялся)
    if prev_diff * curr_diff < 0:
        # добавляем фильтр: разница должна быть больше eps, чтобы не ловить микродрожь
        if abs(curr_diff) <= _eps(curr_a, curr_b):
            return False

        if cross_type == "up" and curr_diff > 0:
            return True
        if cross_type == "down" and curr_diff < 0:
            return True

    return False


def check_cond_1(df, state: Dict, last_closed_pos: int) -> Optional[Dict]:
    """
    Условие 1: сначала EMA5 пересекает EMA21 (up или down),
    затем в пределах 5 баров EMA10 пересекает EMA21 в том же направлении.
    """

    now = int(time.time())
    last_ts = int(df["ts"].iloc[last_closed_pos])

    last_bar_closed = (now - last_ts) >= 60  # для 1m TF
    logger.info("[P1][DEBUG] last_bar_closed=%s last_closed_pos=%s now=%s last_ts=%s",
                last_bar_closed, last_closed_pos, now, last_ts)

    prev_closed_pos = last_closed_pos - 1

    prev_closed = {
        "ema5": df["ema5"].iloc[prev_closed_pos],
        "ema10": df["ema10"].iloc[prev_closed_pos],
        "ema21": df["ema21"].iloc[prev_closed_pos],
    }
    last_closed = {
        "ema5": df["ema5"].iloc[last_closed_pos],
        "ema10": df["ema10"].iloc[last_closed_pos],
        "ema21": df["ema21"].iloc[last_closed_pos],
    }

    logger.info("[P1][DEBUG] prev_closed: pos=%s ema5=%s ema10=%s ema21=%s",
                prev_closed_pos, prev_closed["ema5"], prev_closed["ema10"], prev_closed["ema21"])
    logger.info("[P1][DEBUG] last_closed: pos=%s ema5=%s ema10=%s ema21=%s",
                last_closed_pos, last_closed["ema5"], last_closed["ema10"], last_closed["ema21"])

    # --------------------------------------------------------
    # 1. если есть активное ожидание, то игнорируем новые ema5/21
    # --------------------------------------------------------
    if state.get("cond1_waiting"):
        start_pos = state["cond1_waiting"]["start_pos"]
        direction = state["cond1_waiting"]["direction"]

        bars_since = last_closed_pos - start_pos
        if bars_since >= 5:
            logger.info("[P1] ⏱ timeout: bars_since=%s -> сброс ожидания", bars_since)
            state.pop("cond1_waiting")
            return {"cond": 1, "reason": "Нет подтвержденного пересечения EMA10/21 в допустимом диапазоне"}

        # проверяем пересечение EMA10/21 в том же направлении
        if _is_real_cross(prev_closed["ema10"], prev_closed["ema21"],
                          last_closed["ema10"], last_closed["ema21"], direction):
            logger.info("[P1] ✅ подтвержденное пересечение ema10/21 type=%s", direction)
            state.pop("cond1_waiting")
            return {"cond": 1, "direction": direction}

        logger.info("[P1] ❌ wait: prev=%s curr=%s", prev_closed["ema10"] - prev_closed["ema21"],
                    last_closed["ema10"] - last_closed["ema21"])
        return None

    # --------------------------------------------------------
    # 2. если ожидания нет — ищем новое пересечение EMA5/21
    # --------------------------------------------------------
    for cross_type in ("up", "down"):
        if _is_real_cross(prev_closed["ema5"], prev_closed["ema21"],
                          last_closed["ema5"], last_closed["ema21"], cross_type):
            logger.info("[P1] ℹ️ Detected ema5/21 cross at pos=%s type=%s -> start waiting",
                        last_closed_pos, cross_type)
            state["cond1_waiting"] = {"start_pos": last_closed_pos, "direction": cross_type}
            return None

    # если ничего не нашли
    logger.info("[P1] ❌ reason= values={}")
    return None
