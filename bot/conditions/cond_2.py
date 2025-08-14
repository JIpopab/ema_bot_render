
# bot/conditions/cond_2.py
from typing import Tuple, Dict
def check_cond_2(df_by_tf, direction: str) -> Tuple[bool, Dict]:
    """
    2) 5m: «плавный MACD»: последнее пересечение в сторону тренда не позднее 11 свеч назад,
       и |DIF-DEA| после кросса не превышает 70.
    """
    import pandas as pd
    from ..utils import last_cross_index
    df5 = df_by_tf["5m"]
    dif, dea = df5["macd_dif"], df5["macd_dea"]
    cross = last_cross_index(dif, dea, "up" if direction=="long" else "down", lookback=50)
    if cross is None or cross > 11:
        return False, {"cond": 2, "reason": "MACD: нет свежего кросса в сторону тренда ≤11 свеч"}
    i = len(df5) - cross - 1
    if abs(dif.iloc[i] - dea.iloc[i]) > 70:
        return False, {"cond": 2, "reason": f"MACD: |DIF-DEA|={abs(dif.iloc[i]-dea.iloc[i]):.1f} > 70"}
    return True, {"cond": 2}
