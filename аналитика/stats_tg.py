from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
import os
import json
from urllib.parse import urlparse
import requests
import schedule
import threading
from datetime import datetime, timedelta

# ===== ТЕЛЕГРАМ НАСТРОЙКИ =====
# Укажите токен и chat id в config.json или через переменные окружения
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Глобальные переменные для хранения статистики
daily_stats = {
    'last_run': None,
    'total_channels_processed': 0,
    'successful_parses': 0,
    'failed_parses': 0,
    'total_views_today': 0,
    'total_subscribers_today': 0,
    'total_videos_today': 0
}

def setup_driver():
    """Настройка Chrome драйвера"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Фоновый режим
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def read_links_from_file(filename):
    """
    Читает ссылки из файла
    """
    links = []
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):  # Пропускаем пустые строки и комментарии
                    # Убираем точку в начале ссылки, если есть
                    if line.startswith('.'):
                        line = line[1:]
                    links.append(line)
        return links
    except FileNotFoundError:
        print(f"❌ Файл {filename} не найден!")
        return []
    except Exception as e:
        print(f"❌ Ошибка при чтении файла: {e}")
        return []

def get_channel_about_page(channel_url):
    """
    Преобразует URL канала в URL страницы 'About'
    """
    # Если это обычная ссылка на канал
    if '/channel/' in channel_url:
        channel_id = channel_url.split('/channel/')[-1].split('/')[0]
        return f"https://www.youtube.com/channel/{channel_id}/about"
    # Если это пользовательская ссылка (как @TheBeautifulGame-l5k)
    elif '/@' in channel_url:
        username = channel_url.split('/@')[-1].split('/')[0]
        return f"https://www.youtube.com/@{username}/about"
    # Если это уже страница about
    elif '/about' in channel_url:
        return channel_url
    else:
        # Пытаемся извлечь имя канала из URL
        parsed = urlparse(channel_url)
        path_parts = parsed.path.split('/')
        if len(path_parts) > 1 and path_parts[1]:
            return f"https://www.youtube.com/{path_parts[1]}/about"
        return channel_url + '/about'

def parse_number(text):
    """Преобразует текст с числами в числовое значение"""
    if not text or text == 'Неизвестно' or text == '0':
        return 0
    
    # Убираем пробелы и нечисловые символы, кроме точек и запятых
    cleaned = re.sub(r'[^\d,.]', '', str(text))
    
    # Заменяем запятую на точку для дробных чисел
    cleaned = cleaned.replace(',', '.')
    
    try:
        # Пробуем преобразовать в float, затем в int
        num = float(cleaned)
        return int(num) if num.is_integer() else num
    except:
        return 0

def calculate_total_statistics(results):
    """Подсчитывает общую статистику по всем каналам"""
    total_channels = 0
    total_videos = 0
    total_views = 0
    total_subscribers = 0
    
    successful_channels = 0
    
    for result in results:
        if 'error' not in result:
            successful_channels += 1
            
            # Считаем видео
            videos = parse_number(result.get('videos_count', '0'))
            total_videos += videos
            
            # Считаем просмотры
            views_text = result.get('total_views', '0')
            views = parse_number(views_text)
            total_views += views
            
            # Считаем подписчиков
            subs_text = result.get('subscribers', '0')
            subs = parse_number(subs_text)
            total_subscribers += subs
    
    total_channels = successful_channels
    
    return {
        'total_channels': total_channels,
        'total_videos': total_videos,
        'total_views': total_views,
        'total_subscribers': total_subscribers
    }

def format_large_number(number):
    """Форматирует большие числа для красивого вывода"""
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f} млрд"
    elif number >= 1_000_000:
        return f"{number / 1_000_000:.1f} млн"
    elif number >= 1_000:
        return f"{number / 1_000:.1f} тыс"
    else:
        return f"{number:,}".replace(',', ' ')

def parse_channel_data_selenium(driver, url):
    """
    Парсит данные канала с использованием Selenium
    """
    try:
        print(f"   🌐 Загружаем страницу...")
        driver.get(url)
        
        # Ждем загрузки контента
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Даем время для загрузки динамического контента
        time.sleep(3)
        
        # Получаем HTML после выполнения JavaScript
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
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
        
        # Способ 1: Поиск в основном контенте
        print(f"   🔍 Ищем данные в основном контенте...")
        
        # Поиск названия канала
        try:
            channel_name_elem = driver.find_element(By.CSS_SELECTOR, "yt-formatted-string#channel-handle")
            channel_data['channel_name'] = channel_name_elem.text
        except:
            try:
                title_elem = driver.find_element(By.TAG_NAME, "title")
                channel_data['channel_name'] = title_elem.get_attribute("textContent").replace(' - YouTube', '')
            except:
                channel_data['channel_name'] = "Неизвестно"
        
        # Поиск описания
        try:
            desc_elem = driver.find_element(By.CSS_SELECTOR, "yt-formatted-string#description")
            channel_data['description'] = desc_elem.text
        except:
            channel_data['description'] = ""
        
        # Поиск всех строк с информацией
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.description-item")
            for row in rows:
                try:
                    # Получаем текст всей строки
                    row_text = row.text
                    
                    # Просмотры
                    if 'просмотр' in row_text.lower():
                        parts = row_text.split('просмотр')
                        if parts:
                            channel_data['total_views'] = parts[0].strip()
                    
                    # Видео
                    if 'видео' in row_text.lower():
                        parts = row_text.split('видео')
                        if parts:
                            channel_data['videos_count'] = parts[0].strip()
                    
                    # Дата регистрации
                    if 'дата регистрации:' in row_text.lower():
                        channel_data['join_date'] = row_text.replace('Дата регистрации:', '').strip()
                    
                    # Страна
                    if 'страна' in row_text.lower():
                        parts = row_text.split('Страна')
                        if len(parts) > 1:
                            channel_data['country'] = parts[1].strip()
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"   ⚠️ Ошибка при парсинге строк: {e}")
        
        # Способ 2: Поиск в meta-тегах
        try:
            meta_elems = driver.find_elements(By.TAG_NAME, "meta")
            for meta in meta_elems:
                content = meta.get_attribute("content")
                if content:
                    # Подписчики в описании
                    if 'подписчик' in content:
                        match = re.search(r'(\d+[\d\s,]*)\s*подписчик', content)
                        if match:
                            channel_data['subscribers'] = match.group(1)
        except:
            pass
        
        # Способ 3: Поиск в JSON-LD данных
        try:
            script_elems = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
            for script in script_elems:
                try:
                    json_data = json.loads(script.get_attribute("innerHTML"))
                    if isinstance(json_data, dict):
                        # Просмотры
                        if 'interactionStatistic' in json_data:
                            for stat in json_data['interactionStatistic']:
                                if stat.get('interactionType') == 'https://schema.org/WatchAction':
                                    channel_data['total_views'] = str(stat.get('userInteractionCount', '0'))
                                elif stat.get('interactionType') == 'https://schema.org/FollowAction':
                                    channel_data['subscribers'] = str(stat.get('userInteractionCount', 'Неизвестно'))
                except:
                    continue
        except:
            pass
        
        # Если просмотры не найдены, пытаемся найти альтернативными способами
        if channel_data['total_views'] == '0':
            try:
                # Ищем любой элемент содержащий "просмотр"
                elements_with_views = driver.find_elements(By.XPATH, "//*[contains(text(), 'просмотр')]")
                for elem in elements_with_views:
                    text = elem.text
                    if 'просмотр' in text:
                        # Извлекаем число перед "просмотр"
                        match = re.search(r'([\d\s,]+)\s*просмотр', text)
                        if match:
                            channel_data['total_views'] = match.group(1).strip()
                            break
            except:
                pass
        
        return channel_data
        
    except Exception as e:
        return {'url': url, 'error': f'Ошибка парсинга: {str(e)}'}

def save_results_to_file(results, filename, total_stats):
    """
    Сохраняет результаты в файл
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("YouTube Channels Parser Results (Selenium)\n")
            f.write("=" * 70 + "\n\n")
            
            # Записываем общую статистику в начало файла
            f.write("📊 ОБЩАЯ СТАТИСТИКА ПО ВСЕМ КАНАЛАМ:\n")
            f.write(f"   📈 Количество каналов: {total_stats['total_channels']}\n")
            f.write(f"   🎥 Общее количество видео: {total_stats['total_videos']:,} ({format_large_number(total_stats['total_videos'])})\n")
            f.write(f"   👀 Общее количество просмотров: {total_stats['total_views']:,} ({format_large_number(total_stats['total_views'])})\n")
            f.write(f"   👥 Общее количество подписчиков: {total_stats['total_subscribers']:,} ({format_large_number(total_stats['total_subscribers'])})\n")
            f.write(f"   📊 Средние показатели на канал:\n")
            f.write(f"      🎥 Видео: {total_stats['total_videos'] // max(1, total_stats['total_channels']):,}\n")
            f.write(f"      👀 Просмотры: {total_stats['total_views'] // max(1, total_stats['total_channels']):,}\n")
            f.write(f"      👥 Подписчики: {total_stats['total_subscribers'] // max(1, total_stats['total_channels']):,}\n")
            f.write("\n" + "=" * 70 + "\n\n")
            
            for i, result in enumerate(results, 1):
                f.write(f"КАНАЛ {i}:\n")
                f.write(f"🔗 URL: {result['url']}\n")
                
                if 'error' in result:
                    f.write(f"❌ ОШИБКА: {result['error']}\n")
                else:
                    f.write(f"📺 Название: {result.get('channel_name', 'Неизвестно')}\n")
                    f.write(f"👥 Подписчики: {result.get('subscribers', 'Неизвестно')}\n")
                    f.write(f"👀 Всего просмотров: {result.get('total_views', '0')}\n")
                    f.write(f"🎥 Количество видео: {result.get('videos_count', '0')}\n")
                    f.write(f"📅 Дата регистрации: {result.get('join_date', 'Неизвестно')}\n")
                    
                    if result.get('country'):
                        f.write(f"🌍 Страна: {result['country']}\n")
                    
                    if result.get('description'):
                        desc = result['description'][:200] + "..." if len(result['description']) > 200 else result['description']
                        f.write(f"📝 Описание: {desc}\n")
                
                f.write("\n" + "-" * 70 + "\n\n")
        
        print(f"✅ Результаты сохранены в файл: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении файла: {e}")
        return False

