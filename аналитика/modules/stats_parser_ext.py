"""
Расширение StatsParser: email + links из about / ytInitialData / page source.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse, unquote


_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9][a-zA-Z0-9._%+\-]{0,63}@[a-zA-Z0-9][a-zA-Z0-9.\-]{0,253}\.[a-zA-Z]{2,24}"
)

_SKIP_EMAIL = (
    "youtube.",
    "google.",
    "example.com",
    "sentry.io",
    "schema.org",
    "w3.org",
    "noreply",
    "no-reply",
    "donotreply",
)


def _clean_email(email: str) -> str:
    email = (email or "").strip().rstrip(".,;:)\\]>\"'")
    email = unquote(email)
    if email.lower().startswith("mailto:"):
        email = email[7:]
    if "?" in email:
        email = email.split("?", 1)[0]
    return email.strip()


def is_valid_public_email(email: str) -> bool:
    email = _clean_email(email)
    if not email or "@" not in email:
        return False
    low = email.lower()
    if any(x in low for x in _SKIP_EMAIL):
        return False
    if low.count("@") != 1:
        return False
    return True


def extract_email(*texts) -> str:
    for text in texts:
        if not text:
            continue
        if isinstance(text, (list, tuple)):
            for item in text:
                found = extract_email(item)
                if found:
                    return found
            continue
        if isinstance(text, dict):
            found = extract_email_from_obj(text)
            if found:
                return found
            continue
        for m in _EMAIL_RE.finditer(str(text)):
            email = _clean_email(m.group(0))
            if is_valid_public_email(email):
                return email
    return ""


def extract_email_from_obj(obj) -> str:
    found: list[str] = []

    def walk(node, depth=0):
        if depth > 25 or len(found) > 5:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                kl = str(k).lower()
                if kl in ("businessemail", "email", "emailaddress", "business_email", "mail"):
                    if isinstance(v, str) and is_valid_public_email(v):
                        found.append(_clean_email(v))
                    elif isinstance(v, dict):
                        st = v.get("simpleText") or v.get("content") or ""
                        if isinstance(st, str) and is_valid_public_email(st):
                            found.append(_clean_email(st))
                walk(v, depth + 1)
        elif isinstance(node, list):
            for item in node[:200]:
                walk(item, depth + 1)
        elif isinstance(node, str):
            if "@" in node and len(node) < 300:
                for m in _EMAIL_RE.finditer(node):
                    email = _clean_email(m.group(0))
                    if is_valid_public_email(email):
                        found.append(email)
                        return

    walk(obj)
    return found[0] if found else ""


def extract_mailto_from_html(html: str) -> str:
    if not html:
        return ""
    for m in re.finditer(r"mailto:([^\"'\s?>]+)", html, re.I):
        email = _clean_email(m.group(1))
        if is_valid_public_email(email):
            return email
    return extract_email(html)


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


def _find_about_metadata(data):
    metadata = None
    try:
        tabs = (
            (data or {})
            .get("contents", {})
            .get("twoColumnBrowseResultsRenderer", {})
            .get("tabs", [])
        )
        for tab in tabs:
            tr = tab.get("tabRenderer", {})
            title = (tr.get("title") or "").lower()
            if title in ("о канале", "about", "info", "channel"):
                contents = ((tr.get("content", {}) or {}).get("sectionListRenderer", {}) or {}).get("contents", []) or []
                for s in contents:
                    for i in (s.get("itemSectionRenderer", {}) or {}).get("contents", []) or []:
                        if "channelAboutFullMetadataRenderer" in i:
                            return i["channelAboutFullMetadataRenderer"]
    except Exception:
        pass
    try:
        def walk(node, depth=0):
            nonlocal metadata
            if metadata or depth > 20:
                return
            if isinstance(node, dict):
                if "channelAboutFullMetadataRenderer" in node:
                    metadata = node["channelAboutFullMetadataRenderer"]
                    return
                for v in node.values():
                    walk(v, depth + 1)
            elif isinstance(node, list):
                for item in node[:100]:
                    walk(item, depth + 1)
        walk(data)
    except Exception:
        pass
    return metadata


def _enrich(data, page_text="", yt_data=None, page_html=""):
    if not data:
        return data
    if data.get("error"):
        return data
    data.setdefault("email", "")
    data.setdefault("links", [])

    if not data.get("email"):
        candidates = []
        if yt_data:
            candidates.append(extract_email_from_obj(yt_data))
        candidates.append(extract_mailto_from_html(page_html))
        link_texts = []
        for L in data.get("links") or []:
            if isinstance(L, dict):
                link_texts.append(L.get("title") or "")
                link_texts.append(L.get("url") or "")
            else:
                link_texts.append(str(L))
        candidates.append(extract_email(data.get("description", ""), page_text, *link_texts))
        for c in candidates:
            if c:
                data["email"] = c
                break
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
            metadata = _find_about_metadata(data)
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
            email = extract_email_from_obj(data)
            if email:
                channel_data["email"] = email
        except Exception:
            pass
        return _enrich(channel_data, yt_data=data)

    def _parse_from_dom(self, url):
        channel_data = orig_dom(self, url)
        page_text = ""
        page_html = ""
        try:
            from selenium.webdriver.common.by import By
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            page_html = self.driver.page_source or ""
        except Exception:
            pass
        return _enrich(channel_data, page_text=page_text, page_html=page_html)

    def parse_channel_data(self, url):
        data = orig_parse(self, url)
        if not data:
            return {"url": url, "error": "404 Not Found", "email": ""}
        if not data.get("error") and not data.get("email"):
            try:
                page_html = ""
                page_text = ""
                if getattr(self, "driver", None):
                    page_html = self.driver.page_source or ""
                    page_text = self.driver.find_element("tag name", "body").text
                data = _enrich(data, page_text=page_text, page_html=page_html)
            except Exception:
                pass
        return data

    parser_cls._parse_from_yt_data = _parse_from_yt_data
    parser_cls._parse_from_dom = _parse_from_dom
    parser_cls.parse_channel_data = parse_channel_data
    parser_cls.extract_email = staticmethod(extract_email)
    return parser_cls
