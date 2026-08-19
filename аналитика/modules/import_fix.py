"""Hotfix: import_channels always splits url:email."""
def apply_import_fix(WebAPI):
    import uuid
    import re as _re

    def import_channels(self, text: str, fmt: str = "url"):
        text = text or ""
        existing = []
        try:
            existing = self._channels_list()
        except Exception:
            existing = list((self._proj() or {}).get("channels") or [])
        by_url = {(c.get("url") or "").rstrip("/").lower(): c for c in existing}
        added = 0
        updated = 0

        def split_line(line):
            line = (line or "").strip()
            if not line or line.startswith("#"):
                return "", ""
            if line.startswith("."):
                line = line[1:]
            m = _re.match(
                r"^(https?://.+?):([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})$",
                line,
            )
            if m:
                return m.group(1).rstrip("/"), m.group(2).strip()
            parts = line.split()
            if len(parts) >= 2 and "@" in parts[-1] and "." in parts[-1]:
                return parts[0].rstrip("/"), parts[-1].strip()
            if "://" not in line and ":" in line:
                a, b = line.split(":", 1)
                if "@" in b and "." in b:
                    return a.strip().rstrip("/"), b.strip()
            return line.rstrip("/"), ""

        for line in text.splitlines():
            url, email = split_line(line)
            if not url:
                continue
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
            print("import save:", e)
        try:
            if hasattr(self, "_sync_links_file"):
                self._sync_links_file(existing)
        except Exception:
            pass

        try:
            stats = list((self._proj() or {}).get("last_stats") or [])
            email_map = {(c.get("url") or "").rstrip("/").lower(): c.get("email") or "" for c in existing}
            changed = False
            for r in stats:
                if not isinstance(r, dict):
                    continue
                u = (r.get("url") or "").rstrip("/").lower()
                if u in email_map and email_map[u] and not r.get("email"):
                    r["email"] = email_map[u]
                    changed = True
                u0, e0 = split_line(r.get("url") or "")
                if u0 and u0 != (r.get("url") or "").rstrip("/"):
                    r["url"] = u0
                    if e0 and not r.get("email"):
                        r["email"] = e0
                    changed = True
            if changed:
                self.store.update_active(last_stats=stats)
                self.current_stats = stats
        except Exception as e:
            print("import merge:", e)

        return {"ok": True, "added": added, "updated": updated, "total": len(existing), "channels": existing}

    WebAPI.import_channels = import_channels
    print("import_fix applied")
    return WebAPI
