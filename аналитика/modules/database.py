"""
Модуль для работы с базой данных SQLite
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

class Database:
    def __init__(self, db_path="analytics.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Получение соединения с базой данных"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица истории статистики каналов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_stats_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_url TEXT NOT NULL,
                channel_name TEXT,
                subscribers INTEGER,
                views INTEGER,
                videos INTEGER,
                parse_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(channel_url, parse_date)
            )
        ''')
        
        # Таблица истории операций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        ''')
        
        # Таблица настроек прокси/серверов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxy_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                purchase_date TEXT,
                expiry_date TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица тегов аккаунтов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                account_folder TEXT NOT NULL,
                tag TEXT NOT NULL,
                UNIQUE(account_name, account_folder, tag)
            )
        ''')
        
        # Таблица уведомлений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _now_str(self):
        """Единый формат даты для SQLite"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def save_channel_stats(self, channel_data):
        """Сохранение статистики канала"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO channel_stats_history 
                (channel_url, channel_name, subscribers, views, videos, parse_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                channel_data.get('url', ''),
                channel_data.get('channel_name', ''),
                self._parse_number(channel_data.get('subscribers', '0')),
                self._parse_number(channel_data.get('total_views', '0')),
                self._parse_number(channel_data.get('videos_count', '0')),
                self._now_str()
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при сохранении статистики: {e}")
            return False
        finally:
            conn.close()
    
    def get_channel_history(self, channel_url, days=30):
        """Получение истории канала за последние N дней"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM channel_stats_history
            WHERE channel_url = ? 
            AND parse_date >= datetime('now', '-' || ? || ' days')
            ORDER BY parse_date DESC
        ''', (channel_url, days))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_all_channels_history(self, days=30):
        """Получение истории всех каналов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM channel_stats_history
            WHERE parse_date >= datetime('now', '-' || ? || ' days')
            ORDER BY parse_date DESC, channel_name
        ''', (days,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def log_operation(self, operation_type, description, details=None):
        """Логирование операции"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO operations_log (operation_type, description, details)
            VALUES (?, ?, ?)
        ''', (operation_type, description, json.dumps(details) if details else None))
        
        conn.commit()
        conn.close()
    
    def get_operations_log(self, limit=100):
        """Получение лога операций"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM operations_log
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def add_account_tag(self, account_name, account_folder, tag):
        """Добавление тега к аккаунту"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO account_tags (account_name, account_folder, tag)
                VALUES (?, ?, ?)
            ''', (account_name, account_folder, tag))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении тега: {e}")
            return False
        finally:
            conn.close()
    
    def get_account_tags(self, account_name, account_folder):
        """Получение тегов аккаунта"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tag FROM account_tags
            WHERE account_name = ? AND account_folder = ?
        ''', (account_name, account_folder))
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def remove_account_tag(self, account_name, account_folder, tag):
        """Удаление тега у аккаунта"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM account_tags
            WHERE account_name = ? AND account_folder = ? AND tag = ?
        ''', (account_name, account_folder, tag))
        
        conn.commit()
        conn.close()
    
    def has_recent_notification(self, notification_type, message=None, hours=24):
        """Проверка наличия недавнего уведомления того же типа"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if message:
            cursor.execute('''
                SELECT COUNT(*) FROM notifications
                WHERE type = ? AND message = ?
                AND created_at >= datetime('now', '-' || ? || ' hours')
            ''', (notification_type, message, hours))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM notifications
                WHERE type = ?
                AND created_at >= datetime('now', '-' || ? || ' hours')
            ''', (notification_type, hours))

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def add_notification(self, notification_type, message):
        """Добавление уведомления"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notifications (type, message)
            VALUES (?, ?)
        ''', (notification_type, message))
        
        conn.commit()
        conn.close()
    
    def get_unread_notifications(self):
        """Получение непрочитанных уведомлений"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM notifications
            WHERE read = 0
            ORDER BY created_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def mark_notification_read(self, notification_id):
        """Отметить уведомление как прочитанное"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notifications SET read = 1
            WHERE id = ?
        ''', (notification_id,))
        
        conn.commit()
        conn.close()
    
    def _parse_number(self, text):
        """Парсинг числа из текста"""
        import re
        if not text or text == 'Неизвестно' or text == '0':
            return 0
        
        cleaned = re.sub(r'[^\d,.]', '', str(text))
        cleaned = cleaned.replace(',', '.')
        
        try:
            num = float(cleaned)
            return int(num) if num.is_integer() else num
        except:
            return 0

