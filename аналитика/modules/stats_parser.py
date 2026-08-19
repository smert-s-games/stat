"""
Модуль для парсинга статистики YouTube каналов
Оптимизирован: быстрее загрузка, надёжный разбор чисел и данных, ytInitialData
"""
import re
import time
import json
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    HAS_WDM = True
except ImportError:
    HAS_WDM = False


class StatsParser:
    BAD_CHANNEL_NAMES = {
        "shorts", "videos", "home", "about", "community", "playlists",
        "channels", "live", "posts", "store", "search", "youtube",
        "subscriptions", "library", "history", "trending",
    }

    def __init__(self):
        self.driver = None

    def _is_bad_channel_name(self, name):
        n = (name or "").strip().lower()
        if not n or n == "неизвестно":
            return True
        if n in self.BAD_CHANNEL_NAMES:
            return True
        return False

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1280,720")
            chrome_options.add_argument("--lang=ru-RU")
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
            if HAS_WDM:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(20)
            return True
        except Exception as e:
            print(f"Ошибка при создании драйвера: {e}")
            return False

    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def read_links_from_file(self, filepath):
        links = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # auto-split url:email
                    m = re.match(r"^(https?://\S+?):([^\s/]+@[^\s/]+)$", line)
                    if m:
                        links.append({"url": m.group(1), "email": m.group(2)})
                    elif line.startswith("http"):
                        links.append({"url": line, "email": ""})
                    else:
                        links.append(line)
        except Exception as e:
            print("read links:", e)
        return links

    def parse_number(self, text):
        if text is None:
            return 0
        text = str(text).strip().lower().replace("\xa0", " ").replace(" ", "")
        mult = 1
        if "млрд" in text or "b" == text[-1:]:
            mult = 1_000_000_000
            text = re.sub(r"[млрdb]", "", text)
        elif "млн" in text or text.endswith("m"):
            mult = 1_000_000
            text = re.sub(r"[млнm]", "", text)
        elif "тыс" in text or text.endswith("k"):
            mult = 1000
            text = re.sub(r"[тысk.]", "", text)
        text = text.replace(",", ".")
        text = re.sub(r"[^0-9.]", "", text)
        try:
            return int(float(text) * mult) if text else 0
        except Exception:
            return 0

    def format_large_number(self, n):
        try:
            n = int(n)
        except Exception:
            return str(n)
        if n >= 1_000_000_000:
            return f"{n/1_000_000_000:.1f} млрд".replace(".0", "")
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f} млн".replace(".0", "")
        if n >= 1000:
            return f"{n/1000:.1f} тыс".replace(".0", "")
        return str(n)

    def _parse_from_yt_data(self, data, url):
        channel_data = {
            "url": url,
            "channel_name": "Неизвестно",
            "subscribers": "0",
            "total_views": "0",
            "videos_count": "0",
            "email": "",
        }
        try:
            def walk(obj, depth=0):
                if depth > 12:
                    return
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        kl = str(k).lower()
                        if kl in ("title", "channelname", "name") and isinstance(v, str) and len(v) > 1:
                            cand = v.replace(" - YouTube", "").strip()
                            if channel_data["channel_name"] == "Неизвестно" or self._is_bad_channel_name(channel_data["channel_name"]):
                                if not self._is_bad_channel_name(cand):
                                    channel_data["channel_name"] = cand
                        if "subscriber" in kl and isinstance(v, (str, int, float)):
                            channel_data["subscribers"] = str(v)
                        if kl in ("viewcounttext", "viewcount") or ("view" in kl and "count" in kl):
                            if isinstance(v, dict):
                                t = v.get("simpleText") or v.get("content") or ""
                                if t:
                                    channel_data["total_views"] = str(t)
                            elif isinstance(v, (str, int, float)):
                                channel_data["total_views"] = str(v)
                        if "video" in kl and "count" in kl and isinstance(v, (str, int, float)):
                            channel_data["videos_count"] = str(v)
                        if "email" in kl or "businessemail" in kl:
                            if isinstance(v, str) and "@" in v:
                                channel_data["email"] = v
                        walk(v, depth + 1)
                elif isinstance(obj, list):
                    for it in obj[:80]:
                        walk(it, depth + 1)
            walk(data)
        except Exception as e:
            print("yt data walk:", e)
        return channel_data

    def _parse_from_dom(self, url):
        channel_data = {
            "url": url,
            "channel_name": "Неизвестно",
            "subscribers": "0",
            "total_views": "0",
            "videos_count": "0",
            "email": "",
        }
        try:
            for sel in ['meta[property="og:title"]', "#channel-name", "yt-formatted-string#text"]:
                try:
                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if sel.startswith("meta"):
                        name = el.get_attribute("content") or ""
                    else:
                        name = el.text or ""
                    name = name.replace(" - YouTube", "").strip()
                    if name and not self._is_bad_channel_name(name):
                        channel_data["channel_name"] = name
                        break
                except Exception:
                    pass
            if self._is_bad_channel_name(channel_data["channel_name"]):
                title = self.driver.title or ""
                t2 = title.replace(" - YouTube", "").strip()
                if not self._is_bad_channel_name(t2):
                    channel_data["channel_name"] = t2
            src = self.driver.page_source or ""
            m = re.search(r"([\d\s.,]+)\s*(тыс\.?|млн\.?|K|M)?\s*подписчик", src, re.I)
            if m:
                channel_data["subscribers"] = (m.group(1) + " " + (m.group(2) or "")).strip()
            m = re.search(r"([\d\s.,]+)\s*(тыс\.?|млн\.?|K|M)?\s*видео", src, re.I)
            if m:
                channel_data["videos_count"] = (m.group(1) + " " + (m.group(2) or "")).strip()
        except Exception as e:
            print("dom parse:", e)
        return channel_data

    def parse_channel_data(self, url):
        try:
            about_url = url if "/about" in url else url.rstrip("/") + "/about"
            self.driver.get(about_url)
            time.sleep(1.5)
            WebDriverWait(self.driver, 12).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            yt_data = None
            try:
                raw = self.driver.execute_script(
                    "return window.ytInitialData || window.ytInitialPlayerResponse || null;"
                )
                if raw:
                    yt_data = raw if isinstance(raw, dict) else json.loads(raw)
            except Exception:
                yt_data = None
            if yt_data:
                channel_data = self._parse_from_yt_data(yt_data, url)
            else:
                channel_data = self._parse_from_dom(url)
            if channel_data.get("channel_name") in (None, "", "Неизвестно") or self._is_bad_channel_name(channel_data.get("channel_name")):
                dom = self._parse_from_dom(url)
                for k in ("channel_name", "subscribers", "total_views", "videos_count", "email"):
                    if not channel_data.get(k) or channel_data.get(k) in ("0", "Неизвестно") or (k == "channel_name" and self._is_bad_channel_name(channel_data.get(k))):
                        if dom.get(k) and not (k == "channel_name" and self._is_bad_channel_name(dom.get(k))):
                            channel_data[k] = dom[k]
            # strong extract from page source
            try:
                src_html = self.driver.page_source or ""
                if self._is_bad_channel_name(channel_data.get("channel_name")):
                    om = re.search(r'property="og:title"\s+content="([^"]+)"', src_html)
                    if not om:
                        om = re.search(r'content="([^"]+)"\s+property="og:title"', src_html)
                    if om:
                        cand = om.group(1).replace(" - YouTube", "").strip()
                        if not self._is_bad_channel_name(cand):
                            channel_data["channel_name"] = cand
                    if self._is_bad_channel_name(channel_data.get("channel_name")):
                        um = re.search(r"youtube\.com/@([^/?&#]+)", url or "")
                        if um:
                            channel_data["channel_name"] = "@" + um.group(1)
                sm = re.search(
                    r'"subscriberCountText"\s*:\s*\{[^}]*?"simpleText"\s*:\s*"([^"]+)"',
                    src_html,
                )
                if sm:
                    channel_data["subscribers"] = sm.group(1).strip()
                elif channel_data.get("subscribers") in ("0", "", None):
                    sm2 = re.search(r"([\d\s.,]+)\s*(тыс\.?|млн\.?|K|M)?\s*подписчик", src_html, re.I)
                    if sm2:
                        channel_data["subscribers"] = (sm2.group(1) + " " + (sm2.group(2) or "")).strip()
                if channel_data.get("videos_count") in ("0", "", None):
                    vm = re.search(r"([\d\s.,]+)\s*(тыс\.?|млн\.?|K|M)?\s*видео", src_html, re.I)
                    if vm:
                        channel_data["videos_count"] = (vm.group(1) + " " + (vm.group(2) or "")).strip()
            except Exception:
                pass
            if self._is_bad_channel_name(channel_data.get("channel_name")):
                um = re.search(r"youtube\.com/@([^/?&#]+)", url or "")
                if um:
                    channel_data["channel_name"] = "@" + um.group(1)
            channel_data["subscribers_num"] = self.parse_number(channel_data.get("subscribers"))
            channel_data["total_views_num"] = self.parse_number(channel_data.get("total_views"))
            channel_data["videos_count_num"] = self.parse_number(channel_data.get("videos_count"))
            if channel_data.get("subscribers_num"):
                channel_data["subscribers"] = self.format_large_number(channel_data["subscribers_num"])
            if channel_data.get("total_views_num"):
                channel_data["total_views"] = self.format_large_number(channel_data["total_views_num"])
            return channel_data
        except TimeoutException:
            return {"url": url, "error": "Таймаут загрузки страницы"}
        except WebDriverException as e:
            return {"url": url, "error": f"Ошибка браузера: {str(e)[:120]}"}
        except Exception as e:
            return {"url": url, "error": f"Ошибка парсинга: {str(e)[:120]}"}

    def parse_channels(self, links_file, progress_callback=None):
        if not self.setup_driver():
            return [{
                "error": "Не удалось создать драйвер браузера. "
                "Установите Chrome и выполните: pip install webdriver-manager"
            }]
        raw = self.read_links_from_file(links_file)
        if not raw:
            return [{"error": "Не найдено ссылок для обработки"}]
        links = []
        for item in raw:
            if isinstance(item, dict):
                links.append(item)
            else:
                links.append({"url": str(item), "email": ""})
        results = []
        total = len(links)
        try:
            for i, item in enumerate(links, 1):
                url = item.get("url") if isinstance(item, dict) else str(item)
                preset_email = (item.get("email") or "") if isinstance(item, dict) else ""
                if progress_callback:
                    try:
                        progress_callback(i, total, url)
                    except Exception:
                        pass
                about_url = url
                data = self.parse_channel_data(about_url)
                if preset_email and not data.get("email"):
                    data["email"] = preset_email
                results.append(data)
                time.sleep(0.4)
        finally:
            self.close_driver()
        return results
