"""Emails from links file + show manually added channels in stats table."""
from __future__ import annotations
import os
import re
import uuid


def _split_line(line: str):
    line = (line or "").strip()
    if not line or line.startswith("#"):
        return "", ""
    m = re.match(r"^(https?://\S+?):([^\s]+@[^\s]+)$", line)
    if m:
        return m.group(1).rstrip("/"), m.group(2).strip()
    m2 = re.match(r"^(https?://\S+)[\s;|]+([^\s]+@[^\s]+)$", line)
    if m2:
        return m2.group(1).rstrip("/"), m2.group(2).strip()
    if line.startswith("http"):
        return line.split()[0].rstrip("/"), ""
    return line, ""


def _email_map_from_file(path: str) -> dict:
    out = {}
    if not path or not os.path.exists(path):
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                u, e = _split_line(line)
                if u and e:
                    out[u.rstrip("/").lower()] = e
    except Exception as ex:
        print("email map file:", ex)
    return out


def _email_map_from_channels(channels) -> dict:
    out = {}
    for c in channels or []:
        if not isinstance(c, dict):
            continue
        u = (c.get("url") or "").rstrip("/").lower()
        e = (c.get("email") or "").strip()
        if u and e:
            out[u] = e
    return out


def _apply_emails(stats, email_map: dict):
    if not email_map:
        return stats, False
    changed = False
    fixed = []
    for r in stats or []:
        if not isinstance(r, dict):
            fixed.append(r)
            continue
        r = dict(r)
        u = (r.get("url") or "").rstrip("/").lower()
        u0, e0 = _split_line(r.get("url") or "")
        if u0:
            u = u0.rstrip("/").lower()
            r["url"] = u0
            if e0 and not (r.get("email") or "").strip():
                r["email"] = e0
                changed = True
        if u in email_map:
            if (r.get("email") or "").strip() != email_map[u]:
                r["email"] = email_map[u]
                changed = True
        fixed.append(r)
    return fixed, changed


def _placeholder_row(c: dict) -> dict:
    url = (c.get("url") or "").strip()
    name = (c.get("name") or "").strip()
    if not name:
        m = re.search(r"youtube\.com/@([^/?&#]+)", url)
        name = ("@" + m.group(1)) if m else url
    return {
        "url": url,
        "channel_name": name,
        "email": (c.get("email") or "").strip(),
        "subscribers": "—",
        "total_views": "—",
        "videos_count": "—",
        "status": "⏳",
        "error": "",
        "pending": True,
    }


