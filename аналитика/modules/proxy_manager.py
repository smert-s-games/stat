"""
Модуль для управления информацией о прокси и сервере
"""
import json
import os
from datetime import datetime

class ProxyManager:
    def __init__(self, config_file):
        self.config_file = config_file
    
    def load_config(self):
        """Загрузка конфигурации"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self, config):
        """Сохранение конфигурации"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка при сохранении конфигурации: {e}")
            return False
    
    def get_proxy_info(self):
        """Получение информации о прокси"""
        config = self.load_config()
        return config.get('proxy', {})
    
    def get_server_info(self):
        """Получение информации о сервере"""
        config = self.load_config()
        return config.get('server', {})
    
    def update_proxy_info(self, purchase_date, expiry_date):
        """Обновление информации о прокси"""
        config = self.load_config()
        if 'proxy' not in config:
            config['proxy'] = {}
        config['proxy']['purchase_date'] = purchase_date
        config['proxy']['expiry_date'] = expiry_date
        return self.save_config(config)
    
    def update_server_info(self, purchase_date, expiry_date):
        """Обновление информации о сервере"""
        config = self.load_config()
        if 'server' not in config:
            config['server'] = {}
        config['server']['purchase_date'] = purchase_date
        config['server']['expiry_date'] = expiry_date
        return self.save_config(config)
    
    def get_days_remaining(self, expiry_date_str):
        """Получение количества оставшихся дней"""
        if not expiry_date_str or expiry_date_str == 'Не указана':
            return None
        
        try:
            exp_date = datetime.strptime(expiry_date_str, "%d.%m.%Y")
            days_left = (exp_date - datetime.now()).days
            return days_left
        except:
            return None

