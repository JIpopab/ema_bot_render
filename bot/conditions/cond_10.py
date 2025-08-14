
# bot/conditions/cond_10.py
from typing import Tuple, Dict
from .cond_8 import check_cond_8 as check30
from .cond_9 import check_cond_9 as check1h

def check_cond_10(df_by_tf, direction: str, start_idx: int) -> Tuple[bool, Dict]:
    df = dict(df_by_tf)

    df_10_1 = dict(df)
    df_10_1["30m"] = df["1H"]
    ok_a, info_a = check30(df_10_1, direction, start_idx)

    df_10_2 = dict(df)
    if "2H" not in df:
        return False, {"cond": 10, "reason": "Нет 2H в данных"}
    df_10_2["1H"] = df["2H"]
    ok_b, info_b = check1h(df_10_2, direction, start_idx)

    if ok_a and ok_b:
        return True, {"cond": 10, "note": "Перенос TF (30m→1h, 1h→2h) активирован", "impulse_tf": "1h/2h"}
    return False, {"cond": 10, "reason": f"Перенос TF не прошёл: p8_on_1h={ok_a}, p9_on_2h={ok_b}"}
