# Веб-интерфейс YT Analytics

Настоящий HTML/CSS UI через [pywebview](https://pywebview.flowrl.com/).

## Установка

```bash
pip install pywebview
# Windows: обычно достаточно
# Linux: может понадобиться python3-gi / WebKit
```

## Запуск

Из папки `аналитика`:

```bash
python run_web.py
```

Старый Tkinter-интерфейс:

```bash
python run.py
```

## Структура

- `index.html` — разметка
- `css/styles.css` — стили (CSS-переменные, светлая/тёмная тема)
- `js/app.js` — фронтенд
- `../web_api.py` — Python API для JS
- `../run_web.py` — точка входа
