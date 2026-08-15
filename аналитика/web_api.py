"""
API для веб-интерфейса (pywebview).
Связывает HTML/JS с модулями парсинга, аккаунтов, видео и т.д.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from modules.stats_parser import StatsParser
from modules.account_manager import AccountManager
from modules.database import Database
from modules.stats_history import StatsHistory
from modules.export_manager import ExportManager

try:
    from modules.stats_parser_ext import install_stats_parser_ext
    install_stats_parser_ext(StatsParser)
except Exception:
    pass

try:
    from modules.telegram_bot import TelegramBotManager
except Exception:
    TelegramBotManager = None


class WebAPI:
    def __init__(self, window=None):
        self.window = window
        self.config_file = str(BASE / "config.json")
        self.config = self._load_config()
        self.stats_parser = StatsParser()
        self.account_manager = AccountManager()
        self.database = Database()
        self.stats_history = StatsHistory(self.database)
        self.export_manager = ExportManager()
        self.telegram_bot = TelegramBotManager(self.config_file) if TelegramBotManager else None

        self.current_stats = []
        self.current_accounts = []
        self._stats_running = False
        self._accounts_running = False
        self._video_process = None
        self._video_stop = False
        self._bot_running = False

    def _load_config(self):
        default = {
            "accounts_folders": [],
            "links_file": "links.txt",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "proxy": {"purchase_date": "", "expiry_date": ""},
            "server": {"purchase_date": "", "expiry_date": ""},
            "theme": "light",
            "video_scripts": [],
        }
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            default.update(data)
        except Exception:
            pass
        return default

    def _save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_config(self):
        return {
            "theme": self.config.get("theme", "light"),
            "links_file": self.config.get("links_file", ""),
            "proxy": self.config.get("proxy", {}),
            "server": self.config.get("server", {}),
            "telegram_bot_token": self.config.get("telegram_bot_token", ""),
            "telegram_chat_id": self.config.get("telegram_chat_id", ""),
            "accounts_folders": self.config.get("accounts_folders", []),
        }

    def toggle_theme(self):
        cur = self.config.get("theme", "light")
        self.config["theme"] = "dark" if cur == "light" else "light"
        self._save_config()
        return {"theme": self.config["theme"]}

    def _js(self, code: str):
        if self.window:
            try:
                self.window.evaluate_js(code)
            except Exception as e:
                print("JS eval error:", e)

    def _js_str(self, s: str) -> str:
        return json.dumps(s, ensure_ascii=False)

    def open_url(self, url: str):
        if url and url.startswith("http"):
            webbrowser.open(url)
        return True

    def pick_file(self, title="Выберите файл", filetypes=None):
        import webview
        ft = ("All files (*.*)",)
        if filetypes:
            ft = tuple(f"{name} ({pat})" for name, pat in filetypes)
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=False, file_types=ft
        )
        if result and len(result) > 0:
            path = result[0]
            if title and "ссылок" in title.lower():
                self.config["links_file"] = path
                self._save_config()
            return path
        return None

    def pick_folder(self, title="Выберите папку"):
        import webview
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return result[0]
        return None

    def get_dashboard(self):
        channels = views = subs = 0
        fmt = self.stats_parser.format_large_number
        for r in self.current_stats:
            if "error" in r:
                continue
            channels += 1
            try:
                views += self.stats_parser.parse_number(r.get("total_views", "0"))
                subs += self.stats_parser.parse_number(r.get("subscribers", "0"))
            except Exception:
                pass

        proxy = self.config.get("proxy", {})
        server = self.config.get("server", {})

        def days_left(expiry):
            if not expiry:
                return None
            try:
                return (datetime.strptime(expiry, "%d.%m.%Y") - datetime.now()).days
            except ValueError:
                return None

        pe, se = proxy.get("expiry_date", ""), server.get("expiry_date", "")
        pd, sd = days_left(pe), days_left(se)
        lines = [
            f"<p><strong>📡 Прокси</strong><br>Окончание: {pe or 'не указано'}"
            + (f"<br>Осталось: {pd} дн." if pd is not None else "")
            + "</p>",
            f"<p><strong>🖥️ Сервер</strong><br>Окончание: {se or 'не указано'}"
            + (f"<br>Осталось: {sd} дн." if sd is not None else "")
            + "</p>",
        ]
        return {
            "channels": channels or "—",
            "views": fmt(views) if channels else "—",
            "subs": fmt(subs) if channels else "—",
            "accounts": len(self.current_accounts) or "—",
            "proxy_html": "".join(lines),
        }

    def start_parse(self):
        if self._stats_running:
            return {"error": "Парсинг уже выполняется"}
        links = self.config.get("links_file", "links.txt")
        if not links or not os.path.exists(links):
            return {"error": f"Файл не найден: {links}"}

        self._stats_running = True

        def worker():
            try:
                def progress(current, total, link):
                    msg = f"[{current}/{total}] {link}\n"
                    self._js(f"App.onParseProgress({self._js_str(msg)})")

                results = self.stats_parser.parse_channels(links, progress_callback=progress)
                self.current_stats = results or []
                try:
                    self.stats_history.save_stats(self.current_stats)
                    self.database.log_operation(
                        "stats_parse", f"Парсинг: {len(self.current_stats)} каналов"
                    )
                except Exception:
                    pass
                payload = json.dumps(self.current_stats, ensure_ascii=False)
                self._js(f"App.onParseDone({payload})")
            except Exception as e:
                self._js(f"App.onParseProgress({self._js_str(chr(10) + '❌ ' + str(e) + chr(10))})")
                self._js("App.onParseDone([])")
            finally:
                self._stats_running = False

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def export_stats(self):
        if not self.current_stats:
            return {"error": "Нет данных для экспорта — сначала запустите парсинг"}
        try:
            path = self.export_manager.export_stats_to_excel(self.current_stats)
            return {"ok": True, "path": str(path)}
        except Exception:
            try:
                out = BASE / f"export_stats_{datetime.now():%Y%m%d_%H%M%S}.json"
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(self.current_stats, f, ensure_ascii=False, indent=2)
                return {"ok": True, "path": str(out)}
            except Exception as e2:
                return {"error": str(e2)}

    def refresh_accounts(self):
        folders = self.config.get("accounts_folders", []) or []
        accounts = []
        if folders:
            try:
                accounts = self.account_manager.scan_multiple_folders(folders)
            except Exception as e:
                return {"error": str(e), "folders": folders, "accounts": []}
        self.current_accounts = accounts or []
        for a in self.current_accounts:
            a["folder_short"] = os.path.basename(a.get("folder", "")) or a.get("folder", "")
        return {"folders": folders, "accounts": self.current_accounts}

    def add_accounts_folder(self, path: str):
        folders = self.config.get("accounts_folders") or []
        if path and path not in folders:
            folders.append(path)
            self.config["accounts_folders"] = folders
            self._save_config()
        return True

    def get_video_scripts(self):
        scripts = self.config.get("video_scripts") or []
        return [
            {"path": p, "name": os.path.basename(p), "exists": os.path.isfile(p)}
            for p in scripts
        ]

    def add_video_script(self, path: str):
        scripts = self.config.get("video_scripts") or []
        path = os.path.abspath(path)
        if path not in scripts:
            scripts.append(path)
            self.config["video_scripts"] = scripts
            self._save_config()
        return True

    def remove_video_script(self, idx: int):
        scripts = self.config.get("video_scripts") or []
        if 0 <= idx < len(scripts):
            scripts.pop(idx)
            self.config["video_scripts"] = scripts
            self._save_config()
        return True

    def run_video_script(self, idx: int):
        scripts = self.config.get("video_scripts") or []
        if not (0 <= idx < len(scripts)):
            return {"error": "Скрипт не выбран"}
        path = scripts[idx]
        if not os.path.isfile(path):
            return {"error": f"Файл не найден: {path}"}
        if self._video_process and self._video_process.poll() is None:
            return {"error": "Уже выполняется"}

        self._video_stop = False

        def worker():
            try:
                self._js(f"App.onVideoLog({self._js_str('▶ ' + path)})")
                creationflags = 0
                if sys.platform == "win32":
                    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                self._video_process = subprocess.Popen(
                    [sys.executable, "-u", path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=os.path.dirname(path) or None,
                    bufsize=1,
                    creationflags=creationflags,
                )
                assert self._video_process.stdout
                for line in self._video_process.stdout:
                    if self._video_stop:
                        break
                    line = line.rstrip("\n\r")
                    if line:
                        self._js(f"App.onVideoLog({self._js_str(line)})")
                code = self._video_process.poll()
                ok = (not self._video_stop) and code == 0
                self._js(f"App.onVideoDone({str(ok).lower()})")
            except Exception as e:
                self._js(f"App.onVideoLog({self._js_str('❌ ' + str(e))})")
                self._js("App.onVideoDone(false)")
            finally:
                self._video_process = None

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def stop_video_script(self):
        self._video_stop = True
        proc = self._video_process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._js("App.onVideoDone(false)")
        return True

    def save_proxy(self, data: dict):
        self.config["proxy"] = {
            "purchase_date": (data or {}).get("purchase_date", ""),
            "expiry_date": (data or {}).get("expiry_date", ""),
        }
        self._save_config()
        return True

    def save_server(self, data: dict):
        self.config["server"] = {
            "purchase_date": (data or {}).get("purchase_date", ""),
            "expiry_date": (data or {}).get("expiry_date", ""),
        }
        self._save_config()
        return True

    def save_telegram(self, data: dict):
        self.config["telegram_bot_token"] = (data or {}).get("token", "")
        self.config["telegram_chat_id"] = (data or {}).get("chat_id", "")
        self._save_config()
        return True

    def start_bot(self):
        if not self.telegram_bot:
            self._js(f"App.onBotLog({self._js_str('❌ Модуль Telegram недоступен')})")
            return {"error": "no bot module"}
        if self._bot_running:
            return {"error": "already running"}

        token = self.config.get("telegram_bot_token", "")
        chat = self.config.get("telegram_chat_id", "")
        if not token or not chat:
            return {"error": "token/chat required"}

        self._bot_running = True

        def worker():
            try:
                def cb(msg):
                    self._js(f"App.onBotLog({self._js_str(str(msg))})")

                self.telegram_bot.start(cb)
            except Exception as e:
                self._js(f"App.onBotLog({self._js_str('❌ ' + str(e))})")
            finally:
                self._bot_running = False

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def stop_bot(self):
        try:
            if self.telegram_bot:
                self.telegram_bot.stop()
        except Exception:
            pass
        self._bot_running = False
        self._js(f"App.onBotLog({self._js_str('⏹ Остановлен')})")
        return True
