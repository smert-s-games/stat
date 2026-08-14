"""
YouTube Analytics — главный файл временно неполный.

Полный main.py (~105 KB, класс AnalyticsApp) нужно восстановить один раз.

Как восстановить:

1) Через git (если клонировал репозиторий):

   git checkout 23c873d65548e2e94423cfba6536cdc68376e9b6 -- "аналитика/main.py"
   python3 аналитика/apply_fixes.py
   git add "аналитика/main.py"
   git commit -m "Restore main.py + theme/notification fixes"
   git push

2) Через сайт GitHub:
   - открой аналитика/main.py → Edit
   - вставь полный файл приложения (с class AnalyticsApp)
   - Commit
   - локально: python3 аналитика/apply_fixes.py && git push

Уже готово в репозитории:
- modules/stats_parser.py — оптимизированный парсер
- apply_fixes.py — фикс темы и уведомлений
- STATUS.md — описание статуса
"""

raise SystemExit(
    "main.py ещё не восстановлен. См. инструкцию в начале этого файла или аналитика/STATUS.md"
)
