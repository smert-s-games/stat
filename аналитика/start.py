import os
import subprocess
from itertools import permutations
from pathlib import Path

def validate_video_file(video_path):
    """Проверяет, что видео файл валиден и может быть обработан"""
    try:
        if not os.path.exists(video_path):
            return False
        
        if os.path.getsize(video_path) == 0:
            print(f"⚠️ Файл пустой: {os.path.basename(video_path)}")
            return False
        
        # Проверяем видео через ffprobe
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name,width,height,duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            return True
        else:
            print(f"⚠️ Не удалось прочитать видео: {os.path.basename(video_path)}")
            return False
            
    except Exception as e:
        print(f"⚠️ Ошибка проверки {os.path.basename(video_path)}: {str(e)}")
        return False

def get_all_video_permutations(input_folder, group_size=3):
    """
    Получает все возможные перестановки видео по group_size штук из всех файлов в папке
    """
    # Получаем список всех видео файлов
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm']
    video_files = []
    
    for file in os.listdir(input_folder):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            video_path = os.path.join(input_folder, file)
            # Проверяем валидность видео
            if validate_video_file(video_path):
                video_files.append(file)
            else:
                print(f"⏭️ Пропущен невалидный файл: {file}")
    
    if not video_files:
        print("❌ Не найдено валидных видео файлов")
        return []
    
    if len(video_files) < group_size:
        print(f"⚠️ Недостаточно видео для создания перестановок по {group_size} файлов")
        return []
    
    print(f"✓ Найдено валидных видео файлов: {len(video_files)}")
    print("Список видео:", video_files)
    
    # Генерируем ВСЕ возможные перестановки
    all_permutations = list(permutations(video_files, group_size))
    
    # Убираем дубликаты
    unique_permutations = []
    seen = set()
    for perm in all_permutations:
        perm_tuple = tuple(perm)
        if perm_tuple not in seen:
            seen.add(perm_tuple)
            unique_permutations.append(perm)
    
    print(f"✓ Создано уникальных перестановок: {len(unique_permutations)}")
    if len(unique_permutations) != len(all_permutations):
        print(f"⚠️ Удалено дубликатов: {len(all_permutations) - len(unique_permutations)}")
    
    print("Первые 10 перестановок:")
    for i, perm in enumerate(unique_permutations[:10]):
        print(f"  {i+1}. {perm}")
    
    return unique_permutations

def combine_videos_ffmpeg(video_files, input_folder, output_path):
    """
    Склеивает видео используя ffmpeg с перекодированием для совместимости
    """
    # Создаем временный файл со списком видео для ffmpeg
    list_file = "temp_file_list.txt"
    
    try:
        # Проверяем существование всех видео файлов
        for video in video_files:
            video_path = os.path.join(input_folder, video)
            if not os.path.exists(video_path):
                print(f"⚠️ Видео файл не найден: {video_path}")
                return False
        
        with open(list_file, 'w', encoding='utf-8') as f:
            for video in video_files:
                video_path = os.path.join(input_folder, video)
                # Экранируем специальные символы для Windows
                video_path = video_path.replace('\\', '/').replace("'", "'\\''")
                f.write(f"file '{video_path}'\n")
        
        # Проверяем валидность всех видео перед склейкой
        valid_videos = []
        for video in video_files:
            video_path = os.path.join(input_folder, video)
            if validate_video_file(video_path):
                valid_videos.append(video)
            else:
                print(f"⚠️ Пропущен невалидный файл при склейке: {video}")
        
        if len(valid_videos) != len(video_files):
            print(f"❌ Не все видео файлы валидны ({len(valid_videos)}/{len(video_files)})")
            return False
        
        if not valid_videos:
            print(f"❌ Нет валидных видео для склейки")
            return False
        
        # Используем перекодирование с нормализацией всех параметров
        # Это гарантирует совместимость даже при разных разрешениях и кодеках
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            # Перекодируем видео для совместимости
            '-c:v', 'libx264',           # Видео кодек H.264
            '-preset', 'medium',         # Баланс скорости/качества
            '-crf', '23',                # Качество (18-28, меньше = лучше качество)
            '-pix_fmt', 'yuv420p',      # Формат пикселей для совместимости
            '-r', '30',                  # Целевая частота кадров (нормализуем все к 30 fps)
            '-g', '30',                  # GOP size для лучшей совместимости
            '-keyint_min', '30',         # Минимальный интервал ключевых кадров
            '-sc_threshold', '0',        # Отключаем сценарные изменения для стабильности
            # Обрабатываем аудио
            '-c:a', 'aac',               # Аудио кодек AAC
            '-b:a', '192k',              # Битрейт аудио
            '-ar', '44100',              # Частота дискретизации
            '-ac', '2',                  # Стерео звук
            # Другие параметры для стабильности
            '-movflags', '+faststart',   # Оптимизация для веб-воспроизведения
            '-avoid_negative_ts', 'make_zero',  # Избегаем проблем с временными метками
            '-fflags', '+genpts',        # Генерируем PTS для исправления проблем с временными метками
            '-vsync', 'cfr',             # Постоянная частота кадров
            output_path,
            '-y'                         # Перезаписывать существующие файлы
        ]
        
        # Запускаем ffmpeg с таймаутом (30 минут на видео)
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True,
            timeout=1800  # 30 минут таймаут
        )
        
        # Проверяем, что выходной файл создан и не пустой
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            # Дополнительная проверка: пытаемся прочитать метаданные выходного файла
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                output_path
            ]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            if probe_result.returncode == 0 and probe_result.stdout.strip():
                return True
            else:
                print(f"⚠️ Выходной файл создан, но не содержит валидного видео")
                return False
        else:
            print(f"⚠️ Выходной файл не создан или пустой: {output_path}")
            return False
        
    except subprocess.TimeoutExpired:
        print(f"⏱️ Таймаут при создании видео (превышено 30 минут)")
        return False
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        print(f"Ошибка ffmpeg: {error_msg[:500]}")  # Ограничиваем длину сообщения
        return False
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return False
    finally:
        # Удаляем временный файл
        if os.path.exists(list_file):
            try:
                os.remove(list_file)
            except:
                pass

