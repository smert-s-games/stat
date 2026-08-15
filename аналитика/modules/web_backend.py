"""API backend: projects, sessions, stats, expenses."""
from __future__ import annotations

import json
import os
import sys
import threading
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from modules.stats_parser import StatsParser
from modules.account_manager import AccountManager
from modules.database import Database
from modules.stats_history import StatsHistory
from modules.export_manager import ExportManager
from modules.project_store import ProjectStore

try:
    from modules.stats_parser_ext import install_stats_parser_ext
    install_stats_parser_ext(StatsParser)
except Exception:
    pass

try:
    from modules.telegram_bot import TelegramBotManager
except Exception:
    TelegramBotManager = None


def _is_error_result(r: dict) -> bool:
    if not r:
        return True
    if r.get("error"):
        return True
    blob = (str(r.get("status", "")) + " " + str(r.get("error", "")) + " " + str(r.get("channel_name", ""))).lower()
    return any(t in blob for t in ("404", "not found", "не найден", "ошибка", "error", "timeout", "таймаут"))


def sort_stats(results: list, mode: str = "default") -> list:
    items = list(results or [])
    ok = [r for r in items if not _is_error_result(r)]
    bad = [r for r in items if _is_error_result(r)]
    parser = StatsParser()

    def num(r, key):
        return parser.parse_number(r.get(key, "0"))

    if mode == "name":
        ok.sort(key=lambda r: str(r.get("channel_name") or "").lower())
    elif mode == "subs_desc":
        ok.sort(key=lambda r: num(r, "subscribers"), reverse=True)
    elif mode == "subs_asc":
        ok.sort(key=lambda r: num(r, "subscribers"))
    elif mode == "views_desc":
        ok.sort(key=lambda r: num(r, "total_views"), reverse=True)
    elif mode == "views_asc":
        ok.sort(key=lambda r: num(r, "total_views"))
    elif mode == "videos_desc":
        ok.sort(key=lambda r: num(r, "videos_count"), reverse=True)
    return ok + bad


def sort_accounts(accounts: list, mode: str = "materials_desc") -> list:
    items = list(accounts or [])

    def key_materials(a):
        try:
            return int(a.get("materials_count") or 0)
        except Exception:
            return 0

    def key_size(a):
        try:
            return int(a.get("size_bytes") or 0)
        except Exception:
            return 0

    def quality_rank(a):
        q = str(a.get("quality_score") or "")
        if "Отлично" in q:
            return 3
        if "Хорошо" in q:
            return 2
        if "Удовлетворительно" in q:
            return 1
        return 0

    if mode == "name":
        items.sort(key=lambda a: str(a.get("name") or "").lower())
    elif mode == "materials_desc":
        items.sort(key=key_materials, reverse=True)
    elif mode == "materials_asc":
        items.sort(key=key_materials)
    elif mode == "size_desc":
        items.sort(key=key_size, reverse=True)
    elif mode == "size_asc":
        items.sort(key=key_size)
    elif mode == "quality_desc":
        items.sort(key=quality_rank, reverse=True)
    elif mode == "quality_asc":
        items.sort(key=quality_rank)
    return items


