
# bot/checker.py
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
    results_agg = {"direction": None, "start_index": None, "by_cond": []}

    ok1, info1 = check_cond_1(df_by_tf, "long")
    if not ok1:
        ok1s, info1s = check_cond_1(df_by_tf, "short")
        if not ok1s:
            return False, {"reason": "Нет стартовой свечи ни для long, ни для short", "by_cond": [info1, info1s]}
        start_idx = info1s["start_index"]; direction = "short"; by_cond = [info1s]
    else:
        start_idx = info1["start_index"]; direction = "long"; by_cond = [info1]

    impulse_tf = "30m"

    checks = []
    for cid in [c for c in ENABLED_CONDITIONS if c in [2,3,4,5,6,7]]:
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
        checks.append((cid, ok, inf))

    ok8, inf8 = check_cond_8(df_by_tf, direction, start_idx); checks.append((8, ok8, inf8))
    ok9, inf9 = check_cond_9(df_by_tf, direction, start_idx); checks.append((9, ok9, inf9))

    ok10, inf10 = check_cond_10(df_by_tf, direction, start_idx); checks.append((10, ok10, inf10))
    if ok10:
        impulse_tf = "1h/2h"

    ok11, inf11 = check_cond_11(df_by_tf, direction, start_idx); checks.append((11, ok11, inf11))

    by_cond = by_cond + [inf for _,_,inf in checks]

    if STRICT_MODE:
        base_ok = all(ok for cid, ok, _ in checks if cid in ENABLED_CONDITIONS)
    else:
        base_ok = all(ok for cid, ok, _ in checks if cid in [2,3,4,5,6,7])
        path_30 = ok8 and ok9
        path_1h2h = ok10 and ok11
        base_ok = base_ok and (path_30 or path_1h2h)

    return base_ok, {
        "direction": direction,
        "start_index": start_idx,
        "impulse_tf": impulse_tf,
        "by_cond": by_cond
    }
