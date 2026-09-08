"""Improve channel name, subscribers, videos_count, email extraction."""
from __future__ import annotations
import re


BAD_NAMES = {
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
    if not n or n in BAD_NAMES or len(n) <= 2:
        return True
    if "подпис" in n and len(n) < 20:
        return True
    return False


def apply_parser_fix(StatsParser):
    _orig = getattr(StatsParser, "_parser_fix_orig", None) or StatsParser.parse_channel_data
    if not getattr(StatsParser, "_parser_fix_orig", None):
        StatsParser._parser_fix_orig = StatsParser.parse_channel_data
        _orig = StatsParser.parse_channel_data

    def parse_channel_data(self, url):
        data = _orig(self, url)
        if not isinstance(data, dict) or data.get("error"):
            return data
        try:
            src = self.driver.page_source if self.driver else ""
        except Exception:
            src = ""

        name = (data.get("channel_name") or "").strip()

        if src:
            for pat in (
                r'property="og:title"\s+content="([^"]+)"',
                r'content="([^"]+)"\s+property="og:title"',
                r'"microformatDataRenderer"\s*:\s*\{[^}]*?"title"\s*:\s*"([^"]+)"',
                r'"channelMetadataRenderer"\s*:\s*\{[^}]*?"title"\s*:\s*"([^"]+)"',
                r'"alternateName"\s*:\s*"(@[^"]+)"',
                r'twitter:title[^>]+content="([^"]+)"',
            ):
                m = re.search(pat, src, re.I)
                if not m:
                    continue
                cand = m.group(1).replace(" - YouTube", "").strip()
                if cand and not _bad(cand):
                    name = cand
                    break

        if _bad(name):
            um = re.search(r"youtube\.com/@([^/?&#]+)", url or "", re.I)
            if um:
                name = "@" + um.group(1)
        data["channel_name"] = name

        if self.parse_number(str(data.get("videos_count") or "0")) <= 0 and src:
            for pat in (
                r'"content"\s*:\s*"([\d\s.,]+)\s*видео"',
                r'"videosCountText"\s*:\s*\{[^\]]*?\[\s*\{\s*"text"\s*:\s*"([^"]+)"',
                r'"videoCountText"\s*:\s*\{[^}]*?"simpleText"\s*:\s*"([^"]+)"',
                r'([\d\s.,]+)\s*(тыс\.?|млн\.?|K|M)?\s*видео',
                r'([\d\s.,]+)\s*(K|M)?\s*videos?',
            ):
                m = re.search(pat, src, re.I)
                if not m:
                    continue
                n = self.parse_number(m.group(1))
                if n > 0:
                    data["videos_count_num"] = n
                    data["videos_count"] = self.format_large_number(n)
                    break

        if self.parse_number(str(data.get("subscribers") or "0")) <= 0 and src:
            for pat in (
                r'"subscriberCountText"\s*:\s*\{[^}]*?"simpleText"\s*:\s*"([^"]+)"',
                r'"content"\s*:\s*"([\d\s.,]+\s*(?:тыс\.?|млн\.?|K|M)?\s*подписчик[^"]*)"',
                r'([\d\s.,]+)\s*(тыс\.?|млн\.?|K|M)?\s*подписчик',
                r'([\d\s.,]+)\s*(K|M)?\s*subscribers?',
            ):
                m = re.search(pat, src, re.I)
                if not m:
                    continue
                raw = m.group(1)
                if m.lastindex and m.lastindex >= 2 and m.group(2):
                    raw = (m.group(1) + " " + m.group(2)).strip()
                n = self.parse_number(raw)
                if n > 0:
                    data["subscribers_num"] = n
                    data["subscribers"] = self.format_large_number(n)
                    break

        if not (data.get("email") or "").strip() and src:
            em = re.search(
                r"mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
                src,
            )
            if em:
                data["email"] = em.group(1)

        return data

    StatsParser.parse_channel_data = parse_channel_data
    StatsParser._parser_fix_v1 = True
    StatsParser._parser_fix_v3 = True
    return StatsParser
