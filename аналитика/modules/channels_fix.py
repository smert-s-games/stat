"""Ensure WebAPI has channel list helpers and robust delete_channels."""
from __future__ import annotations
import uuid


def apply_channels_fix(WebAPI):
    if getattr(WebAPI, "_channels_fix_applied", False):
        return WebAPI

    def _channels_list(self):
        p = self._proj() or {}
        ch = list(p.get("channels") or [])
        if not ch:
            for r in p.get("last_stats") or []:
                if not isinstance(r, dict):
                    continue
                url = (r.get("url") or "").strip()
                if not url:
                    continue
                ch.append({
                    "id": str(uuid.uuid4())[:8],
                    "url": url,
                    "email": (r.get("email") or "").strip(),
                    "name": (r.get("channel_name") or "").strip(),
                })
            if ch:
                try:
                    self.store.update_active(channels=ch)
                except Exception:
                    pass
        return ch

    def _sync_links_file(self, channels):
        import os
        from modules.web_backend import BASE
        p = self._proj() or {}
        path = p.get("links_file") or "links.txt"
        if not os.path.isabs(path):
            path = str(BASE / path)
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                for c in channels or []:
                    u = (c.get("url") or "").strip()
                    if u:
                        f.write(u + "\n")
        except Exception as e:
            print("sync links:", e)

    def delete_channels(self, ids=None, urls=None):
        ids = set(ids or [])
        urls = set((u or "").rstrip("/").lower() for u in (urls or []) if u)
        try:
            existing = self._channels_list()
        except Exception:
            existing = list((self._proj() or {}).get("channels") or [])
        kept = []
        removed_urls = set(urls)
        for c in existing:
            if not isinstance(c, dict):
                continue
            cid = c.get("id")
            u = (c.get("url") or "").rstrip("/").lower()
            if cid in ids or u in removed_urls:
                removed_urls.add(u)
                continue
            kept.append(c)
        try:
            self.store.update_active(channels=kept)
        except Exception as e:
            print("delete channels store:", e)
        try:
            self._sync_links_file(kept)
        except Exception as e:
            print("sync links:", e)
        stats = list((self._proj() or {}).get("last_stats") or [])
        stats2 = [
            r for r in stats
            if isinstance(r, dict)
            and (r.get("url") or "").rstrip("/").lower() not in removed_urls
        ]
        try:
            self.store.update_active(last_stats=stats2)
        except Exception as e:
            print("delete stats:", e)
        self.current_stats = stats2
        return {
            "ok": True,
            "removed": max(0, len(existing) - len(kept)),
            "channels": kept,
            "stats": stats2,
        }

    WebAPI._channels_list = _channels_list
    WebAPI._sync_links_file = _sync_links_file
    WebAPI.delete_channels = delete_channels
    WebAPI._channels_fix_applied = True
    return WebAPI
