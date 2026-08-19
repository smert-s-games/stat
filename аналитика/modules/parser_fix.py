"""Improve subscribers / videos_count extraction after main parser."""
from __future__ import annotations
import re


def apply_parser_fix(StatsParser):
    if getattr(StatsParser, "_parser_fix_v1", False):
        return StatsParser

    _orig = StatsParser.parse_channel_data

    def parse_channel_data(self, url):
        data = _orig(self, url)
        if not isinstance(data, dict) or data.get("error"):
            return data
        try:
            src = self.driver.page_source if self.driver else ""
        except Exception:
            src = ""
        if not src:
            return data

        def need(key):
            return self.parse_number(str(data.get(key) or "0")) <= 0

        if need("subscribers"):
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

        if need("videos_count"):
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

        return data

    StatsParser.parse_channel_data = parse_channel_data
    StatsParser._parser_fix_v1 = True
    return StatsParser
