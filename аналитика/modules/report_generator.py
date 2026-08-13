"""
Модуль для генерации отчетов
"""
from datetime import datetime
import os

class ReportGenerator:
    def __init__(self):
        pass
    
    def generate_stats_report(self, stats_data, accounts_data=None, output_file=None):
        """Генерация текстового отчета"""
        if output_file is None:
            output_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("ОТЧЕТ ПО АНАЛИТИКЕ YOUTUBE КАНАЛОВ\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n")
                
                # Статистика по каналам
                if stats_data:
                    f.write("СТАТИСТИКА ПО КАНАЛАМ\n")
                    f.write("-" * 80 + "\n\n")
                    
                    total_channels = len([r for r in stats_data if 'error' not in r])
                    total_views = sum(self._parse_number(r.get('total_views', '0')) for r in stats_data if 'error' not in r)
                    total_subs = sum(self._parse_number(r.get('subscribers', '0')) for r in stats_data if 'error' not in r)
                    total_videos = sum(self._parse_number(r.get('videos_count', '0')) for r in stats_data if 'error' not in r)
                    
                    f.write(f"Всего каналов: {total_channels}\n")
                    f.write(f"Всего просмотров: {self._format_number(total_views)}\n")
                    f.write(f"Всего подписчиков: {self._format_number(total_subs)}\n")
                    f.write(f"Всего видео: {self._format_number(total_videos)}\n\n")
                    
                    f.write("Детальная информация по каналам:\n")
                    for i, result in enumerate(stats_data, 1):
                        if 'error' not in result:
                            f.write(f"\n{i}. {result.get('channel_name', 'Неизвестно')}\n")
                            f.write(f"   URL: {result.get('url', '')}\n")
                            f.write(f"   Подписчики: {result.get('subscribers', '0')}\n")
                            f.write(f"   Просмотры: {result.get('total_views', '0')}\n")
                            f.write(f"   Видео: {result.get('videos_count', '0')}\n")
                
                # Статистика по аккаунтам
                if accounts_data:
                    f.write("\n\n" + "=" * 80 + "\n")
                    f.write("СТАТИСТИКА ПО АККАУНТАМ\n")
                    f.write("-" * 80 + "\n\n")
                    
                    total_accounts = len(accounts_data)
                    total_materials = sum(a.get('materials_count', 0) for a in accounts_data)
                    total_size = sum(a.get('size_bytes', 0) for a in accounts_data)
                    
                    f.write(f"Всего аккаунтов: {total_accounts}\n")
                    f.write(f"Всего материалов: {total_materials}\n")
                    f.write(f"Общий размер: {self._format_size(total_size)}\n\n")
                    
                    f.write("Детальная информация по аккаунтам:\n")
                    for i, account in enumerate(accounts_data, 1):
                        f.write(f"\n{i}. {account.get('name', 'Неизвестно')}\n")
                        f.write(f"   Папка: {account.get('folder', '')}\n")
                        f.write(f"   Материалов: {account.get('materials_count', 0)}\n")
                        f.write(f"   Размер: {account.get('size', '0')}\n")
                        f.write(f"   Качество: {account.get('quality_score', '')}\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("Конец отчета\n")
                f.write("=" * 80 + "\n")
            
            return output_file
        except Exception as e:
            raise Exception(f"Ошибка при генерации отчета: {e}")
    
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
    
    def _format_number(self, number):
        """Форматирование числа"""
        if number >= 1_000_000_000:
            return f"{number / 1_000_000_000:.1f} млрд"
        elif number >= 1_000_000:
            return f"{number / 1_000_000:.1f} млн"
        elif number >= 1_000:
            return f"{number / 1_000:.1f} тыс"
        else:
            return f"{number:,}".replace(',', ' ')
    
    def _format_size(self, size_bytes):
        """Форматирование размера"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} ПБ"

