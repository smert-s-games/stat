# Статус

## Готово
- Полный `main.py` (AnalyticsApp)
- Оптимизированный `modules/stats_parser.py`
- Фиксы темы и уведомлений через `modules/patches.py` + `run.py`

## Запуск
```bash
cd аналитика
pip install -r ../requirements.txt   # или requirements из корня
python run.py
```

`run.py` применяет патчи автоматически:
1. Смена темы не уничтожает UI
2. Уведомления помечаются прочитанными

Можно и `python main.py`, но без патчей темы/уведомлений.

## Опционально (вшить фиксы в main.py)
```bash
python3 apply_fixes.py
```
