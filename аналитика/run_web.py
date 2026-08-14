"""
Веб-интерфейс YT Analytics (HTML/CSS через pywebview).
Запуск: python run_web.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

try:
    import webview
except ImportError:
    print("Установите pywebview:  pip install pywebview")
    sys.exit(1)

from web_api import WebAPI


def main():
    index = BASE / "web" / "index.html"
    if not index.exists():
        print(f"Не найден интерфейс: {index}")
        sys.exit(1)

    api = WebAPI()
    window = webview.create_window(
        title="YT Analytics",
        url=index.as_uri(),
        js_api=api,
        width=1280,
        height=840,
        min_size=(1000, 640),
    )
    api.window = window
    webview.start(debug=False)


if __name__ == "__main__":
    main()
