"""
Модуль для работы с историей статистики
"""
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

class StatsHistory:
    def __init__(self, db):
        self.db = db
    
    def save_stats(self, results):
        """Сохранение результатов парсинга"""
        for result in results:
            if 'error' not in result:
                self.db.save_channel_stats(result)
    
    def get_channel_growth(self, channel_url, days=30):
        """Получение роста канала за период"""
        history = self.db.get_channel_history(channel_url, days)
        
        if len(history) < 2:
            return None
        
        # Сортируем по дате
        history = sorted(history, key=lambda x: x[6])  # parse_date в индексе 6
        
        first = history[0]
        last = history[-1]
        
        growth = {
            'subscribers_growth': last[3] - first[3] if last[3] and first[3] else 0,
            'views_growth': last[4] - first[4] if last[4] and first[4] else 0,
            'videos_growth': last[5] - first[5] if last[5] and first[5] else 0,
            'period_days': days
        }
        
        return growth
    
    def get_all_channels_summary(self, days=30):
        """Получение сводки по всем каналам"""
        history = self.db.get_all_channels_history(days)
        
        channels_data = defaultdict(lambda: {
            'name': '',
            'url': '',
            'stats': []
        })
        
        for record in history:
            url = record[1]
            if url not in channels_data:
                channels_data[url]['name'] = record[2]
                channels_data[url]['url'] = url
            
            channels_data[url]['stats'].append({
                'date': record[6],
                'subscribers': record[3],
                'views': record[4],
                'videos': record[5]
            })
        
        # Вычисляем средний рост для каждого канала
        summary = []
        for url, data in channels_data.items():
            if len(data['stats']) >= 2:
                stats_sorted = sorted(data['stats'], key=lambda x: x['date'])
                first = stats_sorted[0]
                last = stats_sorted[-1]
                
                summary.append({
                    'name': data['name'],
                    'url': url,
                    'subscribers_growth': (last['subscribers'] or 0) - (first['subscribers'] or 0),
                    'views_growth': (last['views'] or 0) - (first['views'] or 0),
                    'videos_growth': (last['videos'] or 0) - (first['videos'] or 0)
                })
        
        return summary