def apply_email_stats_fix(WebAPI):
    if getattr(WebAPI, "_email_stats_fix", False):
        return WebAPI

    def _links_path(self):
        p = self._proj() or {}
        path = p.get("links_file") or "links.txt"
        if not os.path.isabs(path):
            from modules.web_backend import BASE
            path = str(BASE / path)
        return path

    def _build_email_map(self):
        p = self._proj() or {}
        m = {}
        m.update(_email_map_from_channels(p.get("channels") or []))
        m.update(_email_map_from_file(self._links_path()))
        return m

    def _sync_links_file(self, channels):
        path = self._links_path()
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                for c in channels or []:
                    if not isinstance(c, dict):
                        continue
                    u = (c.get("url") or "").strip()
                    if not u:
                        continue
                    e = (c.get("email") or "").strip()
                    if e:
                        f.write(f"{u}:{e}\n")
                    else:
                        f.write(u + "\n")
        except Exception as e:
            print("sync links:", e)

    def import_channels(self, text: str, fmt: str = "url"):
        text = text or ""
        fmt = (fmt or "url").strip().lower()
        try:
            existing = self._channels_list()
        except Exception:
            existing = list((self._proj() or {}).get("channels") or [])
        by_url = {(c.get("url") or "").rstrip("/").lower(): c for c in existing if isinstance(c, dict)}
        added = 0
        updated = 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            url, email = line, ""
            u0, e0 = _split_line(line)
            if u0:
                url, email = u0, e0
            elif fmt in ("url_email", "channel:email", "url:email"):
                parts = re.split(r"[\s;|]+", line)
                if len(parts) >= 2 and "@" in parts[-1]:
                    url, email = parts[0], parts[-1]
            url = (url or "").strip().rstrip("/")
            if not url:
                continue
            if not url.startswith("http"):
                if url.startswith("@"):
                    url = "https://www.youtube.com/" + url
                else:
                    url = "https://www.youtube.com/@" + url.lstrip("@")
            key = url.lower()
            if key in by_url:
                if email and by_url[key].get("email") != email:
                    by_url[key]["email"] = email
                    updated += 1
                continue
            item = {"id": str(uuid.uuid4())[:8], "url": url, "email": email, "name": ""}
            existing.append(item)
            by_url[key] = item
            added += 1

        try:
            self.store.update_active(channels=existing)
        except Exception as e:
            print("import channels store:", e)
        try:
            self._sync_links_file(existing)
        except Exception as e:
            print("import sync:", e)

        stats = list((self._proj() or {}).get("last_stats") or [])
        by_stats = {}
        for r in stats:
            if isinstance(r, dict) and r.get("url"):
                by_stats[(r.get("url") or "").rstrip("/").lower()] = r

        email_map = self._build_email_map()
        for item in existing:
            key = (item.get("url") or "").rstrip("/").lower()
            if not key:
                continue
            if key not in by_stats:
                row = _placeholder_row(item)
                if key in email_map:
                    row["email"] = email_map[key]
                stats.append(row)
                by_stats[key] = row
            else:
                row = by_stats[key]
                if email_map.get(key):
                    row["email"] = email_map[key]
                elif item.get("email") and not row.get("email"):
                    row["email"] = item["email"]

        stats, _ = _apply_emails(stats, email_map)
        try:
            self.store.update_active(last_stats=stats)
        except Exception as e:
            print("import stats:", e)
        self.current_stats = stats
        return {
            "ok": True,
            "added": added,
            "updated": updated,
            "total": len(existing),
            "channels": existing,
            "stats": stats,
        }

    def get_cached_stats(self):
        try:
            self.store._index = self.store._load_index()
        except Exception:
            pass
        from modules.web_backend import sort_stats
        p = self._proj() or {}
        results = list(p.get("last_stats") or [])
        email_map = self._build_email_map()
        results, changed = _apply_emails(results, email_map)
        by_url = {(r.get("url") or "").rstrip("/").lower(): r for r in results if isinstance(r, dict)}
        for c in p.get("channels") or []:
            if not isinstance(c, dict):
                continue
            key = (c.get("url") or "").rstrip("/").lower()
            if not key:
                continue
            if key not in by_url:
                results.append(_placeholder_row(c))
                changed = True
            elif email_map.get(key) and not (by_url[key].get("email") or "").strip():
                by_url[key]["email"] = email_map[key]
                changed = True
        mode = p.get("stats_sort") or "default"
        try:
            results = sort_stats(results, mode)
        except Exception:
            pass
        if changed:
            try:
                self.store.update_active(last_stats=results)
            except Exception:
                pass
        self.current_stats = results
        return results

    def start_parse(self):
        import threading
        import json
        import os
        from modules.web_backend import BASE, sort_stats

        try:
            ch = self._channels_list() if hasattr(self, "_channels_list") else (self._proj() or {}).get("channels")
            if ch:
                self._sync_links_file(ch)
        except Exception as e:
            print("pre-parse sync:", e)

        if getattr(self, "_stats_running", False):
            return {"error": "Парсинг уже выполняется"}
        p = self._proj() or {}
        links = p.get("links_file") or "links.txt"
        if not os.path.isabs(links):
            links = str(BASE / links)
        if not os.path.exists(links):
            return {"error": f"Файл не найден: {links}"}

        self._stats_running = True
        email_map = self._build_email_map()

        def worker():
            try:
                def progress(current, total, link):
                    try:
                        self._js(
                            "App.onParseProgress("
                            + self._js_str(f"[{current}/{total}] {link}\n")
                            + ")"
                        )
                    except Exception:
                        pass
                results = self.stats_parser.parse_channels(links, progress_callback=progress)
                cleaned = []
                for r in results or []:
                    if not isinstance(r, dict):
                        continue
                    r = dict(r)
                    u = (r.get("url") or "").rstrip("/").lower()
                    if u in email_map:
                        r["email"] = email_map[u]
                    r.setdefault("email", "")
                    if r.get("error"):
                        err = str(r["error"])
                        if "404" in err or "not found" in err.lower():
                            r["error"] = "404 Not Found"
                        cleaned.append(r)
                        continue
                    cleaned.append(r)
                cleaned, _ = _apply_emails(cleaned, email_map)
                mode = (self._proj() or {}).get("stats_sort") or "default"
                cleaned = sort_stats(cleaned, mode)
                self.current_stats = cleaned
                try:
                    self.store.update_active(last_stats=cleaned)
                except Exception as e:
                    print("session save error:", e)
                try:
                    self._js("App.onParseDone(" + json.dumps(cleaned, ensure_ascii=False) + ")")
                except Exception as e:
                    print("onParseDone:", e)
            except Exception as e:
                try:
                    self._js("App.onParseProgress(" + self._js_str("\n❌ " + str(e) + "\n") + ")")
                    self._js("App.onParseDone([])")
                except Exception:
                    pass
            finally:
                self._stats_running = False

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    WebAPI._sync_links_file = _sync_links_file
    WebAPI._build_email_map = _build_email_map
    WebAPI._links_path = _links_path
    WebAPI.import_channels = import_channels
    WebAPI.get_cached_stats = get_cached_stats
    WebAPI.start_parse = start_parse
    WebAPI._email_stats_fix = True
    print("email_stats_fix applied")
    return WebAPI
