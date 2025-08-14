# bot/checker.py (updated)
from typing import Dict, Tuple
import pandas as pd
from .config import ENABLED_CONDITIONS, STRICT_MODE
from .conditions.cond_1 import check_cond_1
from .conditions.cond_2 import check_cond_2
from .conditions.cond_3 import check_cond_3
from .conditions.cond_4 import check_cond_4
from .conditions.cond_5 import check_cond_5
from .conditions.cond_6 import check_cond_6
from .conditions.cond_7 import check_cond_7
from .conditions.cond_8 import check_cond_8
from .conditions.cond_9 import check_cond_9
from .conditions.cond_10 import check_cond_10
from .conditions.cond_11 import check_cond_11

def run_checks(df_by_tf: Dict[str, pd.DataFrame]) -> Tuple[bool, Dict]:
    """
    Enforced logic:
    - Conditions 1..7 are mandatory.
    - If 8 and 9 passed -> impulse_tf = '30m' => success.
    - Else try 10 (TF transfer) and require 11 -> impulse_tf = '1h/2h' => success.
    Returns (ok, result_dict) where result_dict contains per-condition details and overall summary.
    """
    result = {
        "by_cond": {},
        "direction": None,
        "start_index": None,
        "impulse_tf": None,
        "summary": "",
    }

    # 1) Detect start for long or short (cond_1)
    ok1_long, info1_long = check_cond_1(df_by_tf, "long")
    ok1_short, info1_short = check_cond_1(df_by_tf, "short")

    # Обработка ошибки отсутствующих EMA
    if "error" in info1_long or "error" in info1_short:
        result["by_cond"][1] = {"ok": False, "info_long": info1_long, "info_short": info1_short}
        result["summary"] = "wait_for_data"
        return False, result

    # Определяем направление
    if ok1_long and not ok1_short:
        direction = "long"
        info1 = info1_long
    elif ok1_short and not ok1_long:
        direction = "short"
        info1 = info1_short
    elif ok1_long and ok1_short:
        # выбираем более свежую свечу
        if info1_long.get("start_index", 0) >= info1_short.get("start_index", 0):
            direction = "long"
            info1 = info1_long
        else:
            direction = "short"
            info1 = info1_short
    else:
        result["by_cond"][1] = {"ok": False, "info_long": info1_long, "info_short": info1_short}
        result["summary"] = "no_start"
        return False, result

    result["direction"] = direction
    result["by_cond"][1] = {"ok": True, "info": info1}
    start_idx = info1.get("start_index")
    result["start_index"] = start_idx

    # Mandatory checks 2..7
    mandatory_ok = True
    for cid in [2,3,4,5,6,7]:
        if cid == 2:
            ok, inf = check_cond_2(df_by_tf, direction)
        elif cid == 3:
            ok, inf = check_cond_3(df_by_tf, direction, start_idx)
        elif cid == 4:
            ok, inf = check_cond_4(df_by_tf, direction, start_idx)
        elif cid == 5:
            ok, inf = check_cond_5(df_by_tf, direction, start_idx)
        elif cid == 6:
            ok, inf = check_cond_6(df_by_tf, direction, start_idx)
        elif cid == 7:
            ok, inf = check_cond_7(df_by_tf, direction)
        else:
            ok, inf = False, {"cond": cid, "reason": "unknown"}
        result["by_cond"][cid] = {"ok": ok, "info": inf}
        if not ok:
            mandatory_ok = False

    if not mandatory_ok:
        result["summary"] = "failed_mandatory_2_7"
        return False, result

    # Branch: check 8 & 9 (30m)
    ok8, inf8 = check_cond_8(df_by_tf, direction, start_idx)
    result["by_cond"][8] = {"ok": ok8, "info": inf8}
    ok9, inf9 = check_cond_9(df_by_tf, direction, start_idx)
    result["by_cond"][9] = {"ok": ok9, "info": inf9}

    if ok8 and ok9:
        result["impulse_tf"] = "30m"
        # mark 10/11 as skipped
        result["by_cond"][10] = {"ok": False, "info": {"note": "skipped, 8&9 satisfied"}}
        result["by_cond"][11] = {"ok": False, "info": {"note": "skipped, 8&9 satisfied"}}
        result["summary"] = "ok_30m_branch"
        return True, result

    # Else try transfer (10) and require 11
    ok10, inf10 = check_cond_10(df_by_tf, direction, start_idx)
    result["by_cond"][10] = {"ok": ok10, "info": inf10}
    if ok10:
        ok11, inf11 = check_cond_11(df_by_tf, direction, start_idx)
        result["by_cond"][11] = {"ok": ok11, "info": inf11}
        if ok11:
            result["impulse_tf"] = "1h/2h"
            result["summary"] = "ok_1h2h_branch"
            return True, result
        else:
            result["summary"] = "failed_11_after_10"
            return False, result

    result["summary"] = "failed_higher_tf_checks"
    return False, result