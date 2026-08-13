"""
Модуль для управления аккаунтами и анализа материалов
"""
import os
from pathlib import Path
from datetime import datetime

class AccountManager:
    def __init__(self):
        pass
    
    def format_size(self, size_bytes):
        """Форматирует размер в читаемый вид"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} ПБ"
    
    def get_folder_size(self, folder_path):
        """Получает размер папки в байтах"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
        except Exception:
            pass
        return total_size
    
    def count_materials(self, folder_path):
        """Подсчитывает количество материалов в папке"""
        count = 0
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm']
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac']
        
        all_extensions = video_extensions + image_extensions + audio_extensions
        
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in all_extensions):
                        count += 1
        except Exception:
            pass
        
        return count
    
    def calculate_quality_score(self, account_data):
        """Вычисляет оценку качества аккаунта"""
        score = 0
        
        # Базовые критерии
        materials_count = account_data.get('materials_count', 0)
        size_bytes = account_data.get('size_bytes', 0)
        
        # Оценка по количеству материалов
        if materials_count > 100:
            score += 3
        elif materials_count > 50:
            score += 2
        elif materials_count > 20:
            score += 1
        
        # Оценка по размеру (наличие контента)
        if size_bytes > 1_000_000_000:  # > 1 ГБ
            score += 3
        elif size_bytes > 500_000_000:  # > 500 МБ
            score += 2
        elif size_bytes > 100_000_000:  # > 100 МБ
            score += 1
        
        # Определение уровня качества
        if score >= 5:
            return "⭐⭐⭐ Отлично"
        elif score >= 3:
            return "⭐⭐ Хорошо"
        elif score >= 1:
            return "⭐ Удовлетворительно"
        else:
            return "❌ Плохо"
    
    def scan_accounts(self, accounts_folder):
        """Сканирует папку с аккаунтами и собирает информацию"""
        accounts_data = []
        
        if not os.path.exists(accounts_folder):
            return accounts_data
        
        try:
            for item in os.listdir(accounts_folder):
                item_path = os.path.join(accounts_folder, item)
                
                # Проверяем, что это папка
                if os.path.isdir(item_path):
                    # Подсчитываем материалы
                    materials_count = self.count_materials(item_path)
                    
                    # Получаем размер
                    size_bytes = self.get_folder_size(item_path)
                    size_formatted = self.format_size(size_bytes)
                    
                    # Получаем дату изменения
                    try:
                        modified_time = os.path.getmtime(item_path)
                        modified_date = datetime.fromtimestamp(modified_time).strftime("%d.%m.%Y %H:%M")
                    except:
                        modified_date = "Неизвестно"
                    
                    account_data = {
                        'name': item,
                        'folder': accounts_folder,  # Добавляем информацию о папке
                        'materials_count': materials_count,
                        'size': size_formatted,
                        'size_bytes': size_bytes,
                        'modified_date': modified_date,
                        'quality_score': ''
                    }
                    
                    # Вычисляем оценку качества
                    account_data['quality_score'] = self.calculate_quality_score(account_data)
                    
                    accounts_data.append(account_data)
        except Exception as e:
            print(f"Ошибка при сканировании аккаунтов: {e}")
        
        return accounts_data
    
    def scan_multiple_folders(self, accounts_folders):
        """Сканирует несколько папок с аккаунтами и собирает информацию"""
        all_accounts_data = []
        
        if isinstance(accounts_folders, str):
            accounts_folders = [accounts_folders]
        
        for folder in accounts_folders:
            if folder and os.path.exists(folder):
                folder_accounts = self.scan_accounts(folder)
                all_accounts_data.extend(folder_accounts)
        
        # Сортируем по количеству материалов (по убыванию)
        all_accounts_data.sort(key=lambda x: x['materials_count'], reverse=True)
        
        return all_accounts_data

