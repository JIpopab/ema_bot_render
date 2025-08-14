
# bot/conditions/cond_5.py
from typing import Tuple, Dict
def check_cond_5(df_by_tf, direction: str, start_idx: int) -> Tuple[bool, Dict]:
    """
    5) 5m: RSI6/RSI9/RSI21 «свободное пространство» на стартовой.
       Long: rsi6<70 или (rsi6>=70 и rsi6-rsi9>=4); rsi21<70 всегда.
       Short: rsi6>30 или (rsi6<=30 и rsi9-rsi6>=4); rsi21>30 всегда.
    """
    df5 = df_by_tf["5m"]; i = start_idx
    r6, r9, r21 = df5["rsi6"].iloc[i], df5["rsi9"].iloc[i], df5["rsi21"].iloc[i]
    if direction == "long":
        if not ( (r6 < 70 or (r6 >= 70 and (r6 - r9) >= 4)) and (r21 < 70) ):
            return False, {"cond": 5, "reason": f"5m RSI long: r6={r6:.1f}, r9={r9:.1f}, r21={r21:.1f}"}
    else:
        if not ( (r6 > 30 or (r6 <= 30 and (r9 - r6) >= 4)) and (r21 > 30) ):
            return False, {"cond": 5, "reason": f"5m RSI short: r6={r6:.1f}, r9={r9:.1f}, r21={r21:.1f}"}
    return True, {"cond": 5}
