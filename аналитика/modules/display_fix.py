"""Normalize display of channel names (Поиск/Подписаться -> @handle) in cached stats."""
from __future__ import annotations
import re

BAD = {
    "shorts", "videos", "home", "about", "community", "playlists",
    "channels", "live", "posts", "store", "search", "youtube",
    "subscriptions", "library", "history", "trending",
    "поиск", "главная", "видео", "шортс", "сообщество", "трансляции",
    "плейлисты", "каналы", "о канале", "подписки", "библиотека",
    "история", "в тренде", "магазин", "неизвестно", "www.youtube.com",
    "подписаться", "subscribe", "subscribed", "join", "присоединиться",
    "sign in", "войти", "share", "поделиться", "more", "ещё", "еще",
}


def _bad(name: str) -> bool:
    n = (name or "").strip().lower()
    return (not n) or n in BAD or len(n) <= 2


def _fix_name(r: dict) -> dict:
    if not isinstance(r, dict):
        return r
    r = dict(r)
    name = (r.get("channel_name") or "").strip()
    url = (r.get("url") or "").strip()
    if _bad(name):
        m = re.search(r"youtube\.com/@([^/?&#]+)", url)
        if m:
            r["channel_name"] = "@" + m.group(1)
        elif url:
            m2 = re.search(r"youtube\.com/(?:channel/|c/|user/)?([^/?&#]+)", url)
            if m2 and m2.group(1).lower() not in ("channel", "c", "user", "www"):
                r["channel_name"] = m2.group(1)
    return r


def apply_display_fix(WebAPI):
    # Always re-wrap so latest BAD list applies
    _orig = WebAPI.get_cached_stats

    def get_cached_stats(self):
        results = _orig(self)
        if not isinstance(results, list):
            return results
        fixed = [_fix_name(r) for r in results]
        changed = False
        for a, b in zip(results, fixed):
            if isinstance(a, dict) and isinstance(b, dict):
                if (a.get("channel_name") or "") != (b.get("channel_name") or ""):
                    changed = True
                    break
        if changed:
            try:
                self.store.update_active(last_stats=fixed)
                self.current_stats = fixed
            except Exception:
                pass
        return fixed

    WebAPI.get_cached_stats = get_cached_stats
    WebAPI._display_fix = True
    WebAPI._display_fix_v2 = True
    return WebAPI
