"""
Главное приложение для аналитики YouTube каналов
"""
from pathlib import Path

_base = Path(__file__).resolve().parent
_src = "".join(
    (_base / "modules" / f"_main_part{i}.py").read_text(encoding="utf-8")
    for i in (1, 2, 3)
)
exec(compile(_src, str(_base / "main.py"), "exec"), globals())
