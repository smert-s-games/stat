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
    "unsubscribe", "отписаться",
}


def _bad(name: str) -> bool:
    n = (name or "").strip().lower().replace("\u00a0", " ")
    if not n or n in BAD or len(n) <= 2:
        return True
    if "подпис" in n and len(n) < 20:
        return True
    return False


def _name_from_url(url: str) -> str:
    url = (url or "").strip()
    m = re.search(r"youtube\.com/@([^/?&#]+)", url, re.I)
    if m:
        return "@" + m.group(1)
    m2 = re.search(r"youtube\.com/(?:channel/|c/|user/)([^/?&#]+)", url, re.I)
    if m2:
        return m2.group(1)
    return ""


def _fix_name(r: dict) -> dict:
    if not isinstance(r, dict):
        return r
    r = dict(r)
    name = (r.get("channel_name") or "").strip()
    url = (r.get("url") or "").strip()
    if _bad(name):
        alt = _name_from_url(url)
        if alt:
            r["channel_name"] = alt
    return r


def apply_display_fix(WebAPI):
    _orig = WebAPI.get_cached_stats

    def get_cached_stats(self):
        results = _orig(self)
        if not isinstance(results, list):
            return results
        fixed = [_fix_name(r) for r in results]
        try:
            self.store.update_active(last_stats=fixed)
            self.current_stats = fixed
        except Exception:
            pass
        return fixed

    WebAPI.get_cached_stats = get_cached_stats
    WebAPI._display_fix = True
    WebAPI._display_fix_v3 = True
    print("display_fix v3 applied")
    return WebAPI