def create_permutation_name(video_files, permutation_index):
    """
    Создает уникальное имя файла для перестановки
    """
    name_parts = []
    for i, video in enumerate(video_files):
        base_name = os.path.splitext(video)[0]
        # Используем больше символов и добавляем индекс позиции для уникальности
        short_name = base_name[:12].replace(' ', '_')
        name_parts.append(f"{i+1}_{short_name}")
    
    combined_name = "_".join(name_parts)
    # Добавляем хеш всей перестановки для уникальности
    perm_hash = abs(hash('_'.join(video_files))) % 100000
    return f"perm_{permutation_index:04d}_{perm_hash:05d}_{combined_name}.mp4"

def main():
    # Настройки путей
    input_folder = "video_from_pinterest"  # Папка с исходными видео
    output_folder = "ready_videos"  # Папка для результата
    videos_per_group = 3
    
    # Проверяем существование входной папки
    if not os.path.exists(input_folder):
        print(f"Ошибка: Папка '{input_folder}' не существует!")
        return
    
    # Создаем выходную папку если ее нет
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # Получаем ВСЕ возможные перестановки из всех видео в папке
    all_permutations = get_all_video_permutations(input_folder, videos_per_group)
    
    if not all_permutations:
        return
    
    print(f"\nНачинаю создание всех {len(all_permutations)} перестановок...")
    print("Это может занять некоторое время...")
    
    successful = 0
    failed = 0
    
    # Обрабатываем каждую перестановку
    for i, permutation in enumerate(all_permutations, 1):
        output_filename = create_permutation_name(permutation, i)
        output_path = os.path.join(output_folder, output_filename)
        
        print(f"[{i}/{len(all_permutations)}] Создаю: {permutation} -> {output_filename}")
        
        if combine_videos_ffmpeg(permutation, input_folder, output_path):
            print(f"   ✓ Успешно")
            successful += 1
        else:
            print(f"   ✗ Ошибка")
            failed += 1
        
        # Прогресс каждые 10 перестановок
        if i % 10 == 0:
            print(f"Прогресс: {i}/{len(all_permutations)} (успешно: {successful}, ошибок: {failed})")
    
    print(f"\n=== ОБРАБОТКА ЗАВЕРШЕНА ===")
    print(f"Успешно создано: {successful} перестановок")
    print(f"С ошибками: {failed}")
    print(f"Всего обработано: {len(all_permutations)} перестановок")
    print(f"Результаты сохранены в папке: {output_folder}")

if __name__ == "__main__":
    main()