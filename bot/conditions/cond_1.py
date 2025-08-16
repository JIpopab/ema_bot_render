# bot/conditions/cond_1.py
"""
Условие 1 (финальная версия, с проверками закрытых свечей и детальным логированием):

Логика:
1) Отслеживаем пересечение EMA5 / EMA21 (старт ожидания).
2) После старта ждём реального пересечения EMA10 / EMA21 на закрытии свечи,
   допускаем максимум 4 свечи ожидания (если нет - сбрасываем на 5-й).
3) Одновременное пересечение (EMA5 и EMA10 пересекли EMA21 на одной свече) — считается валидным.
4) Игнорируем касания/micro-пересечения (используем eps-гистерезис).
5) Сигнал формируется только если пересечение произошло по EMA-линии,
   а не по цене свечи (никаких проверок по `close` для триггера).
6) Защита от дублирования сигнала (persist) и логирование двух последних закрытых свечей.
7) Проверяем, что последняя свеча закрыта (по таймстемпу и TF длине). Если последняя — живая,
   используем предпоследнюю как "last closed".
"""
from typing import Tuple, Dict, Optional
import pandas as pd
import json
import os
import logging
import time

logger = logging.getLogger(__name__)
STATE_FILE = "cond1_state.json"

# Гистерезис: абсолютный и относительный
EPS_ABS = 1e-10
EPS_REL = 1e-6  # ~0.0001% relative tolerance


def _eps(a: float, b: float) -> float:
    base = max(abs(a), abs(b), 1.0)
    return max(EPS_ABS, EPS_REL * base)


def _flush_handlers():
    """Force flush on handlers (полезно для Render stdout buffering)."""
    root = logging.getLogger()
    for h in list(root.handlers) + list(logger.handlers):
        try:
            if hasattr(h, "flush"):
                h.flush()
        except Exception:
            pass


def load_state() -> Dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # corrupted -> ignore
            return {}
    return {}


def save_state(state: Dict):
    safe_state = {}
    for k, v in state.items():
        # JSON-serializable conversion for numpy types
        try:
            if hasattr(v, "item"):
                safe_state[k] = v.item()
            else:
                safe_state[k] = v
        except Exception:
            safe_state[k] = str(v)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(safe_state, f)


def _is_real_cross(prev_a: float, prev_b: float, curr_a: float, curr_b: float, cross_type: str) -> bool:
    """
    Проверка настоящего пересечения:
    - касание (==) не считается
    - пересечение есть только при строгой смене знака разности
    """

    # Разности
    prev_diff = prev_a - prev_b
    curr_diff = curr_a - curr_b

    # Касание (равенство хотя бы в одной точке) → не пересечение
    if prev_diff == 0 or curr_diff == 0:
        return False

    # Смена знака (строгое пересечение)
    crossed = (prev_diff * curr_diff) < 0

    if not crossed:
        return False

    # Проверка направления
    if cross_type == "long":
        return prev_diff < 0 and curr_diff > 0  # снизу вверх
    elif cross_type == "short":
        return prev_diff > 0 and curr_diff < 0  # сверху вниз
    else:
        return False


def _is_touch(a: float, b: float, eps: float = 1e-9) -> bool:
    """
    Касание EMA: значения настолько близки, что считаем их равными.
    Используется перед проверкой пересечения.
    """
    return abs(a - b) < eps


def _last_cross_pos(series_a: pd.Series, series_b: pd.Series, cross_type: str, lookback: int = 200) -> Optional[int]:
    """
    Ищет последнее подтвержденное пересечение (позиция в серии, 0-based).
    Ищет среди последних `lookback` точек, включая последнюю точку серии.
    Возвращает position (int) или None.
    """
    n = len(series_a)
    if n < 2:
        return None
    start = max(1, n - lookback)
    for i in range(n - 1, start - 1, -1):
        prev_a, prev_b = series_a.iat[i - 1], series_b.iat[i - 1]
        curr_a, curr_b = series_a.iat[i], series_b.iat[i]
        if _is_real_cross(prev_a, prev_b, curr_a, curr_b, cross_type):
            return i
    return None


def _tf_seconds_for_5m() -> int:
    """Возвращает длительность 5m в секундах — значение фиксированное: 300s."""
    return 5 * 60


