"""
Модуль для работы с Telegram ботом
"""
import json
import os
import requests
import threading
import time
from datetime import datetime

class TelegramBotManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.bot_token = None
        self.chat_id = None
        self.running = False
        self.thread = None
        self.status_callback = None
    
    def load_config(self):
        """Загрузка конфигурации"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def send_message(self, message, parse_mode='HTML', token=None, chat_id=None):
        """Отправка сообщения в Telegram"""
        if not token or not chat_id:
            config = self.load_config()
            token = token or config.get('telegram_bot_token', '')
            chat_id = chat_id or config.get('telegram_chat_id', '')
        
        if not token or not chat_id:
            raise Exception("Bot Token или Chat ID не указаны в конфигурации")
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode
        }
        
        try:
            response = requests.post(url, data=payload, timeout=10)
            if response.status_code == 200:
                return True
            raise Exception(f"Ошибка отправки: {response.status_code} - {response.text}")
        except Exception as e:
            if isinstance(e, Exception) and 'Ошибка отправки' in str(e):
                raise
            raise Exception(f"Ошибка при отправке сообщения: {e}") from e
    
    def start(self, status_callback=None):
        """Запуск бота"""
        self.status_callback = status_callback
        config = self.load_config()
        self.bot_token = config.get('telegram_bot_token', '')
        self.chat_id = config.get('telegram_chat_id', '')
        
        if not self.bot_token or not self.chat_id:
            raise Exception("Bot Token или Chat ID не указаны")
        
        # Проверка подключения
        if self.status_callback:
            self.status_callback("Проверка подключения к Telegram API...")
        
        try:
            test_message = "🚀 <b>YouTube Analytics Bot запущен!</b>\n\nБот готов к работе."
            self.send_message(test_message)
            
            if self.status_callback:
                self.status_callback("✅ Бот успешно запущен и подключен к Telegram")
                self.status_callback(f"📱 Chat ID: {self.chat_id}")
            
            self.running = True
            
            # Запуск в отдельном потоке для мониторинга
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"❌ Ошибка при запуске бота: {e}")
            raise
    
    def _monitor_loop(self):
        """Цикл мониторинга бота"""
        while self.running:
            try:
                # Проверка статуса бота каждые 60 секунд
                time.sleep(60)
                if self.running and self.status_callback:
                    self.status_callback(f"💓 Бот работает... {datetime.now().strftime('%H:%M:%S')}")
            except:
                break
    
    def stop(self):
        """Остановка бота"""
        self.running = False
        if self.status_callback:
            self.status_callback("⏹️ Бот остановлен")
    
    def send_daily_stats(self, stats_data):
        """Отправка ежедневной статистики"""
        if not self.running:
            return False
        
        try:
            message = self._format_stats_message(stats_data)
            return self.send_message(message)
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"❌ Ошибка при отправке статистики: {e}")
            return False
    
    def _format_stats_message(self, stats):
        """Форматирование сообщения со статистикой"""
        message = "📊 <b>ЕЖЕДНЕВНАЯ СТАТИСТИКА YouTube Парсера</b>\n\n"
        
        if stats.get('last_run'):
            message += f"📅 <b>Последний запуск:</b> {stats['last_run']}\n"
        
        message += f"🔍 <b>Обработано каналов:</b> {stats.get('total_channels_processed', 0)}\n"
        message += f"✅ <b>Успешных парсингов:</b> {stats.get('successful_parses', 0)}\n"
        message += f"❌ <b>Ошибок парсинга:</b> {stats.get('failed_parses', 0)}\n"
        
        if stats.get('successful_parses', 0) > 0:
            success_rate = (stats.get('successful_parses', 0) / max(1, stats.get('total_channels_processed', 1))) * 100
            message += f"📈 <b>Успешность:</b> {success_rate:.1f}%\n\n"
        
        message += f"👀 <b>Всего просмотров:</b> {self._format_number(stats.get('total_views_today', 0))}\n"
        message += f"👥 <b>Всего подписчиков:</b> {self._format_number(stats.get('total_subscribers_today', 0))}\n"
        message += f"🎥 <b>Всего видео:</b> {self._format_number(stats.get('total_videos_today', 0))}\n"
        
        return message
    
    def _format_number(self, number):
        """Форматирование больших чисел"""
        if number >= 1_000_000_000:
            return f"{number / 1_000_000_000:.1f} млрд"
        elif number >= 1_000_000:
            return f"{number / 1_000_000:.1f} млн"
        elif number >= 1_000:
            return f"{number / 1_000:.1f} тыс"
        else:
            return f"{number:,}".replace(',', ' ')

