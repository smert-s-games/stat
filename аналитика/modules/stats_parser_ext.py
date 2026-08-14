"""
Расширение StatsParser: email + links из about / description.
Вызывается из patches после загрузки приложения.
"""
import re
from urllib.parse import parse_qs, urlparse


_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9][a-zA-Z0-9._%+\-]{0,63}@[a-zA-Z0-9][a-zA-Z0-9.\-]{0,253}\.[a-zA-Z]{2,}"
)


def extract_email(*texts):
    for text in texts:
        if not text:
            continue
        if isinstance(text, (list, tuple)):
            for item in text:
                found = extract_email(item)
                if found:
                    return found
            continue
        for m in _EMAIL_RE.finditer(str(text)):
            email = m.group(0).rstrip(".,;)")
            low = email.lower()
            if any(x in low for x in ("youtube.", "google.", "example.com", "sentry.io")):
                continue
            return email
    return ""


def _extract_primary_links(metadata):
    links = []
    if not metadata:
        return links
    for link in metadata.get("primaryLinks", []) or []:
        title_node = link.get("title") or {}
        title = title_node.get("simpleText") if isinstance(title_node, dict) else (title_node or "")
        nav = link.get("navigationEndpoint") or {}
        url = (
            (nav.get("urlEndpoint") or {}).get("url")
            or ((nav.get("commandMetadata") or {}).get("webCommandMetadata") or {}).get("url")
            or ""
        )
        if "youtube.com/redirect" in url and "q=" in url:
            try:
                q = parse_qs(urlparse(url).query).get("q", [""])[0]
                if q:
                    url = q
            except Exception:
                pass
        if url or title:
            links.append({"title": title, "url": url})
    return links


def _enrich(data, page_text=""):
    if not data or "error" in data:
        return data
    if "email" not in data:
        data["email"] = ""
    if "links" not in data:
        data["links"] = []
    if not data.get("email"):
        link_texts = []
        for L in data.get("links") or []:
            if isinstance(L, dict):
                link_texts.append(L.get("title") or "")
                link_texts.append(L.get("url") or "")
            else:
                link_texts.append(str(L))
        data["email"] = extract_email(
            data.get("description", ""), page_text, *link_texts
        )
    return data


def install_stats_parser_ext(parser_cls):
    orig_yt = parser_cls._parse_from_yt_data
    orig_dom = parser_cls._parse_from_dom
    orig_parse = parser_cls.parse_channel_data

    def _parse_from_yt_data(self, data, url):
        channel_data = orig_yt(self, data, url)
        if not channel_data:
            return channel_data
        try:
            metadata = None
            tabs = (
                (data or {}).get("contents", {})
                .get("twoColumnBrowseResultsRenderer", {})
                .get("tabs", [])
            )
            for tab in tabs:
                tr = tab.get("tabRenderer", {})
                if tr.get("title") in ("О канале", "About", "Info"):
                    for s in (tr.get("content", {}).get("sectionListRenderer", {}) or {}).get("contents", []) or []:
                        for i in (s.get("itemSectionRenderer", {}) or {}).get("contents", []) or []:
                            if "channelAboutFullMetadataRenderer" in i:
                                metadata = i["channelAboutFullMetadataRenderer"]
                                break
                        if metadata:
                            break
                if metadata:
                    break
            if metadata:
                links = _extract_primary_links(metadata)
                if links:
                    channel_data["links"] = links
                if not channel_data.get("description"):
                    desc = metadata.get("description", {})
                    if isinstance(desc, dict):
                        channel_data["description"] = desc.get("simpleText") or ""
                        if not channel_data["description"] and desc.get("runs"):
                            channel_data["description"] = "".join(
                                r.get("text", "") for r in desc["runs"]
                            )
        except Exception:
            pass
        return _enrich(channel_data)

    def _parse_from_dom(self, url):
        channel_data = orig_dom(self, url)
        page_text = ""
        try:
            from selenium.webdriver.common.by import By
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            page_text = ""
        return _enrich(channel_data, page_text)

    def parse_channel_data(self, url):
        data = orig_parse(self, url)
        return _enrich(data or {})

    parser_cls._parse_from_yt_data = _parse_from_yt_data
    parser_cls._parse_from_dom = _parse_from_dom
    parser_cls.parse_channel_data = parse_channel_data
    parser_cls.extract_email = staticmethod(extract_email)
    return parser_cls
