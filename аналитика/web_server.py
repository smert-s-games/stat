"""
Локальный HTTP-сервер для веб-UI (без pywebview).
Работает на Python 3.11–3.15, Windows/Linux.

Запуск: python run_web.py
"""
from __future__ import annotations

import json
import mimetypes
import queue
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

from web_api import WebAPI, BASE

WEB_DIR = BASE / "web"
HOST = "127.0.0.1"
PORT = 8765


class EventBus:
    """Очередь событий для SSE (прогресс парсинга, логи)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._subs: list[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=500)
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)

    def emit(self, event: str, data):
        payload = {"event": event, "data": data}
        with self._lock:
            dead = []
            for q in self._subs:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                try:
                    self._subs.remove(q)
                except ValueError:
                    pass


events = EventBus()
api = WebAPI(window=None)


def _bridge_js(code: str):
    """Перехват вызовов App.* из web_api → SSE."""
    try:
        if "App.onParseProgress(" in code:
            arg = code.split("App.onParseProgress(", 1)[1]
            arg = arg[: arg.rfind(")")]
            msg = json.loads(arg)
            events.emit("parse_progress", msg)
        elif "App.onParseDone(" in code:
            arg = code.split("App.onParseDone(", 1)[1]
            arg = arg[: arg.rfind(")")]
            data = json.loads(arg)
            events.emit("parse_done", data)
        elif "App.onVideoLog(" in code:
            arg = code.split("App.onVideoLog(", 1)[1]
            arg = arg[: arg.rfind(")")]
            msg = json.loads(arg)
            events.emit("video_log", msg)
        elif "App.onVideoDone(" in code:
            arg = code.split("App.onVideoDone(", 1)[1].strip().rstrip(")")
            ok = arg.lower() == "true"
            events.emit("video_done", ok)
        elif "App.onBotLog(" in code:
            arg = code.split("App.onBotLog(", 1)[1]
            arg = arg[: arg.rfind(")")]
            msg = json.loads(arg)
            events.emit("bot_log", msg)
    except Exception as e:
        print("bridge parse error:", e, code[:120])


api._js = _bridge_js  # type: ignore


def _set_links_file(path: str):
    path = (path or "").strip()
    if not path:
        return {"error": "пустой путь"}
    api.config["links_file"] = path
    api._save_config()
    return {"ok": True, "path": path}


if not hasattr(api, "set_links_file"):
    api.set_links_file = _set_links_file  # type: ignore


class Handler(BaseHTTPRequestHandler):
    server_version = "YTAnalytics/1.0"

    def log_message(self, fmt, *args):
        if args and str(args[0]).startswith("GET /api/events"):
            return
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/events":
            self._sse()
            return

        if path.startswith("/api/"):
            self._json(404, {"error": "not found"})
            return

        if path in ("/", "", "/index.html"):
            rel = "index.html"
        else:
            rel = path.lstrip("/").replace("..", "")

        file_path = (WEB_DIR / rel).resolve()
        if not str(file_path).startswith(str(WEB_DIR.resolve())) or not file_path.is_file():
            self._json(404, {"error": "file not found"})
            return

        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return

        if path == "/api/rpc":
            method = body.get("method")
            args = body.get("args") or []
            kwargs = body.get("kwargs") or {}
            if not method or not isinstance(method, str):
                self._json(400, {"error": "method required"})
                return
            if method.startswith("_"):
                self._json(403, {"error": "forbidden"})
                return
            fn = getattr(api, method, None)
            if not callable(fn):
                self._json(404, {"error": f"unknown method: {method}"})
                return
            try:
                result = fn(*args, **kwargs)
                self._json(200, {"ok": True, "result": result})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return

        self._json(404, {"error": "not found"})

    def _json(self, code: int, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()

        q = events.subscribe()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    item = q.get(timeout=15)
                    line = f"event: {item['event']}\ndata: {json.dumps(item['data'], ensure_ascii=False)}\n\n"
                    self.wfile.write(line.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            events.unsubscribe(q)


def run_server(open_browser: bool = True, port: int = PORT):
    if not WEB_DIR.is_dir():
        raise SystemExit(f"Не найдена папка UI: {WEB_DIR}")

    httpd = ThreadingHTTPServer((HOST, port), Handler)
    url = f"http://{HOST}:{port}/"
    print("=" * 50)
    print("  YT Analytics — веб-интерфейс")
    print(f"  Откройте в браузере: {url}")
    print("  Остановка: Ctrl+C")
    print("=" * 50)

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
