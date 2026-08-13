"""
Модуль для парсинга статистики YouTube каналов
"""
import sys
import os
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class StatsParser:
    def __init__(self):
        self.driver = None
    
    def setup_driver(self):
        """Настройка Chrome драйвера"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            print(f"Ошибка при создании драйвера: {e}")
            return False
    
    def read_links_from_file(self, filename):
        """Читает ссылки из файла"""
        links = []
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if line.startswith('.'):
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
        """Преобразует URL канала в URL страницы 'About'"""
        if '/channel/' in channel_url:
            channel_id = channel_url.split('/channel/')[-1].split('/')[0]
            return f"https://www.youtube.com/channel/{channel_id}/about"
        elif '/@' in channel_url:
            username = channel_url.split('/@')[-1].split('/')[0]
            return f"https://www.youtube.com/@{username}/about"
        elif '/about' in channel_url:
            return channel_url
        else:
            parsed = urlparse(channel_url)
            path_parts = parsed.path.split('/')
            if len(path_parts) > 1 and path_parts[1]:
                return f"https://www.youtube.com/{path_parts[1]}/about"
            return channel_url + '/about'
    
    def parse_number(self, text):
        """Преобразует текст с числами в числовое значение"""
        if not text or text == 'Неизвестно' or text == '0':
            return 0
        
        cleaned = re.sub(r'[^\d,.]', '', str(text))
        cleaned = cleaned.replace(',', '.')
        
        try:
            num = float(cleaned)
            return int(num) if num.is_integer() else num
        except:
            return 0
    
    def format_large_number(self, number):
        """Форматирует большие числа для красивого вывода"""
        if number >= 1_000_000_000:
            return f"{number / 1_000_000_000:.1f} млрд"
        elif number >= 1_000_000:
            return f"{number / 1_000_000:.1f} млн"
        elif number >= 1_000:
            return f"{number / 1_000:.1f} тыс"
        else:
            return f"{number:,}".replace(',', ' ')
    
    def parse_channel_data(self, url):
        """Парсит данные канала"""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            
            channel_data = {
                'url': url,
                'channel_name': '',
                'description': '',
                'total_views': '0',
                'subscribers': 'Неизвестно',
                'videos_count': '0',
                'join_date': '',
                'country': '',
                'links': []
            }
            
            # Поиск названия канала
            try:
                channel_name_elem = self.driver.find_element(By.CSS_SELECTOR, "yt-formatted-string#channel-handle")
                channel_data['channel_name'] = channel_name_elem.text
            except:
                try:
                    title_elem = self.driver.find_element(By.TAG_NAME, "title")
                    channel_data['channel_name'] = title_elem.get_attribute("textContent").replace(' - YouTube', '')
                except:
                    channel_data['channel_name'] = "Неизвестно"
            
            # Поиск описания
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, "yt-formatted-string#description")
                channel_data['description'] = desc_elem.text
            except:
                channel_data['description'] = ""
            
            # Поиск всех строк с информацией
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.description-item")
                for row in rows:
                    try:
                        row_text = row.text
                        
                        if 'просмотр' in row_text.lower():
                            parts = row_text.split('просмотр')
                            if parts:
                                channel_data['total_views'] = parts[0].strip()
                        
                        if 'видео' in row_text.lower():
                            parts = row_text.split('видео')
                            if parts:
                                channel_data['videos_count'] = parts[0].strip()
                        
                        if 'дата регистрации:' in row_text.lower():
                            channel_data['join_date'] = row_text.replace('Дата регистрации:', '').strip()
                        
                        if 'страна' in row_text.lower():
                            parts = row_text.split('Страна')
                            if len(parts) > 1:
                                channel_data['country'] = parts[1].strip()
                    except:
                        continue
            except:
                pass
            
            # Поиск подписчиков
            try:
                meta_elems = self.driver.find_elements(By.TAG_NAME, "meta")
                for meta in meta_elems:
                    content = meta.get_attribute("content")
                    if content and 'подписчик' in content:
                        match = re.search(r'(\d+[\d\s,]*)\s*подписчик', content)
                        if match:
                            channel_data['subscribers'] = match.group(1)
            except:
                pass
            
            # Альтернативный поиск просмотров
            if channel_data['total_views'] == '0':
                try:
                    elements_with_views = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'просмотр')]")
                    for elem in elements_with_views:
                        text = elem.text
                        if 'просмотр' in text:
                            match = re.search(r'([\d\s,]+)\s*просмотр', text)
                            if match:
                                channel_data['total_views'] = match.group(1).strip()
                                break
                except:
                    pass
            
            return channel_data
            
        except Exception as e:
            return {'url': url, 'error': f'Ошибка парсинга: {str(e)}'}
    
    def parse_channels(self, links_file, progress_callback=None):
        """Парсит список каналов из файла"""
        if not self.setup_driver():
            return [{'error': 'Не удалось создать драйвер браузера. Проверьте Chrome и ChromeDriver.'}]
        
        links = self.read_links_from_file(links_file)
        if not links:
            return [{'error': 'Не найдено ссылок для обработки'}]
        
        results = []
        total = len(links)
        
        try:
            for i, link in enumerate(links, 1):
                if progress_callback:
                    progress_callback(i, total, link)
                about_url = self.get_channel_about_page(link)
                data = self.parse_channel_data(about_url)
                if data.get('channel_name') and data['channel_name'] != 'Неизвестно':
                    data['url'] = link
                results.append(data)
                time.sleep(2)
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        return results