def check_cond_1(df_by_tf, direction: str) -> Tuple[bool, Dict]:
    """
    Основная функция проверки условия 1.

    Возвращает (ok: bool, info: dict).
    Если ok==True -> info содержит "cond" и "start_index" (позиция свечи в df5, int).
    """
    # Проверки наличия TF
    if "5m" not in df_by_tf:
        info = {"cond": 1, "reason": "Нет 5m Данных"}
        logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
        _flush_handlers()
        return False, info

    df5: pd.DataFrame = df_by_tf["5m"]

    # Требуем столбцы ema5, ema10, ema21 и time
    for col in ("ema5", "ema10", "ema21", "time"):
        if col not in df5.columns:
            info = {"cond": 1, "reason": f"Нет колонки {col} в df5"}
            logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
            _flush_handlers()
            return False, info

    if len(df5) < 3:
        info = {"cond": 1, "reason": "Недостаточно данных (нужны >=3 свечи)"}
        logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
        _flush_handlers()
        return False, info

    ema5 = df5["ema5"]
    ema10 = df5["ema10"]
    ema21 = df5["ema21"]

    cross_type = "up" if direction == "long" else "down"

    # Определим, закрыта ли последняя свеча (по таймстемпу)
    try:
        last_row_ts = int(df5["time"].iat[-1])  # секундный epoch
        now_ts = int(time.time())
        tf_seconds = _tf_seconds_for_5m()
        last_bar_closed = (now_ts >= (last_row_ts + tf_seconds))
    except Exception:
        # Если что-то странное с time -> считаем, что последняя свеча закрыта (fallback)
        last_bar_closed = True

    # Выбираем позицию "последней закрытой свечи"
    if last_bar_closed:
        last_closed_pos = len(df5) - 1
    else:
        # Если последняя ещё формируется, используем предпоследнюю как закрытую
        last_closed_pos = len(df5) - 2

    # Safety check
    if last_closed_pos < 1:
        info = {"cond": 1, "reason": "Недостаточно закрытых свечей для проверки"}
        logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
        _flush_handlers()
        return False, info

    # --- DEBUG: логируем две последние закрытые свечи (для отладки ложных сигналов) ---
    try:
        prev_closed_pos = last_closed_pos - 1
        debug_prev = {
            "pos": int(prev_closed_pos),
            "time": int(df5["time"].iat[prev_closed_pos]),
            "ema5": float(ema5.iat[prev_closed_pos]),
            "ema10": float(ema10.iat[prev_closed_pos]),
            "ema21": float(ema21.iat[prev_closed_pos]),
        }
        debug_last = {
            "pos": int(last_closed_pos),
            "time": int(df5["time"].iat[last_closed_pos]),
            "ema5": float(ema5.iat[last_closed_pos]),
            "ema10": float(ema10.iat[last_closed_pos]),
            "ema21": float(ema21.iat[last_closed_pos]),
        }
        logger.info("[P1][DEBUG] last_bar_closed=%s last_closed_pos=%s now=%s last_ts=%s",
                    last_bar_closed, last_closed_pos, int(time.time()), debug_last["time"])
        logger.info("[P1][DEBUG] prev_closed: pos=%s ema5=%.12f ema10=%.12f ema21=%.12f",
                    debug_prev["pos"], debug_prev["ema5"], debug_prev["ema10"], debug_prev["ema21"])
        logger.info("[P1][DEBUG] last_closed: pos=%s ema5=%.12f ema10=%.12f ema21=%.12f",
                    debug_last["pos"], debug_last["ema5"], debug_last["ema10"], debug_last["ema21"])
        _flush_handlers()
    except Exception:
        # не критично
        pass

    # --- Найдём последнее пересечение EMA5/EMA21 внутри окна (включая last_closed_pos) ---
    # Работаем на срезе series до last_closed_pos включительно
    try:
        slice_a = ema5.iloc[: last_closed_pos + 1]
        slice_b = ema21.iloc[: last_closed_pos + 1]
        cross5_pos = _last_cross_pos(slice_a, slice_b, cross_type=cross_type, lookback=200)
    except Exception as e:
        logger.exception("[P1] _last_cross_pos failed: %s", e); _flush_handlers()
        cross5_pos = None

    # Загрузка состояния
    state = load_state()
    waiting = bool(state.get("waiting", False))
    start_pos = state.get("start_pos")  # int or None
    wait_cross_type = state.get("cross_type")
    last_signal_pos = state.get("last_signal_pos")
    last_signal_dir = state.get("last_signal_dir")

    # Если обнаружили новое пересечение EMA5/EMA21 — (re)start ожидания
    if cross5_pos is not None:
        # cross5_pos — позиция в slice (0..last_closed_pos), т.е. позиция в df5
        # Если состояние старое или другой тип — стартуем
        if (not waiting) or (start_pos is None) or (int(cross5_pos) != int(start_pos)) or (wait_cross_type != cross_type):
            waiting = True
            start_pos = int(cross5_pos)
            wait_cross_type = cross_type
            state["waiting"] = waiting
            state["start_pos"] = start_pos
            state["cross_type"] = wait_cross_type
            logger.info("[P1] ℹ️ Detected ema5/21 cross at pos=%s type=%s -> start waiting", start_pos, wait_cross_type)
            _flush_handlers()
            save_state(state)

    # Если сейчас в режиме ожидания и тип совпадает — проверяем окно X+1..X+4 и сбрасываем на X+5
    if waiting and (wait_cross_type == cross_type) and (start_pos is not None):
        # Если start_pos расположен позже last_closed_pos (маловероятно), не можем ничего сделать
        if start_pos >= last_closed_pos:
            # возможно, пересечение случилось на текущей ещё формирующейся свече (edge) — ждём следующую закрытую свечу
            info = {"cond": 1, "reason": "Ждём следующей закрытой свечи после EMA5/21 пересечения"}
            logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
            _flush_handlers()
            return False, info

        bars_since = last_closed_pos - start_pos  # 0..inf, 0 означает, что последняя закрытая свеча — та самая, где был start_pos
        # Timeout: на X+5 (bars_since >=5) сбрасываем
        if bars_since >= 5:
            # timeout -> сброс
            state["waiting"] = False
            state["start_pos"] = None
            state["cross_type"] = None
            save_state(state)
            info = {"cond": 1, "reason": "Нет подтвержденного пересечения EMA10/21 в допустимом диапазоне"}
            logger.info("[P1] ⏱ timeout: bars_since=%s -> %s", bars_since, json.dumps(info, ensure_ascii=False))
            _flush_handlers()
            return False, info

        # Проверяем ТОЛЬКО текущую последнюю закрытую свечу (last_closed_pos)
        prev_pos = last_closed_pos - 1
        if prev_pos < 0:
            info = {"cond": 1, "reason": "Недостаточно предыдущих данных для проверки пересечения EMA10/21"}
            logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
            _flush_handlers()
            return False, info

        prev_ema10, prev_ema21 = float(ema10.iat[prev_pos]), float(ema21.iat[prev_pos])
        curr_ema10, curr_ema21 = float(ema10.iat[last_closed_pos]), float(ema21.iat[last_closed_pos])

        # Касание — не сигнал
        if _is_touch(curr_ema10, curr_ema21):
            info = {"cond": 1, "reason": "EMA10 коснулась EMA21, ждем следующей свечи"}
            logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
            _flush_handlers()
            return False, info

        # Реальное пересечение
        if _is_real_cross(prev_ema10, prev_ema21, curr_ema10, curr_ema21, cross_type):
            # Защита от дублирования (persist) по позиции последней сигнальной свечи
            if last_signal_pos is not None and last_signal_dir == cross_type and int(last_signal_pos) == int(last_closed_pos):
                info = {"cond": 1, "reason": "Сигнал уже был (persist)"}
                logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
                _flush_handlers()
                return False, info

            # Успех — формируем сигнал. Сохраняем и очищаем ожидание.
            state["waiting"] = False
            state["start_pos"] = None
            state["cross_type"] = None
            state["last_signal_pos"] = int(last_closed_pos)
            state["last_signal_dir"] = cross_type
            save_state(state)

            info = {"cond": 1, "start_index": int(start_pos)}
            logger.info("[P1] ✅ reason=%s values=%s", "EMA10 пересекла EMA21, сигнал готов", json.dumps(info, ensure_ascii=False))
            _flush_handlers()
            return True, info
        else:
            # Пока пересечения нет — ждём дальше (до timeout)
            info = {"cond": 1, "reason": "Ждем подтвержденного пересечения EMA10/21"}
            logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
            _flush_handlers()
            return False, info

    # Если не в ожидании — no_start
    info = {"cond": 1, "reason": "no_start"}
    logger.info("[P1] SUMMARY: no_start | impulse_tf=None | direction=None")
    logger.info("[P1] ❌ reason=%s values=%s", info["reason"], json.dumps(info, ensure_ascii=False))
    _flush_handlers()
    return False, info