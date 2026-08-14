"""Главное приложение для аналитики YouTube каналов — entry point"""
from pathlib import Path
_base = Path(__file__).resolve().parent
_src = (_base / "modules" / "_main_part1.py").read_text(encoding="utf-8")
_src += (_base / "modules" / "_main_part2.py").read_text(encoding="utf-8")
exec(compile(_src, str(_base / "main.py"), "exec"), globals())
