
# Telegram EMA Bot v2 (OKX, BTC-USDT-SWAP)

- TF: 5m, 15m, 30m, 1H, 2H
- Индикаторы: EMA(5/10/21/50/200), MACD(9,22,6), RSI(6/9/21), KDJ(9,3,3), StochRSI(9,8,3,3), ATR14, VolMA(5/10)
- Полная логика условий п.1–11 из ТЗ. Уведомления в Telegram: подробная отметка по каждому пункту + П/С уровни (ATR и свинги).

## Deploy (Render.com)
1. Репозиторий с файлами (в корне: `main.py`, `render.yaml`, `requirements.txt`, папка `bot/`).
2. В Render создайте Web Service из Git, укажите:
   - `startCommand`: `gunicorn main:app`
3. В Variables добавьте `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
4. Деплой. Эндпоинты:
   - `/` — статус «активен»
   - `/test` — тестовое сообщение в Telegram
   - `/status` — последнее отправленное событие

## Локальный запуск
```bash
pip install -r requirements.txt
python main.py
```
