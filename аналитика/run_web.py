"""
Веб-интерфейс YT Analytics через локальный HTTP-сервер + браузер.
Работает на Python 3.11–3.15 без pywebview/pythonnet.

Запуск:
    python run_web.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from web_server import run_server, PORT


def main():
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(open_browser=True, port=port)


if __name__ == "__main__":
    main()
