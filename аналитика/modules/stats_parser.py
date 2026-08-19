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
    def __init__(self):
        self.driver = None

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

    @staticmethod
    def split_url_email(line):
        """Split 'https://youtube.com/@ch:email@gmail.com' -> (url, email)."""
        line = (line or "").strip()
        if not line or line.startswith("#"):
            return "", ""
        if line.startswith("."):
            line = line[1:]
        m = re.match(
            r"^(https?://.+?):([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})$",
            line,
        )
        if m:
            return m.group(1).rstrip("/"), m.group(2).strip()
        parts = line.split()
        if len(parts) >= 2 and "@" in parts[-1] and "." in parts[-1]:
            return parts[0].rstrip("/"), parts[-1].strip()
        return line.rstrip("/"), ""

    def read_links_from_file(self, filename):
        """Читает ссылки из файла. Поддерживает формат url и url:email."""
        links = []
        try:
            with open(filename, "r", encoding="utf-8") as file:
                for line in file:
                    url, email = self.split_url_email(line)
                    if not url:
                        continue
                    links.append({"url": url, "email": email})
            return links
        except FileNotFoundError:
            print(f"Файл {filename} не найден!")
            return []
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return []

    def get_channel_about_page(self, channel_url):
        """Преобразует URL канала в URL страницы About"""
        channel_url, _em = self.split_url_email(channel_url)
        channel_url = channel_url.strip().rstrip("/")
        if "/about" in channel_url:
            return channel_url
        if "/channel/" in channel_url:
            channel_id = channel_url.split("/channel/")[-1].split("/")[0]
            return f"https://www.youtube.com/channel/{channel_id}/about"
        if "/@" in channel_url:
            username = channel_url.split("/@")[-1].split("/")[0]
            return f"https://www.youtube.com/@{username}/about"
        if "/c/" in channel_url or "/user/" in channel_url:
            return channel_url + "/about"
        parsed = urlparse(channel_url)
        if parsed.path and parsed.path != "/":
            return channel_url.rstrip("/") + "/about"
        return channel_url + "/about"

    def parse_number(self, text):
        if text is None:
            return 0
        text = str(text).strip().lower().replace("\xa0", " ").replace(",", ".")
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        mult = 1
        for key, val in [("тыс", 1000), ("million", 1e6), ("млн", 1e6), ("млрд", 1e9), ("k", 1000), ("m", 1e6), ("b", 1e9)]:
            if key in text:
                mult = val
                text = text.replace(key, "").strip()
                break
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
                            if channel_data["channel_name"] == "Неизвестно":
                                channel_data["channel_name"] = v.replace(" - YouTube", "").strip()
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
                    for it in obj[:50]:
                        walk(it, depth + 1)
            walk(data)
        except Exception:
            pass
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
                        name = (el.get_attribute("content") or "").replace(" - YouTube", "").strip()
                    else:
                        name = el.text.strip()
                    if name:
                        channel_data["channel_name"] = name
                        break
                except Exception:
                    pass
            try:
                title = self.driver.title or ""
                channel_data["channel_name"] = title.replace(" - YouTube", "").strip() or channel_data["channel_name"]
            except Exception:
                pass
            page = self.driver.page_source or ""
            m = re.search(r"([\d\s.,]+)\s*(подписчик|subscriber)", page, re.I)
            if m:
                channel_data["subscribers"] = (m.group(1) + " " + (m.group(2) or "")).strip()
            m = re.search(r"([\d\s.,]+)\s*(просмотр|view)", page, re.I)
            if m:
                channel_data["total_views"] = (m.group(1) + " " + (m.group(2) or "")).strip()
            m = re.search(r"([\d\s.,]+)\s*(видео|video)", page, re.I)
            if m:
                channel_data["videos_count"] = (m.group(1) + " " + (m.group(2) or "")).strip()
            m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", page)
            if m:
                channel_data["email"] = m.group(0)
        except Exception:
            pass
        return channel_data

    def parse_channel_data(self, url):
        try:
            self.driver.get(url)
            time.sleep(1.2)
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
            if channel_data.get("channel_name") in (None, "", "Неизвестно"):
                dom = self._parse_from_dom(url)
                for k in ("channel_name", "subscribers", "total_views", "videos_count", "email"):
                    if not channel_data.get(k) or channel_data.get(k) in ("0", "Неизвестно"):
                        if dom.get(k):
                            channel_data[k] = dom[k]
            # numeric helpers
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
        """Парсит список каналов из файла"""
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
                u, e = self.split_url_email(str(item))
                if u:
                    links.append({"url": u, "email": e})

        results = []
        total = len(links)

        try:
            for i, item in enumerate(links, 1):
                link = item.get("url") or ""
                email = item.get("email") or ""
                if progress_callback:
                    progress_callback(i, total, link)
                about_url = self.get_channel_about_page(link)
                data = self.parse_channel_data(about_url)
                if data.get("channel_name") and data["channel_name"] != "Неизвестно":
                    data["url"] = link
                else:
                    data.setdefault("url", link)
                if email and not data.get("email"):
                    data["email"] = email
                results.append(data)
                if i < total:
                    time.sleep(0.8)
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
        return results
