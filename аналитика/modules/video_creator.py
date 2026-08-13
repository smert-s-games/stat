"""
Модуль для создания видео из перестановок
"""
import os
import subprocess
import random
import tempfile
import re
from itertools import permutations
from pathlib import Path

class VideoCreator:
    MAX_PERMUTATIONS = 500

    def __init__(self):
        self.stop_flag = False
    
    def stop(self):
        """Установка флага остановки"""
        self.stop_flag = True
    
    def validate_video_file(self, video_path, callback=None):
        """Проверяет, что видео файл валиден и может быть обработан"""
        try:
            # Проверяем существование файла
            if not os.path.exists(video_path):
                return False
            
            # Проверяем размер файла (не должен быть пустым)
            if os.path.getsize(video_path) == 0:
                if callback:
                    callback(f"⚠️ Файл пустой: {os.path.basename(video_path)}")
                return False
            
            # Проверяем видео через ffprobe (быстрая проверка метаданных)
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name,width,height,duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            
            result = subprocess.run(
                probe_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Если ffprobe успешно выполнился и вернул данные о видеопотоке
            if result.returncode == 0 and result.stdout.strip():
                return True
            else:
                if callback:
                    callback(f"⚠️ Не удалось прочитать видео: {os.path.basename(video_path)}")
                return False
                
        except subprocess.TimeoutExpired:
            if callback:
                callback(f"⚠️ Таймаут при проверке: {os.path.basename(video_path)}")
            return False
        except Exception as e:
            if callback:
                callback(f"⚠️ Ошибка проверки {os.path.basename(video_path)}: {str(e)}")
            return False
    
    def get_all_video_permutations(self, input_folder, group_size=3, callback=None):
        """Получает все возможные перестановки видео (упрощенная версия)"""
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm']
        video_files = []
        
        try:
            for file in os.listdir(input_folder):
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    video_path = os.path.join(input_folder, file)
                    # Простая проверка - файл существует и не пустой
                    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                        video_files.append(file)
        except Exception as e:
            if callback:
                callback(f"Ошибка при чтении папки: {e}")
            return []
        
        if not video_files:
            if callback:
                callback("❌ Не найдено видео файлов")
            return []

        if len(video_files) < group_size:
            if callback:
                callback(f"⚠️ Недостаточно видео для создания перестановок по {group_size} файлов")
            return []

        if callback:
            callback(f"✓ Найдено видео файлов: {len(video_files)}")
        
        # Генерируем перестановки
        all_permutations = list(permutations(video_files, group_size))
        
        # Убираем дубликаты
        unique_permutations = []
        seen = set()
        for perm in all_permutations:
            perm_tuple = tuple(perm)
            if perm_tuple not in seen:
                seen.add(perm_tuple)
                unique_permutations.append(perm)

        if len(unique_permutations) > self.MAX_PERMUTATIONS:
            if callback:
                callback(
                    f"⚠️ Слишком много перестановок ({len(unique_permutations)}). "
                    f"Ограничено до {self.MAX_PERMUTATIONS}."
                )
            unique_permutations = unique_permutations[:self.MAX_PERMUTATIONS]
        
        if callback:
            callback(f"✓ Создано уникальных перестановок: {len(unique_permutations)}")
            if len(unique_permutations) != len(all_permutations):
                callback(f"⚠️ Удалено дубликатов: {len(all_permutations) - len(unique_permutations)}")
        
        return unique_permutations
    
    def combine_videos_ffmpeg(self, video_files, input_folder, output_path, callback=None):
        """Склеивает видео используя video_processor.py"""
        try:
            # Импортируем функцию из video_processor
            import sys
            import importlib.util
            
            # Получаем путь к video_processor.py
            video_processor_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'video_processor.py')
            
            if not os.path.exists(video_processor_path):
                if callback:
                    callback(f"❌ Файл video_processor.py не найден: {video_processor_path}")
                return False
            
            # Загружаем модуль динамически
            spec = importlib.util.spec_from_file_location("video_processor", video_processor_path)
            video_processor = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(video_processor)
            
            # Проверяем существование всех видео файлов и собираем полные пути
            video_paths = []
            
            for video in video_files:
                video_path = os.path.join(input_folder, video)
                if not os.path.exists(video_path):
                    if callback:
                        callback(f"⚠️ Видео файл не найден: {video}")
                    continue
                
                # Простая проверка - файл существует и не пустой
                if os.path.getsize(video_path) > 0:
                    video_paths.append(os.path.abspath(video_path))
                else:
                    if callback:
                        callback(f"⚠️ Файл пустой: {video}")
            
            if len(video_paths) != len(video_files):
                if callback:
                    callback(f"❌ Не все видео файлы доступны ({len(video_paths)}/{len(video_files)})")
                return False
            
            if not video_paths:
                if callback:
                    callback(f"❌ Нет валидных видео для склейки")
                return False
            
            # Нормализуем путь к выходному файлу
            output_path_normalized = os.path.normpath(output_path)
            
            # Вызываем функцию из video_processor.py
            if callback:
                callback(f"✓ Использую video_processor.py для склейки {len(video_paths)} видео...")
            
            result = video_processor.combine_videos_vertical(video_paths, output_path_normalized, callback)
            
            return result
                
        except ImportError as e:
            if callback:
                callback(f"❌ Ошибка импорта video_processor: {str(e)}")
            return False
        except Exception as e:
            if callback:
                callback(f"❌ Неожиданная ошибка: {str(e)}")
                import traceback
                callback(f"❌ Трассировка:\n{traceback.format_exc()[:500]}")
            return False
    
    def combine_videos_frmpeg(self, *args, **kwargs):
        """Алиас для обратной совместимости (если где-то используется с опечаткой)"""
        return self.combine_videos_ffmpeg(*args, **kwargs)
    
    def create_permutation_name(self, video_files, permutation_index):
        """Создает уникальное имя файла для перестановки"""
        name_parts = []
        for i, video in enumerate(video_files):
            base_name = os.path.splitext(video)[0]
            # Используем больше символов и добавляем индекс позиции для уникальности
            short_name = base_name[:12].replace(' ', '_')
            # Добавляем хеш для гарантии уникальности
            name_hash = hash('_'.join(video_files)) % 10000
            name_parts.append(f"{i+1}_{short_name}")
        
        combined_name = "_".join(name_parts)
        # Добавляем хеш всей перестановки для уникальности
        perm_hash = abs(hash('_'.join(video_files))) % 100000
        return f"perm_{permutation_index:04d}_{perm_hash:05d}_{combined_name}.mp4"
    
    def create_videos(self, input_folder, output_folder, videos_per_group, log_callback=None, progress_callback=None):
        """Создает все перестановки видео"""
        self.stop_flag = False
        
        if not os.path.exists(input_folder):
            if log_callback:
                log_callback(f"Ошибка: Папка '{input_folder}' не существует!")
            return
        
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        all_permutations = self.get_all_video_permutations(input_folder, videos_per_group, log_callback)
        
        if not all_permutations:
            return
        
        if log_callback:
            log_callback(f"\nНачинаю создание всех {len(all_permutations)} перестановок...")
        
        successful = 0
        failed = 0
        
        for i, permutation in enumerate(all_permutations, 1):
            if self.stop_flag:
                if log_callback:
                    log_callback("⏹️ Остановка создания видео...")
                break
            
            output_filename = self.create_permutation_name(permutation, i)
            output_path = os.path.join(output_folder, output_filename)
            
            if log_callback:
                log_callback(f"[{i}/{len(all_permutations)}] Создаю: {', '.join(permutation)} -> {output_filename}")
            
            if progress_callback:
                progress_callback(i, len(all_permutations))
            
            # ИСПРАВЛЕН ВЫЗОВ - правильное имя метода
            if self.combine_videos_ffmpeg(permutation, input_folder, output_path, log_callback):
                if log_callback:
                    log_callback(f"   ✓ Успешно")
                successful += 1
            else:
                if log_callback:
                    log_callback(f"   ✗ Ошибка")
                failed += 1
            
            if i % 10 == 0 and log_callback:
                log_callback(f"Прогресс: {i}/{len(all_permutations)} (успешно: {successful}, ошибок: {failed})")
        
        if log_callback:
            log_callback(f"\n=== ОБРАБОТКА ЗАВЕРШЕНА ===")
            log_callback(f"Успешно создано: {successful} перестановок")
            log_callback(f"С ошибками: {failed}")
            log_callback(f"Результаты сохранены в папке: {output_folder}")