class WebAPI:
    def __init__(self, window=None):
        self.window = window
        self.config_file = str(BASE / "config.json")
        self.config = self._load_legacy_config()
        self.store = ProjectStore()
        self.stats_parser = StatsParser()
        self.account_manager = AccountManager()
        self.database = Database(str(BASE / "analytics.db"))
        self.stats_history = StatsHistory(self.database)
        self.export_manager = ExportManager()
        self.telegram_bot = TelegramBotManager(self.config_file) if TelegramBotManager else None
        self.current_stats = []
        self.current_accounts = []
        self._stats_running = False
        self._video_process = None
        self._video_stop = False
        self._bot_running = False
        self._restore_session()

    def _load_legacy_config(self) -> dict:
        default = {"theme": "light", "telegram_bot_token": "", "telegram_chat_id": ""}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                default.update(json.load(f))
        except Exception:
            pass
        return default

    def _save_legacy_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("config save error:", e)

    def _restore_session(self):
        p = self.store.get_active()
        if p:
            self.current_stats = sort_stats(p.get("last_stats") or [], p.get("stats_sort") or "default")
        self.current_accounts = []

    def _proj(self) -> dict:
        return self.store.get_active() or {}

    def _js(self, code: str):
        if self.window:
            try:
                self.window.evaluate_js(code)
            except Exception as e:
                print("JS eval error:", e)

    def _js_str(self, s: str) -> str:
        return json.dumps(s, ensure_ascii=False)

    def list_projects(self):
        return {"projects": self.store.list_projects(), "active_id": self.store.get_active_id()}

    def create_project(self, name: str):
        p = self.store.create_project(name)
        self._restore_session()
        return {"ok": True, "project": {"id": p["id"], "name": p["name"]}}

    def switch_project(self, pid: str):
        res = self.store.set_active(pid)
        if res.get("error"):
            return res
        self._restore_session()
        return {"ok": True, "id": pid}

    def rename_project(self, pid: str, name: str):
        return self.store.rename_project(pid, name)

    def delete_project(self, pid: str):
        res = self.store.delete_project(pid)
        if not res.get("error"):
            self._restore_session()
        return res

    def get_config(self):
        p = self._proj()
        return {
            "theme": self.config.get("theme", "light"),
            "links_file": p.get("links_file", ""),
            "proxy": p.get("proxy") or {"purchase_date": "", "expiry_date": ""},
            "server": p.get("server") or {"purchase_date": "", "expiry_date": ""},
            "telegram_bot_token": self.config.get("telegram_bot_token", ""),
            "telegram_chat_id": self.config.get("telegram_chat_id", ""),
            "accounts_folders": p.get("accounts_folders") or [],
            "project_id": p.get("id", ""),
            "project_name": p.get("name", ""),
            "stats_sort": p.get("stats_sort") or "default",
            "accounts_sort": p.get("accounts_sort") or "materials_desc",
            "has_cached_stats": bool(p.get("last_stats")),
        }

    def toggle_theme(self):
        cur = self.config.get("theme", "light")
        self.config["theme"] = "dark" if cur == "light" else "light"
        self._save_legacy_config()
        return {"theme": self.config["theme"]}

    def set_links_file(self, path: str):
        path = (path or "").strip()
        if not path:
            return {"error": "пустой путь"}
        self.store.update_active(links_file=path)
        return {"ok": True, "path": path}

    def open_url(self, url: str):
        if url and str(url).startswith("http"):
            webbrowser.open(url)
        return True

    def get_dashboard(self):
        p = self._proj()
        channels = views = subs = 0
        fmt = self.stats_parser.format_large_number
        for r in self.current_stats:
            if _is_error_result(r):
                continue
            channels += 1
            try:
                views += self.stats_parser.parse_number(r.get("total_views", "0"))
                subs += self.stats_parser.parse_number(r.get("subscribers", "0"))
            except Exception:
                pass
        proxy = p.get("proxy") or {}
        server = p.get("server") or {}

        def days_left(expiry):
            if not expiry:
                return None
            try:
                return (datetime.strptime(expiry, "%d.%m.%Y") - datetime.now()).days
            except ValueError:
                return None

        pe, se = proxy.get("expiry_date", ""), server.get("expiry_date", "")
        pd, sd = days_left(pe), days_left(se)
        exp = self.store.expenses_summary()
        lines = [
            f"<p><strong>📁 Проект:</strong> {p.get('name', '—')}</p>",
            f"<p><strong>📡 Прокси</strong><br>Окончание: {pe or 'не указано'}" + (f"<br>Осталось: {pd} дн." if pd is not None else "") + "</p>",
            f"<p><strong>🖥️ Сервер</strong><br>Окончание: {se or 'не указано'}" + (f"<br>Осталось: {sd} дн." if sd is not None else "") + "</p>",
            f"<p><strong>💸 Расходы проекта:</strong> {exp['total']:.2f} ({exp['count']} записей)</p>",
        ]
        return {"channels": channels or "—", "views": fmt(views) if channels else "—", "subs": fmt(subs) if channels else "—", "accounts": len(self.current_accounts) or "—", "proxy_html": "".join(lines), "project_name": p.get("name", ""), "expenses_total": exp["total"]}

    def get_cached_stats(self):
        p = self._proj()
        results = sort_stats(p.get("last_stats") or [], p.get("stats_sort") or "default")
        self.current_stats = results
        return results

    def start_parse(self):
        if self._stats_running:
            return {"error": "Парсинг уже выполняется"}
        p = self._proj()
        links = p.get("links_file") or "links.txt"
        if not os.path.isabs(links):
            links = str(BASE / links)
        if not os.path.exists(links):
            return {"error": f"Файл не найден: {links}"}
        self._stats_running = True

        def worker():
            try:
                def progress(current, total, link):
                    self._js(f"App.onParseProgress({self._js_str(f'[{current}/{total}] {link}\n')})")
                results = self.stats_parser.parse_channels(links, progress_callback=progress)
                cleaned = []
                for r in results or []:
                    if not isinstance(r, dict):
                        continue
                    if r.get("error"):
                        err = str(r["error"])
                        if "404" in err or "not found" in err.lower():
                            r["error"] = "404 Not Found"
                        cleaned.append(r)
                        continue
                    r.setdefault("email", "")
                    if (not r.get("channel_name") or r.get("channel_name") == "Неизвестно") and (r.get("subscribers") in (None, "", "Неизвестно", "0") and r.get("total_views") in (None, "", "0")):
                        r = {"url": r.get("url", ""), "error": "404 Not Found"}
                    cleaned.append(r)
                mode = (self._proj() or {}).get("stats_sort") or "default"
                cleaned = sort_stats(cleaned, mode)
                self.current_stats = cleaned
                try:
                    self.store.update_active(last_stats=cleaned)
                except Exception as e:
                    print("session save error:", e)
                try:
                    self.stats_history.save_stats(cleaned)
                    self.database.log_operation("stats_parse", f"Парсинг: {len(cleaned)} каналов")
                except Exception:
                    pass
                self._js(f"App.onParseDone({json.dumps(cleaned, ensure_ascii=False)})")
            except Exception as e:
                self._js(f"App.onParseProgress({self._js_str(chr(10)+'❌ '+str(e)+chr(10))})")
                self._js("App.onParseDone([])")
            finally:
                self._stats_running = False

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def sort_stats_results(self, mode: str):
        mode = mode or "default"
        self.store.update_active(stats_sort=mode)
        self.current_stats = sort_stats(self.current_stats, mode)
        try:
            self.store.update_active(last_stats=self.current_stats)
        except Exception:
            pass
        return self.current_stats

    def export_stats(self):
        if not self.current_stats:
            return {"error": "Нет данных для экспорта"}
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
        p = self._proj()
        folders = p.get("accounts_folders") or []
        accounts = []
        if folders:
            try:
                accounts = self.account_manager.scan_multiple_folders(folders)
            except Exception as e:
                return {"error": str(e), "folders": folders, "accounts": []}
        for a in accounts:
            a["folder_short"] = os.path.basename(a.get("folder", "")) or a.get("folder", "")
        accounts = sort_accounts(accounts, p.get("accounts_sort") or "materials_desc")
        self.current_accounts = accounts
        return {"folders": folders, "accounts": accounts}

    def sort_accounts_results(self, mode: str):
        mode = mode or "materials_desc"
        self.store.update_active(accounts_sort=mode)
        self.current_accounts = sort_accounts(self.current_accounts, mode)
        return self.current_accounts

    def add_accounts_folder(self, path: str):
        path = (path or "").strip()
        folders = list(self._proj().get("accounts_folders") or [])
        if path and path not in folders:
            folders.append(path)
            self.store.update_active(accounts_folders=folders)
        return True

    def remove_accounts_folder(self, path: str):
        folders = [f for f in (self._proj().get("accounts_folders") or []) if f != path]
        self.store.update_active(accounts_folders=folders)
        return True

    def get_video_scripts(self):
        scripts = self._proj().get("video_scripts") or []
        return [{"path": p, "name": os.path.basename(p), "exists": os.path.isfile(p)} for p in scripts]

    def add_video_script(self, path: str):
        path = os.path.abspath((path or "").strip())
        scripts = list(self._proj().get("video_scripts") or [])
        if path and path not in scripts:
            scripts.append(path)
            self.store.update_active(video_scripts=scripts)
        return True

    def remove_video_script(self, idx: int):
        scripts = list(self._proj().get("video_scripts") or [])
        if 0 <= idx < len(scripts):
            scripts.pop(idx)
            self.store.update_active(video_scripts=scripts)
        return True

    def run_video_script(self, idx: int):
        scripts = list(self._proj().get("video_scripts") or [])
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
                cf = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if sys.platform == "win32" else 0
                self._video_process = subprocess.Popen([sys.executable, "-u", path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", cwd=os.path.dirname(path) or None, bufsize=1, creationflags=cf)
                assert self._video_process.stdout
                for line in self._video_process.stdout:
                    if self._video_stop:
                        break
                    line = line.rstrip("\n\r")
                    if line:
                        self._js(f"App.onVideoLog({self._js_str(line)})")
                ok = (not self._video_stop) and self._video_process.poll() == 0
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

    def save_proxy(self, data=None, **kwargs):
        if data is None:
            data = kwargs
        if not isinstance(data, dict):
            data = {}
        proxy = {"purchase_date": str(data.get("purchase_date", "") or "").strip(), "expiry_date": str(data.get("expiry_date", "") or "").strip()}
        self.store.update_active(proxy=proxy)
        self.config["proxy"] = proxy
        self._save_legacy_config()
        return {"ok": True, "proxy": proxy}

    def save_server(self, data=None, **kwargs):
        if data is None:
            data = kwargs
        if not isinstance(data, dict):
            data = {}
        server = {"purchase_date": str(data.get("purchase_date", "") or "").strip(), "expiry_date": str(data.get("expiry_date", "") or "").strip()}
        self.store.update_active(server=server)
        self.config["server"] = server
        self._save_legacy_config()
        return {"ok": True, "server": server}

    def save_telegram(self, data=None, **kwargs):
        if data is None:
            data = kwargs
        if not isinstance(data, dict):
            data = {}
        self.config["telegram_bot_token"] = str(data.get("token", "") or "")
        self.config["telegram_chat_id"] = str(data.get("chat_id", "") or "")
        self._save_legacy_config()
        return {"ok": True}

    def get_expenses(self):
        return self.store.expenses_summary()

    def add_expense(self, amount, description="", category="", date=""):
        return self.store.add_expense(amount, description, category, date)

    def delete_expense(self, exp_id: str):
        return self.store.delete_expense(exp_id)

    def start_bot(self):
        if not self.telegram_bot:
            self._js(f"App.onBotLog({self._js_str('❌ Модуль Telegram недоступен')})")
            return {"error": "no bot module"}
        if self._bot_running:
            return {"error": "already running"}
        if not self.config.get("telegram_bot_token") or not self.config.get("telegram_chat_id"):
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
