def cond_1(df):
    """
    Условие 1:
    Срабатывает, если EMA5 или EMA10 пересекли EMA21 на последней свече.
    Игнорирует пересечение цены с EMA21.
    """
    try:
        ema5_prev = df["ema5"].iloc[-2]
        ema5_now = df["ema5"].iloc[-1]
        ema10_prev = df["ema10"].iloc[-2]
        ema10_now = df["ema10"].iloc[-1]
        ema21_prev = df["ema21"].iloc[-2]
        ema21_now = df["ema21"].iloc[-1]

        # Проверка на пересечение EMA5 и EMA21
        cross_ema5_up = ema5_prev < ema21_prev and ema5_now >= ema21_now
        cross_ema5_down = ema5_prev > ema21_prev and ema5_now <= ema21_now

        # Проверка на пересечение EMA10 и EMA21
        cross_ema10_up = ema10_prev < ema21_prev and ema10_now >= ema21_now
        cross_ema10_down = ema10_prev > ema21_prev and ema10_now <= ema21_now

        # Если хотя бы одно из пересечений произошло — сигнал есть
        crossed = cross_ema5_up or cross_ema5_down or cross_ema10_up or cross_ema10_down

        return crossed, {
            "ema5": ema5_now,
            "ema10": ema10_now,
            "ema21": ema21_now,
            "cross_ema5_up": cross_ema5_up,
            "cross_ema5_down": cross_ema5_down,
            "cross_ema10_up": cross_ema10_up,
            "cross_ema10_down": cross_ema10_down,
            "reason": "EMA5 или EMA10 пересекли EMA21"
        }

    except Exception as e:
        return False, {"error": str(e)}


# Пример остальных условий (cond_2, cond_3, ...), сюда вставляются твои текущие версии:
# ...