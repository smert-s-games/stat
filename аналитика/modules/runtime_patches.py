"""Runtime patches: multi-proxy, themes, 404, correct channel views."""
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
        err = str(r.get("error") or "")
        name = (r.get("channel_name") or "").strip()
        name_low = name.lower()
        blob = (err + " " + str(r.get("status") or "") + " " + name_low).lower()

        if name_low in ("youtube", "www.youtube.com"):
            cleaned.append({
                "url": r.get("url", ""),
                "channel_name": name,
                "error": "Неактивный канал",
                "status": "❌",
                "email": r.get("email") or "",
                "subscribers": "—",
                "total_views": "—",
                "videos_count": "—",
                "project_name": r.get("project_name", ""),
                "project_id": r.get("project_id", ""),
            })
            continue

        if r.get("error") or ("404" in blob) or ("not found" in blob) or ("неактивн" in blob):
            if "404" in blob or "not found" in blob or "не найден" in blob:
                r["error"] = "404 Not Found"
            elif "неактивн" in blob:
                r["error"] = "Неактивный канал"
            elif not r.get("error"):
                r["error"] = err or "Ошибка"
            r["status"] = "❌"
            cleaned.append(r)
            continue

        subs = str(r.get("subscribers") or "")
        views = str(r.get("total_views") or "")
        emptyish = (
            (not name or name == "Неизвестно")
            and subs in ("", "Неизвестно", "0", "None")
            and views in ("", "0", "None", "Неизвестно")
        )
        if emptyish:
            cleaned.append({
                "url": r.get("url", ""),
                "channel_name": name or r.get("url", ""),
                "error": "404 Not Found",
                "status": "❌",
                "email": r.get("email") or "",
                "subscribers": "—",
                "total_views": "—",
                "videos_count": "—",
                "project_name": r.get("project_name", ""),
                "project_id": r.get("project_id", ""),
            })
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
    _orig_switch = getattr(WebAPI, "switch_project", None)

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
                for k in ("name", "host", "port", "type", "login", "password", "purchase_date", "expiry_date", "notes"):
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
                extra = "<p><strong>Прокси в списке:</strong> %d</p>" % len(proxies)
                if "Прокси в списке" not in data["proxy_html"]:
                    data["proxy_html"] = extra + data["proxy_html"]
        except Exception:
            pass
        return data

    def get_all_projects_stats(self):
        all_stats = []
        projects = []
        try:
            self.store._index = self.store._load_index()
            projects = list(self.store._index.get("projects") or [])
        except Exception as e:
            return {"stats": [], "count": 0, "projects_count": 0, "error": str(e)}
        for proj in projects:
            if not isinstance(proj, dict):
                continue
            name = proj.get("name") or proj.get("id") or "?"
            for r in (proj.get("last_stats") or []):
                if not isinstance(r, dict):
                    continue
                row = dict(r)
                row["project_name"] = name
                row["project_id"] = proj.get("id", "")
                all_stats.append(row)
        all_stats = _normalize_stats_results(all_stats)
        return {"stats": all_stats, "count": len(all_stats), "projects_count": len(projects)}

    def switch_project(self, pid: str):
        self.current_stats = []
        self.current_accounts = []
        try:
            self.store._index = self.store._load_index()
        except Exception:
            pass
        if _orig_switch:
            res = _orig_switch(self, pid)
        else:
            res = self.store.set_active(pid)
            if not res.get("error"):
                self._restore_session()
                res = {"ok": True, "id": pid}
        try:
            self.store._index = self.store._load_index()
            self._restore_session()
        except Exception:
            pass
        if isinstance(res, dict) and not res.get("error"):
            res["stats_count"] = len(getattr(self, "current_stats", []) or [])
            res["project_name"] = (self._proj() or {}).get("name", "")
        return res

    def get_cached_stats(self):
        try:
            self.store._index = self.store._load_index()
        except Exception:
            pass
        from modules.web_backend import sort_stats
        p = self._proj()
        results = sort_stats(list(p.get("last_stats") or []), p.get("stats_sort") or "default")
        results = _normalize_stats_results(results)
        self.current_stats = results
        return results

    try:
        from modules.stats_parser import StatsParser
        if not getattr(StatsParser, "_parse_number_fixed", False):
            import re as _re

            def parse_number(self, text):
                if not text or text in ("Неизвестно", "0", "-", "N/A", "—"):
                    return 0
                text = str(text).strip().lower().replace("\xa0", " ").replace("\u202f", " ")
                text = _re.sub(r"(подписчик|просмотр|видео|views?|subscribers?|videos?).*$", "", text, flags=_re.I)
                text = text.strip()
                multipliers = {
                    "тыс.": 1_000, "тыс": 1_000, "thousand": 1_000, "k": 1_000,
                    "млн.": 1_000_000, "млн": 1_000_000, "million": 1_000_000, "m": 1_000_000,
                    "млрд.": 1_000_000_000, "млрд": 1_000_000_000, "billion": 1_000_000_000, "b": 1_000_000_000,
                }
                mult = 1
                for key, val in sorted(multipliers.items(), key=lambda x: -len(x[0])):
                    if key in text:
                        mult = val
                        text = text.replace(key, "").strip()
                        break
                text = text.replace(" ", "")
                if not text:
                    return 0
                if _re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", text):
                    text = text.replace(",", "")
                elif _re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", text):
                    text = text.replace(".", "").replace(",", ".")
                elif "," in text and "." not in text:
                    left, right = text.split(",", 1)
                    if right.isdigit() and len(right) == 3 and left.isdigit():
                        text = left + right
                    else:
                        text = left + "." + right
                elif "." in text and "," not in text:
                    left, right = text.split(".", 1)
                    if right.isdigit() and len(right) == 3 and left.isdigit() and mult > 1:
                        text = left + right
                cleaned = _re.sub(r"[^\d.]", "", text)
                if not cleaned or cleaned == ".":
                    return 0
                try:
                    return int(float(cleaned) * mult)
                except ValueError:
                    return 0

            StatsParser.parse_number = parse_number
            StatsParser._parse_number_fixed = True
    except Exception as e:
        print("parse_number patch:", e)

    try:
        from modules.stats_parser import StatsParser
        if not getattr(StatsParser, "_views_patched_v3", False):
            import re as _re

            _orig_pcd = StatsParser.parse_channel_data

            def _views_from_about_only(src: str, parse_number):
                """Только about-блоки канала — НЕ карточки видео."""
                cands = []
                if not src:
                    return 0
                for pat in (
                    r'"aboutChannelViewModel"\s*:\s*\{',
                    r'"channelAboutFullMetadataRenderer"\s*:\s*\{',
                ):
                    for m in _re.finditer(pat, src):
                        chunk = src[m.start() : m.start() + 8000]
                        for vm in _re.finditer(
                            r'"viewCountText"\s*:\s*(?:\{[^}]*?"simpleText"\s*:\s*"([^"]+)"|"([^"]+)")',
                            chunk,
                        ):
                            n = parse_number(vm.group(1) or vm.group(2) or "")
                            if n > 0:
                                cands.append(n)
                        # иногда число без Text
                        for vm in _re.finditer(r'"viewCount"\s*:\s*"?(\d+)"?', chunk):
                            n = int(vm.group(1))
                            if n > 0:
                                cands.append(n)
                return max(cands) if cands else 0

            def parse_channel_data(self, url):
                data = _orig_pcd(self, url)
                if not isinstance(data, dict) or data.get("error"):
                    return data
                name = (data.get("channel_name") or "").strip()
                if name.lower() in ("youtube", "www.youtube.com"):
                    data["error"] = "Неактивный канал"
                    data["status"] = "❌"
                    return data

                try:
                    src = self.driver.page_source if self.driver else ""
                except Exception:
                    src = ""

                about_n = _views_from_about_only(src, self.parse_number)
                if about_n > 0:
                    data["total_views_num"] = about_n
                    data["total_views"] = self.format_large_number(about_n)
                else:
                    # не оставляем мусор с карточек: если число крошечное/сомнительное — 0
                    n = int(data.get("total_views_num") or 0) or self.parse_number(
                        str(data.get("total_views") or "0")
                    )
                    # если на about не нашли — лучше показать 0, чем чужие 48 с видео
                    if n > 0 and n < 20:
                        data["total_views"] = "0"
                        data["total_views_num"] = 0
                    elif n > 0:
                        data["total_views_num"] = n
                        data["total_views"] = self.format_large_number(n)
                return data

            StatsParser.parse_channel_data = parse_channel_data
            StatsParser._views_patched_v3 = True
            StatsParser._views_patched = True
            StatsParser._views_patched_v2 = True
    except Exception as e:
        print("views patch:", e)

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

    WebAPI.switch_project = switch_project
    WebAPI.get_cached_stats = get_cached_stats
    WebAPI.get_all_projects_stats = get_all_projects_stats
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
