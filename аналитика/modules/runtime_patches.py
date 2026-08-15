"""Runtime patches: multi-proxy, themes, 404/status normalize after parse."""
from __future__ import annotations

import uuid


def _normalize_stats_results(results):
    cleaned = []
    for r in results or []:
        if not isinstance(r, dict):
            continue
        r = dict(r)
        r.setdefault("email", "")
        r.setdefault("url", r.get("url") or "")
        if r.get("error"):
            err = str(r.get("error") or "")
            low = err.lower()
            if "404" in err or "not found" in low or "не найден" in low:
                r["error"] = "404 Not Found"
            r["status"] = "❌"
            cleaned.append(r)
            continue
        name = (r.get("channel_name") or "").strip()
        subs = str(r.get("subscribers") or "")
        views = str(r.get("total_views") or "")
        emptyish = (
            (not name or name == "Неизвестно")
            and subs in ("", "Неизвестно", "0", "None")
            and views in ("", "0", "None", "Неизвестно")
        )
        if emptyish:
            cleaned.append(
                {
                    "url": r.get("url", ""),
                    "channel_name": name or r.get("url", ""),
                    "error": "404 Not Found",
                    "status": "❌",
                    "email": r.get("email") or "",
                    "subscribers": "—",
                    "total_views": "—",
                    "videos_count": "—",
                }
            )
            continue
        r["status"] = "✅"
        cleaned.append(r)
    return cleaned


def apply_webapi_patches(WebAPI):
    if getattr(WebAPI, "_runtime_patched", False):
        return WebAPI

    _orig_get_config = WebAPI.get_config
    _orig_save_proxy = WebAPI.save_proxy
    _orig_get_dashboard = WebAPI.get_dashboard

    def get_config(self):
        cfg = _orig_get_config(self)
        try:
            p = self._proj()
            cfg["proxies"] = list(p.get("proxies") or [])
            cfg["ui_theme"] = p.get("theme") or cfg.get("theme", "light")
        except Exception:
            cfg.setdefault("proxies", [])
        return cfg

    def set_theme(self, theme: str):
        themes = ["light", "dark", "midnight", "ocean", "forest", "sunset", "purple"]
        theme = theme if theme in themes else "light"
        self.config["theme"] = theme
        if hasattr(self, "_save_legacy_config"):
            self._save_legacy_config()
        try:
            self.store.update_active(theme=theme)
        except Exception:
            pass
        return {"theme": theme}

    def toggle_theme(self):
        themes = ["light", "dark", "midnight", "ocean", "forest", "sunset", "purple"]
        cur = self.config.get("theme", "light")
        try:
            i = themes.index(cur)
        except ValueError:
            i = 0
        return self.set_theme(themes[(i + 1) % len(themes)])

    def get_proxies(self):
        p = self._proj()
        return {"proxies": list(p.get("proxies") or [])}

    def add_proxy(self, data=None, **kwargs):
        if data is None:
            data = kwargs
        if not isinstance(data, dict):
            data = {}
        proxies = list(self._proj().get("proxies") or [])
        item = {
            "id": str(uuid.uuid4())[:8],
            "name": str(data.get("name") or ("Proxy %d" % (len(proxies) + 1))).strip(),
            "host": str(data.get("host") or "").strip(),
            "port": str(data.get("port") or "").strip(),
            "type": str(data.get("type") or "http").strip(),
            "login": str(data.get("login") or "").strip(),
            "password": str(data.get("password") or "").strip(),
            "purchase_date": str(data.get("purchase_date") or "").strip(),
            "expiry_date": str(data.get("expiry_date") or "").strip(),
            "notes": str(data.get("notes") or "").strip(),
        }
        proxies.append(item)
        self.store.update_active(proxies=proxies)
        if item.get("expiry_date"):
            legacy = {
                "purchase_date": item.get("purchase_date", ""),
                "expiry_date": item.get("expiry_date", ""),
            }
            self.store.update_active(proxy=legacy)
            self.config["proxy"] = legacy
            if hasattr(self, "_save_legacy_config"):
                self._save_legacy_config()
        return {"ok": True, "proxy": item, "proxies": proxies}

    def update_proxy(self, proxy_id: str, data=None, **kwargs):
        if data is None:
            data = kwargs
        if not isinstance(data, dict):
            data = {}
        proxies = list(self._proj().get("proxies") or [])
        for i, pr in enumerate(proxies):
            if pr.get("id") == proxy_id:
                for k in (
                    "name", "host", "port", "type", "login", "password",
                    "purchase_date", "expiry_date", "notes",
                ):
                    if k in data:
                        pr[k] = str(data.get(k) or "").strip()
                proxies[i] = pr
                break
        self.store.update_active(proxies=proxies)
        return {"ok": True, "proxies": proxies}

    def delete_proxy(self, proxy_id: str):
        proxies = [p for p in (self._proj().get("proxies") or []) if p.get("id") != proxy_id]
        self.store.update_active(proxies=proxies)
        return {"ok": True, "proxies": proxies}

    def save_proxy(self, data=None, **kwargs):
        if data is None:
            data = kwargs
        if not isinstance(data, dict):
            data = {}
        if data.get("host") or data.get("name") or data.get("as_list"):
            return self.add_proxy(data)
        return _orig_save_proxy(self, data)

    def get_dashboard(self):
        data = _orig_get_dashboard(self)
        try:
            p = self._proj()
            proxies = p.get("proxies") or []
            if data and "proxy_html" in data:
                extra = "<p><strong>📡 Прокси в списке:</strong> %d</p>" % len(proxies)
                if "Прокси в списке" not in data["proxy_html"]:
                    data["proxy_html"] = extra + data["proxy_html"]
        except Exception:
            pass
        return data

    try:
        from modules.stats_parser import StatsParser
        if not getattr(StatsParser, "_norm_patched", False):
            _orig_pc = StatsParser.parse_channels

            def parse_channels(self, links_file, progress_callback=None):
                results = _orig_pc(self, links_file, progress_callback)
                return _normalize_stats_results(results)

            StatsParser.parse_channels = parse_channels
            StatsParser._norm_patched = True
    except Exception as e:
        print("parse_channels patch:", e)

    WebAPI.get_config = get_config
    WebAPI.set_theme = set_theme
    WebAPI.toggle_theme = toggle_theme
    WebAPI.get_proxies = get_proxies
    WebAPI.add_proxy = add_proxy
    WebAPI.update_proxy = update_proxy
    WebAPI.delete_proxy = delete_proxy
    WebAPI.save_proxy = save_proxy
    WebAPI.get_dashboard = get_dashboard
    WebAPI.normalize_stats_results = staticmethod(_normalize_stats_results)
    WebAPI._runtime_patched = True
    return WebAPI
