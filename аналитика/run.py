"""
Точка входа YouTube Analytics с патчами (тема + уведомления).
Запуск: python run.py
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import tkinter as tk

import main as app_module
from modules.patches import apply_patches

apply_patches(app_module.AnalyticsApp)


def main():
    root = tk.Tk()
    app = app_module.AnalyticsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