# ===== ТЕЛЕГРАМ ФУНКЦИИ =====

def send_telegram_message(message):
    """
    Отправляет сообщение в Telegram
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Сообщение отправлено в Telegram")
            return True
        else:
            print(f"❌ Ошибка отправки в Telegram: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при отправке в Telegram: {e}")
        return False

def format_telegram_stats(stats):
    """
    Форматирует статистику для Telegram сообщения
    """
    message = "📊 <b>ЕЖЕДНЕВНАЯ СТАТИСТИКА YouTube Парсера</b>\n\n"
    
    if stats['last_run']:
        message += f"📅 <b>Последний запуск:</b> {stats['last_run']}\n"
    
    message += f"🔍 <b>Обработано каналов:</b> {stats['total_channels_processed']}\n"
    message += f"✅ <b>Успешных парсингов:</b> {stats['successful_parses']}\n"
    message += f"❌ <b>Ошибок парсинга:</b> {stats['failed_parses']}\n"
    
    if stats['successful_parses'] > 0:
        success_rate = (stats['successful_parses'] / stats['total_channels_processed']) * 100
        message += f"📈 <b>Успешность:</b> {success_rate:.1f}%\n\n"
    
    message += f"👀 <b>Всего просмотров сегодня:</b> {format_large_number(stats['total_views_today'])}\n"
    message += f"👥 <b>Всего подписчиков сегодня:</b> {format_large_number(stats['total_subscribers_today'])}\n"
    message += f"🎥 <b>Всего видео сегодня:</b> {format_large_number(stats['total_videos_today'])}\n"
    
    if stats['successful_parses'] > 0:
        avg_views = stats['total_views_today'] // stats['successful_parses']
        avg_subs = stats['total_subscribers_today'] // stats['successful_parses']
        avg_videos = stats['total_videos_today'] // stats['successful_parses']
        
        message += f"\n<b>Средние показатели на канал:</b>\n"
        message += f"   👀 Просмотры: {format_large_number(avg_views)}\n"
        message += f"   👥 Подписчики: {format_large_number(avg_subs)}\n"
        message += f"   🎥 Видео: {format_large_number(avg_videos)}\n"
    
    message += f"\n⏰ <i>Следующий отчет: завтра в 09:00</i>"
    
    return message

def update_daily_stats(results):
    """
    Обновляет ежедневную статистику
    """
    global daily_stats
    
    total_stats = calculate_total_statistics(results)
    successful = sum(1 for r in results if 'error' not in r)
    failed = sum(1 for r in results if 'error' in r)
    
    daily_stats.update({
        'last_run': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_channels_processed': len(results),
        'successful_parses': successful,
        'failed_parses': failed,
        'total_views_today': total_stats['total_views'],
        'total_subscribers_today': total_stats['total_subscribers'],
        'total_videos_today': total_stats['total_videos']
    })

def send_daily_report():
    """
    Отправляет ежедневный отчет в Telegram
    """
    print("📨 Отправка ежедневного отчета в Telegram...")
    message = format_telegram_stats(daily_stats)
    send_telegram_message(message)

def schedule_daily_report():
    """
    Настраивает ежедневную отправку отчета в 09:00
    """
    schedule.every().day.at("09:00").do(send_daily_report)
    
    print("⏰ Планировщик запущен. Ежедневный отчет будет отправляться в 09:00")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверка каждую минуту

def start_scheduler():
    """
    Запускает планировщик в отдельном потоке
    """
    scheduler_thread = threading.Thread(target=schedule_daily_report, daemon=True)
    scheduler_thread.start()

def send_startup_notification():
    """
    Отправляет уведомление о запуске бота
    """
    message = "🚀 <b>YouTube Parser Bot запущен!</b>\n\nБот будет отправлять ежедневную статистику в 09:00 утра."
    send_telegram_message(message)

def main():
    """
    Основная функция для обработки списка ссылок из файла
    """
    print("🎥 YouTube Channel Parser - Selenium Version + Telegram Bot")
    print("=" * 60)
    
    # Запускаем планировщик для ежедневных отчетов
    start_scheduler()
    
    # Отправляем уведомление о запуске
    send_startup_notification()
    
    # Установка драйвера
    print("🚀 Запускаем браузер...")
    driver = setup_driver()
    
    try:
        # Запрос имени файла
        input_file = "D:\\Projects\\BAS\\ютуб\\софты\\YMUN\\ссылки на каналы для прогрева.txt"
        if not input_file:
            input_file = "links.txt"
        
        # Чтение ссылок из файла
        links = read_links_from_file(input_file)
        
        if not links:
            print("❌ Не найдено ссылок для обработки!")
            return
        
        print(f"📁 Найдено {len(links)} ссылок в файле {input_file}")
        print("Начинаем парсинг...\n")
        
        results = []
        successful = 0
        failed = 0
        
        for i, link in enumerate(links, 1):
            print(f"🔍 Обрабатывается {i}/{len(links)}: {link}")
            
            about_url = get_channel_about_page(link)
            print(f"   📄 Страница About: {about_url}")
            
            data = parse_channel_data_selenium(driver, about_url)
            results.append(data)
            
            # Вывод результата
            if 'error' in data:
                print(f"   ❌ Ошибка: {data['error']}")
                failed += 1
            else:
                print(f"   ✅ Успешно: {data.get('channel_name', 'Неизвестно')}")
                print(f"   👀 Просмотры: {data.get('total_views', '0')}")
                print(f"   👥 Подписчики: {data.get('subscribers', 'Неизвестно')}")
                print(f"   🎥 Видео: {data.get('videos_count', '0')}")
                if data.get('join_date'):
                    print(f"   📅 Регистрация: {data['join_date']}")
                successful += 1
            
            print("   " + "-" * 40)
            
            # Задержка между запросами для избежания блокировки
            time.sleep(3)
        
        # Обновляем ежедневную статистику
        update_daily_stats(results)
        
        # Подсчет общей статистики
        print("\n" + "=" * 60)
        print("📊 ПОДСЧЕТ ОБЩЕЙ СТАТИСТИКИ")
        print("=" * 60)
        
        total_stats = calculate_total_statistics(results)
        
        # Вывод красивой статистики
        print(f"\n🎯 ОБЩАЯ СТАТИСТИКА ПО ВСЕМ КАНАЛАМ:")
        print(f"   📈 Количество каналов: {total_stats['total_channels']}")
        print(f"   🎥 Общее количество видео: {total_stats['total_videos']:,} ({format_large_number(total_stats['total_videos'])})")
        print(f"   👀 Общее количество просмотров: {total_stats['total_views']:,} ({format_large_number(total_stats['total_views'])})")
        print(f"   👥 Общее количество подписчиков: {total_stats['total_subscribers']:,} ({format_large_number(total_stats['total_subscribers'])})")
        
        print(f"\n📊 СРЕДНИЕ ПОКАЗАТЕЛИ НА КАНАЛ:")
        if total_stats['total_channels'] > 0:
            avg_videos = total_stats['total_videos'] // total_stats['total_channels']
            avg_views = total_stats['total_views'] // total_stats['total_channels']
            avg_subs = total_stats['total_subscribers'] // total_stats['total_channels']
            
            print(f"   🎥 Среднее видео на канал: {avg_videos:,} ({format_large_number(avg_videos)})")
            print(f"   👀 Средние просмотры на канал: {avg_views:,} ({format_large_number(avg_views)})")
            print(f"   👥 Средние подписчики на канал: {avg_subs:,} ({format_large_number(avg_subs)})")
        
        # Статистика по успешным/неудачным запросам
        print(f"\n📈 СТАТИСТИКА ОБРАБОТКИ:")
        print(f"   ✅ Успешно обработано: {successful}")
        print(f"   ❌ Ошибок: {failed}")
        print(f"   📊 Всего ссылок: {len(links)}")
        
        # Отправляем немедленный отчет о текущем запуске
        immediate_report = format_telegram_stats(daily_stats)
        send_telegram_message("📋 <b>ОТЧЕТ О ТЕКУЩЕМ ЗАПУСКЕ</b>\n\n" + immediate_report)
        
        # Сохранение результатов
        if results:
            output_file = f"youtube_channels_selenium_{int(time.time())}.txt"
            save_results_to_file(results, output_file, total_stats)
            
            # Показ краткого отчета
            print(f"\n📋 КРАТКИЙ ОТЧЕТ ПО КАНАЛАМ:")
            for result in results:
                if 'error' not in result:
                    views_num = parse_number(result.get('total_views', '0'))
                    print(f"   📺 {result.get('channel_name', 'Неизвестно')}: {format_large_number(views_num)} просмотров")
    
    finally:
        # Всегда закрываем драйвер
        print("\n🛑 Закрываем браузер...")
        driver.quit()

if __name__ == "__main__":
    main()