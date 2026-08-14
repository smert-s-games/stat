# Восстановление main.py

Сейчас `аналитика/main.py` на ветке `main` повреждён (заглушка).
Рабочая версия есть в коммите `ac793be0`.

## Быстрое восстановление

```bash
git fetch origin
git checkout ac793be0f996acaa1254bdba8a7bf39bf0e53f19 -- "аналитика/main.py"
python3 apply_fixes.py
git add "аналитика/main.py"
git commit -m "Restore main.py + fix theme switch and notifications"
git push origin main
```

Или скопируй файл `main.py` из коммита/вложения поверх `аналитика/main.py`, затем:

```bash
python3 apply_fixes.py
git add аналитика/main.py && git commit -m "Restore main.py with fixes" && git push
```

## Что чинит apply_fixes.py

1. **Тема** — больше не уничтожает notebook/status_bar при смене темы
2. **Уведомления** — после показа помечаются прочитанными

Парсер (`modules/stats_parser.py`) уже оптимизирован и на месте.
