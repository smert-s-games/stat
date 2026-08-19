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
}


def _bad(name: str) -> bool:
    n = (name or "").strip().lower()
    if not n or n in BAD_NAMES or len(n) <= 2:
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
        if _bad(name) and src:
            m = re.search(
                r'"channelMetadataRenderer"\s*:\s*\{[^}]*?"title"\s*:\s*"([^"]+)"',
                src,
            )
            if m and not _bad(m.group(1)):
                name = m.group(1).strip()
            if _bad(name):
                m = re.search(r'property="og:title"\s+content="([^"]+)"', src)
                if not m:
                    m = re.search(r'content="([^"]+)"\s+property="og:title"', src)
                if m:
                    cand = m.group(1).replace(" - YouTube", "").strip()
                    if not _bad(cand):
                        name = cand
            if _bad(name):
                m = re.search(r'"ownerChannelName"\s*:\s*"([^"]+)"', src)
                if m and not _bad(m.group(1)):
                    name = m.group(1).strip()
        if _bad(name):
            um = re.search(r"youtube\.com/@([^/?&#]+)", url or "")
            if um:
                name = "@" + um.group(1)
        data["channel_name"] = name

        if self.parse_number(str(data.get("videos_count") or "0")) <= 0 and src:
            for pat in (
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
                r'"subscriberCountText"\s*:\s*\{[^\]]*?\[\s*\{\s*"text"\s*:\s*"([^"]+)"',
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
            else:
                em2 = re.search(
                    r"(?:businessEmail|email)[\"']?\s*[:=]\s*[\"']([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
                    src,
                    re.I,
                )
                if em2:
                    data["email"] = em2.group(1)
                else:
                    for em3 in re.finditer(
                        r"\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b",
                        src,
                    ):
                        addr = em3.group(1).lower()
                        if "youtube" in addr or "google" in addr or "example.com" in addr:
                            continue
                        data["email"] = em3.group(1)
                        break

        return data

    StatsParser.parse_channel_data = parse_channel_data
    StatsParser._parser_fix_v1 = True
    StatsParser._parser_fix_v2 = True
    return StatsParser
