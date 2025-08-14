def check_cond_1(df, direction):
    """
    Условие 1:
    На 5m TF: EMA10 пересекает EMA21 вслед за EMA5
    не позднее чем на 4-й свече после пересечения EMA5 через EMA21.

    :param df: pandas.DataFrame с колонками ema5, ema10, ema21
    :param direction: str ("long" или "short")
    :return: tuple (bool, dict)
    """
    try:
        # Определяем направление проверки
        long_mode = direction.lower() == "long"

        # Находим индекс последнего пересечения EMA5 с EMA21
        ema5_cross_idx = None
        for i in range(len(df) - 2, -1, -1):  # идём с конца назад
            ema5_prev, ema5_now = df["ema5"].iloc[i], df["ema5"].iloc[i + 1]
            ema21_prev, ema21_now = df["ema21"].iloc[i], df["ema21"].iloc[i + 1]

            if long_mode:
                if ema5_prev < ema21_prev and ema5_now >= ema21_now:
                    ema5_cross_idx = i + 1
                    break
            else:
                if ema5_prev > ema21_prev and ema5_now <= ema21_now:
                    ema5_cross_idx = i + 1
                    break

        if ema5_cross_idx is None:
            return False, {"reason": "Нет пересечения EMA5 с EMA21"}

        # Проверяем EMA10 в пределах следующих 4 свечей
        ema10_cross_ok = False
        for j in range(ema5_cross_idx, min(ema5_cross_idx + 5, len(df))):
            ema10_prev, ema10_now = df["ema10"].iloc[j - 1], df["ema10"].iloc[j]
            ema21_prev, ema21_now = df["ema21"].iloc[j - 1], df["ema21"].iloc[j]

            if long_mode:
                if ema10_prev < ema21_prev and ema10_now >= ema21_now:
                    ema10_cross_ok = True
                    break
            else:
                if ema10_prev > ema21_prev and ema10_now <= ema21_now:
                    ema10_cross_ok = True
                    break

        if not ema10_cross_ok:
            return False, {
                "reason": "EMA10 не пересек EMA21 в течение 4 свеч после EMA5",
                "ema5_cross_idx": ema5_cross_idx
            }

        return True, {
            "reason": f"EMA10 пересёк EMA21 в течение 4 свеч после EMA5 (направление: {direction})",
            "ema5_cross_idx": ema5_cross_idx,
            "ema5_cross_time": df.index[ema5_cross_idx],
            "ema10_cross_time": df.index[j],
            "ema5_last": df["ema5"].iloc[-1],
            "ema10_last": df["ema10"].iloc[-1],
            "ema21_last": df["ema21"].iloc[-1]
        }

    except Exception as e:
        return False, {"error": str(e)}