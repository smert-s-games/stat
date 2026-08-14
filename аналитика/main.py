"""
Модуль для парсинга статистики YouTube каналов
Оптимизирован: быстрее загрузка, надёжный разбор чисел и данных, ytInitialData
"""
import re
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from urllib.parse import urlparse

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False


class StatsParser:
    def __init__(self):
        self.driver = None

    def setup_driver(self):
        """Настройка Chrome драйвера (быстрый headless)"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--window-size=1280,720")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
        chrome_options.page_load_strategy = "eager"

        try:
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

    def read_links_from_file(self, filename):
        """Читает ссылки из файла"""
        links = []
        try:
            with open(filename, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if line.startswith("."):
                            line = line[1:]
                        links.append(line)
            return links
        except FileNotFoundError:
            print(f"Файл {filename} не найден!")
            return []
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return []

    def get_channel_about_page(self, channel_url):
        """Преобразует URL канала в URL страницы About"""
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
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            return f"https://www.youtube.com/{path_parts[0]}/about"
        return channel_url + "/about"

    def parse_number(self, text):
        """
        Преобразует текст с числами (включая K/M/B, тыс/млн/млрд) в int.
        Примеры: '1,2 млн' → 1200000, '15K' → 15000, '3.4B' → 3400000000
        """
        if not text or text in ("Неизвестно", "0", "-", "N/A"):
            return 0

        text = str(text).strip().lower().replace("\xa0", " ").replace(",", ".")
        text = re.sub(r"(подписчик|просмотр|видео|views?|subscribers?|videos?).*$", "", text, flags=re.I)
        text = text.strip()

        multipliers = {
            "k": 1_000,
            "тыс": 1_000,
            "тыс.": 1_000,
            "m": 1_000_000,
            "млн": 1_000_000,
            "млн.": 1_000_000,
            "b": 1_000_000_000,
            "млрд": 1_000_000_000,
            "млрд.": 1_000_000_000,
            "billion": 1_000_000_000,
            "million": 1_000_000,
            "thousand": 1_000,
        }

        mult = 1
        for key, val in multipliers.items():
            if key in text:
                mult = val
                text = text.replace(key, "").strip()
                break

        cleaned = re.sub(r"[^\d.]", "", text)
        if not cleaned:
            return 0

        try:
            num = float(cleaned) * mult
            return int(num)
        except ValueError:
            return 0

    def format_large_number(self, number):
        """Форматирует большие числа для красивого вывода"""
        try:
            number = int(number)
        except (TypeError, ValueError):
            return "0"
        if number >= 1_000_000_000:
            return f"{number / 1_000_000_000:.1f} млрд"
        if number >= 1_000_000:
            return f"{number / 1_000_000:.1f} млн"
        if number >= 1_000:
            return f"{number / 1_000:.1f} тыс"
        return f"{number:,}".replace(",", " ")

    def _extract_yt_initial_data(self):
        """Достаёт ytInitialData из страницы — самый надёжный источник"""
        try:
            scripts = self.driver.find_elements(By.TAG_NAME, "script")
            for script in scripts:
                content = script.get_attribute("innerHTML") or ""
                if "ytInitialData" not in content:
                    continue
                match = re.search(r"var\s+ytInitialData\s*=\s*(\{.+?\});", content, re.DOTALL)
                if not match:
                    match = re.search(r"ytInitialData\s*=\s*(\{.+?\});", content, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return None

    def _parse_from_yt_data(self, data, url):
        """Парсинг из ytInitialData"""
        channel_data = {
            "url": url,
            "channel_name": "",
            "description": "",
            "total_views": "0",
            "subscribers": "Неизвестно",
            "videos_count": "0",
            "join_date": "",
            "country": "",
            "links": [],
        }
        if not data:
            return None

        try:
            header = (
                data.get("header", {}).get("c4TabbedHeaderRenderer", {})
                or data.get("header", {}).get("pageHeaderRenderer", {})
            )
            if header:
                title = header.get("title") or header.get("pageTitle")
                if isinstance(title, dict):
                    title = title.get("simpleText") or title.get("content")
                if title:
                    channel_data["channel_name"] = str(title)

                for key in ("subscriberCountText", "subscriberCountLabel"):
                    node = header.get(key)
                    if node:
                        sub_text = node.get("simpleText") or (
                            node.get("runs", [{}])[0].get("text") if node.get("runs") else None
                        )
                        if sub_text:
                            channel_data["subscribers"] = sub_text
                            break

            metadata = None
            try:
                tabs = (
                    data.get("contents", {})
                    .get("twoColumnBrowseResultsRenderer", {})
                    .get("tabs", [])
                )
                for tab in tabs:
                    tab_renderer = tab.get("tabRenderer", {})
                    if tab_renderer.get("title") in ("О канале", "About", "Info"):
                        content = tab_renderer.get("content", {})
                        section = content.get("sectionListRenderer", {}).get("contents", [])
                        for s in section:
                            item = s.get("itemSectionRenderer", {}).get("contents", [])
                            for i in item:
                                if "channelAboutFullMetadataRenderer" in i:
                                    metadata = i["channelAboutFullMetadataRenderer"]
                                    break
                            if metadata:
                                break
                    if metadata:
                        break
            except Exception:
                pass

            if metadata:
                title = metadata.get("title", {})
                if isinstance(title, dict):
                    t = title.get("simpleText") or (
                        title.get("runs", [{}])[0].get("text") if title.get("runs") else ""
                    )
                    if t:
                        channel_data["channel_name"] = t

                desc = metadata.get("description", {})
                if isinstance(desc, dict):
                    channel_data["description"] = desc.get("simpleText") or ""
                    if not channel_data["description"] and desc.get("runs"):
                        channel_data["description"] = "".join(r.get("text", "") for r in desc["runs"])

                view_count = metadata.get("viewCountText", {})
                if isinstance(view_count, dict):
                    vt = view_count.get("simpleText") or (
                        view_count.get("runs", [{}])[0].get("text") if view_count.get("runs") else ""
                    )
                    if vt:
                        channel_data["total_views"] = vt

                for row in metadata.get("joinedDateText", {}).get("runs", []) or []:
                    text = row.get("text", "")
                    if text:
                        channel_data["join_date"] = text

                country = metadata.get("country", {})
                if isinstance(country, dict):
                    channel_data["country"] = country.get("simpleText") or ""

            micro = data.get("metadata", {}).get("channelMetadataRenderer", {})
            if micro:
                if not channel_data["channel_name"]:
                    channel_data["channel_name"] = micro.get("title", "")
                if not channel_data["description"]:
                    channel_data["description"] = micro.get("description", "")

            return channel_data
        except Exception:
            return None

    def _parse_from_dom(self, url):
        """Запасной парсинг через DOM"""
        channel_data = {
            "url": url,
            "channel_name": "",
            "description": "",
            "total_views": "0",
            "subscribers": "Неизвестно",
            "videos_count": "0",
            "join_date": "",
            "country": "",
            "links": [],
        }

        for selector in (
            "yt-formatted-string#channel-handle",
            "#channel-name yt-formatted-string",
            "ytd-channel-name yt-formatted-string",
            "meta[property='og:title']",
        ):
            try:
                if selector.startswith("meta"):
                    el = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = (el.get_attribute("content") or "").replace(" - YouTube", "").strip()
                else:
                    el = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = el.text.strip()
                if name:
                    channel_data["channel_name"] = name
                    break
            except Exception:
                continue

        if not channel_data["channel_name"]:
            try:
                title = self.driver.title or ""
                channel_data["channel_name"] = title.replace(" - YouTube", "").strip() or "Неизвестно"
            except Exception:
                channel_data["channel_name"] = "Неизвестно"

        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            body_text = ""

        m = re.search(r"([\d\s.,]+)\s*(тыс\.?|млн\.?|млрд\.?|K|M|B)?\s*подписчик", body_text, re.I)
        if m:
            channel_data["subscribers"] = (m.group(1) + " " + (m.group(2) or "")).strip()

        m = re.search(r"([\d\s.,]+)\s*(тыс\.?|млн\.?|млрд\.?|K|M|B)?\s*просмотр", body_text, re.I)
        if m:
            channel_data["total_views"] = (m.group(1) + " " + (m.group(2) or "")).strip()

        m = re.search(r"([\d\s.,]+)\s*(тыс\.?|млн\.?|млрд\.?|K|M|B)?\s*видео", body_text, re.I)
        if m:
            channel_data["videos_count"] = (m.group(1) + " " + (m.group(2) or "")).strip()

        if channel_data["subscribers"] == "Неизвестно":
            try:
                for meta in self.driver.find_elements(By.TAG_NAME, "meta"):
                    content = meta.get_attribute("content") or ""
                    if "подписчик" in content.lower() or "subscriber" in content.lower():
                        m = re.search(r"([\d\s.,]+)\s*(тыс\.?|млн\.?|K|M)?", content, re.I)
                        if m:
                            channel_data["subscribers"] = m.group(0).strip()
                            break
            except Exception:
                pass

        return channel_data

    def parse_channel_data(self, url):
        """Парсит данные канала (ytInitialData + DOM fallback)"""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 12).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(1.2)

            yt_data = self._extract_yt_initial_data()
            channel_data = self._parse_from_yt_data(yt_data, url)

            if not channel_data or (
                not channel_data.get("channel_name")
                and channel_data.get("subscribers") == "Неизвестно"
            ):
                channel_data = self._parse_from_dom(url)
            else:
                if channel_data.get("subscribers") == "Неизвестно" or channel_data.get("total_views") == "0":
                    dom = self._parse_from_dom(url)
                    if channel_data.get("subscribers") == "Неизвестно" and dom.get("subscribers") != "Неизвестно":
                        channel_data["subscribers"] = dom["subscribers"]
                    if channel_data.get("total_views") in ("0", "") and dom.get("total_views") not in ("0", ""):
                        channel_data["total_views"] = dom["total_views"]
                    if channel_data.get("videos_count") in ("0", "") and dom.get("videos_count") not in ("0", ""):
                        channel_data["videos_count"] = dom["videos_count"]
                    if not channel_data.get("channel_name") and dom.get("channel_name"):
                        channel_data["channel_name"] = dom["channel_name"]

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

        links = self.read_links_from_file(links_file)
        if not links:
            return [{"error": "Не найдено ссылок для обработки"}]

        results = []
        total = len(links)

        try:
            for i, link in enumerate(links, 1):
                if progress_callback:
                    progress_callback(i, total, link)
                about_url = self.get_channel_about_page(link)
                data = self.parse_channel_data(about_url)
                if data.get("channel_name") and data["channel_name"] != "Неизвестно":
                    data["url"] = link
                results.append(data)
                if i < total:
                    time.sleep(0.8)
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None

        return results
