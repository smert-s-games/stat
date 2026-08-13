"""
Скрипт для обработки видео:
- Берет случайно 3 видео из папки ishod и склеивает их
- Добавляет звук из папки ozv
- Удаляет зеленый фон (хромакей) из видео в папке nalog и накладывает на созданное видео
- Сохраняет результат в папку redi

Использование:
    python video_processor.py --num 5
    
    --num - количество видео для создания (по умолчанию: 1)
    --ishod - папка с исходными видео (по умолчанию: ishod)
    --ozv - папка с аудио файлами (по умолчанию: ozv)
    --nalog - папка с видео хромакея (по умолчанию: nalog)
    --redi - папка для сохранения (по умолчанию: redi)

Пример:
    python video_processor.py --num 3
    python video_processor.py --num 10 --ishod videos --redi output
"""

import os
import random
import argparse
import uuid
from pathlib import Path
from datetime import datetime

# Патч для совместимости с новыми версиями Pillow (10.0+)
# В Pillow 10.0+ ANTIALIAS был удален, используем LANCZOS
# Это нужно сделать ДО импорта moviepy, так как moviepy использует ANTIALIAS
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        # Пытаемся использовать новый API (Pillow 10.0+)
        if hasattr(Image, 'Resampling'):
            Image.ANTIALIAS = Image.Resampling.LANCZOS
        elif hasattr(Image, 'LANCZOS'):
            Image.ANTIALIAS = Image.LANCZOS
        else:
            # Fallback для очень старых версий
            Image.ANTIALIAS = 1
except (ImportError, AttributeError):
    pass

from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, concatenate_audioclips, AudioClip
from moviepy.video.fx.all import lum_contrast, colorx

# cv2 и numpy импортируются только когда нужны (для хромакея)
# Это позволяет использовать combine_videos_vertical без установки OpenCV


def generate_unique_metadata():
    """
    Генерирует уникальные метаданные для видео
    """
    video_id = str(uuid.uuid4())
    title = f"Video_{random.randint(1000, 9999)}_{random.randint(100, 999)}"
    description = f"Generated video {video_id[:8]} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    tags = random.sample(['video', 'content', 'generated', 'unique', 'creative', 'media', 'clip'], 3)
    
    return {
        'title': title,
        'description': description,
        'tags': ','.join(tags),
        'video_id': video_id,
        'creation_time': datetime.now().isoformat(),
        'artist': f"Generator_{random.randint(1, 1000)}",
        'album': f"Collection_{random.randint(1, 100)}"
    }


def apply_random_effects(video_clip):
    """
    Применяет небольшие изменения яркости, контраста и насыщенности к видео для уникальности
    """
    # Всегда применяем небольшие изменения яркости и контраста
    brightness = random.uniform(0.0, 0.0)  # Небольшие изменения яркости
    contrast = random.uniform(0.99, 1.00)   # Небольшие изменения контраста
    video_clip = lum_contrast(video_clip, lum=brightness, contrast=contrast)
    
    # Всегда применяем небольшие изменения насыщенности цвета
    saturation = random.uniform(1.0, 1.0)    # Небольшие изменения насыщенности
    video_clip = colorx(video_clip, saturation)
    
    print(f"Применены эффекты: яркость={brightness:.2f}, контраст={contrast:.2f}, насыщенность={saturation:.2f}")
    
    return video_clip


def create_video_with_chromakey(base_video, chromakey_video_path, position='bottom-right'):
    """
    Накладывает видео с удаленным зеленым фоном на базовое видео
    """
    # Импортируем cv2 и numpy только здесь, где они нужны
    try:
        import cv2
        import numpy as np
    except ImportError:
        raise ImportError("Для использования хромакея требуется установить OpenCV: pip install opencv-python")
    
    from moviepy.video.fx.all import resize
    
    # Загружаем видео с хромакеем и убираем звук
    chromakey_clip_original = VideoFileClip(str(chromakey_video_path))
    chromakey_clip_original = chromakey_clip_original.without_audio()
    chromakey_w, chromakey_h = chromakey_clip_original.size
    
    # Получаем размеры базового видео
    base_w, base_h = base_video.size
    base_duration = base_video.duration
    
    # Масштабируем видео хромакея, если оно слишком большое (максимум 30% от размера базового)
    max_w = int(base_w * 0.3)
    max_h = int(base_h * 0.3)
    scale_factor = min(1.0, max_w / chromakey_w, max_h / chromakey_h)
    
    if scale_factor < 1.0:
        chromakey_w = int(chromakey_w * scale_factor)
        chromakey_h = int(chromakey_h * scale_factor)
        chromakey_clip_original = chromakey_clip_original.resize((chromakey_w, chromakey_h))
    
    # Обрезаем или зацикливаем видео хромакея под длину базового
    chromakey_duration = chromakey_clip_original.duration
    
    if chromakey_duration > base_duration:
        chromakey_clip = chromakey_clip_original.subclip(0, base_duration)
    elif chromakey_duration < base_duration:
        num_loops = int(base_duration / chromakey_duration) + 1
        video_segments = [chromakey_clip_original] * num_loops
        chromakey_clip = concatenate_videoclips(video_segments, method="compose")
        chromakey_clip = chromakey_clip.subclip(0, base_duration)
    else:
        chromakey_clip = chromakey_clip_original
    
    # Определяем позицию для наложения
    if position == 'top-left':
        x_pos, y_pos = 0, 0
    elif position == 'top-right':
        x_pos, y_pos = base_w - chromakey_w, 0
    elif position == 'bottom-left':
        x_pos, y_pos = 0, base_h - chromakey_h
    elif position == 'bottom-right':
        x_pos, y_pos = base_w - chromakey_w, base_h - chromakey_h
    else:
        x_pos, y_pos = base_w - chromakey_w, base_h - chromakey_h
    
    # Функция для обработки кадра и удаления зеленого фона
    def process_chromakey_frame(get_frame, t):
        frame = get_frame(t)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        
        # Создаем маску для зеленого цвета
        green_mask = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        green_mask = cv2.GaussianBlur(green_mask, (5, 5), 0)
        
        # Создаем RGBA кадр
        rgba = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGBA)
        # Устанавливаем альфа-канал: зеленый = прозрачный (0), остальное = видимое (255)
        rgba[:, :, 3] = 255 - green_mask
        
        # Конвертируем обратно в RGB (moviepy не поддерживает RGBA напрямую)
        rgb = cv2.cvtColor(rgba, cv2.COLOR_RGBA2RGB)
        return rgb
    
    # Функция для создания маски из кадра
    def make_mask_frame(get_frame, t):
        frame = get_frame(t)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        
        # Создаем маску для зеленого цвета
        green_mask = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        green_mask = cv2.GaussianBlur(green_mask, (5, 5), 0)
        
        # Инвертируем: зеленый = 0 (прозрачно), остальное = 255 (видимо)
        mask = 255 - green_mask
        mask_normalized = mask.astype(np.float32) / 255.0
        
        # Возвращаем маску в формате (H, W, 3)
        return np.stack([mask_normalized] * 3, axis=2)
    
    # Убеждаемся, что видео хромакея имеет правильную длительность
    if chromakey_clip.duration != base_duration:
        chromakey_clip = chromakey_clip.subclip(0, base_duration)
    
    # Создаем маску из видео хромакея
    mask_clip = chromakey_clip.fl(lambda gf, t: make_mask_frame(gf, t), apply_to=['video'])
    mask_clip = mask_clip.to_mask()
    
    # Убеждаемся, что маска имеет правильную длительность и размер
    if mask_clip.duration != base_duration:
        mask_clip = mask_clip.subclip(0, base_duration)
    if mask_clip.size != chromakey_clip.size:
        mask_clip = mask_clip.resize(chromakey_clip.size)
    
    # Применяем маску к видео хромакея
    # В moviepy: маска 1.0 = видимо, 0.0 = прозрачно
    print(f"Применение маски: размер видео {chromakey_clip.size}, размер маски {mask_clip.size}")
    chromakey_masked = chromakey_clip.set_mask(mask_clip)
    
    # Убеждаемся, что маскированное видео имеет правильную длительность
    if chromakey_masked.duration != base_duration:
        chromakey_masked = chromakey_masked.subclip(0, base_duration)
    
    print(f"Наложение видео хромакея: позиция ({x_pos}, {y_pos}), размер базового {base_video.size}")
    
    # Накладываем видео поверх базового
    # CompositeVideoClip: первый элемент - нижний слой, второй - верхний
    final_video = CompositeVideoClip([
        base_video,
        chromakey_masked.set_position((x_pos, y_pos))
    ], size=base_video.size)
    
    # Сохраняем аудио из базового видео (если есть)
    if base_video.audio is not None:
        final_video = final_video.set_audio(base_video.audio)
    
    final_video = final_video.set_duration(base_duration)
    
    print(f"Финальное видео: размер {final_video.size}, длительность {final_video.duration}")
    
    return final_video


def combine_videos_vertical(video_files, output_path, callback=None):
    """
    Склеивает указанные видео файлы в вертикальном формате (1080x1920)
    
    Args:
        video_files: список путей к видео файлам для склейки
        output_path: путь для сохранения результата
        callback: функция для вывода сообщений о прогрессе
    
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        
        if callback:
            callback(f"Загрузка {len(video_files)} видео...")
        
        # Загружаем все видео
        clips = []
        for i, video_path in enumerate(video_files):
            if not os.path.exists(video_path):
                if callback:
                    callback(f"⚠️ Видео файл не найден: {video_path}")
                return False
            
            try:
                clip = VideoFileClip(str(video_path))
                # Нормализуем к вертикальному формату 1080x1920
                # Сохраняем пропорции, добавляем черные полосы если нужно
                w, h = clip.size
                target_w, target_h = 1080, 1920
                
                # Вычисляем масштаб для вписывания в вертикальный формат
                scale_w = target_w / w
                scale_h = target_h / h
                scale = min(scale_w, scale_h)
                
                new_w = int(w * scale)
                new_h = int(h * scale)
                
                # Масштабируем
                from moviepy.video.fx.all import resize
                clip = clip.resize((new_w, new_h))
                
                # Добавляем черные полосы для достижения 1080x1920
                if new_w < target_w or new_h < target_h:
                    # Создаем черный фон нужного размера
                    from moviepy.editor import ColorClip, CompositeVideoClip
                    background = ColorClip(size=(target_w, target_h), color=(0, 0, 0), duration=clip.duration)
                    
                    # Размещаем видео по центру
                    x_center = (target_w - new_w) // 2
                    y_center = (target_h - new_h) // 2
                    clip_positioned = clip.set_position((x_center, y_center))
                    
                    # Композируем видео на черном фоне
                    clip = CompositeVideoClip([background, clip_positioned], size=(target_w, target_h))
                else:
                    # Если видео больше, обрезаем до нужного размера
                    clip = clip.resize((target_w, target_h))
                
                # Нормализуем FPS до 30
                if clip.fps != 30:
                    clip = clip.set_fps(30)
                
                clips.append(clip)
                
                if callback:
                    callback(f"✓ Загружено видео {i+1}/{len(video_files)}")
                    
            except Exception as e:
                if callback:
                    callback(f"❌ Ошибка загрузки видео {i+1}: {str(e)}")
                # Закрываем уже загруженные клипы
                for c in clips:
                    c.close()
                return False
        
        if not clips:
            if callback:
                callback(f"❌ Нет валидных видео для склейки")
            return False
        
        if callback:
            callback(f"Склеивание {len(clips)} видео...")
        
        # Склеиваем видео
        try:
            final_clip = concatenate_videoclips(clips, method="compose")
            
            if callback:
                callback(f"Сохранение результата...")
            
            # Сохраняем результат
            final_clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=30,
                bitrate='8000k',
                ffmpeg_params=['-preset', 'medium', '-crf', '23']
            )
            
            # Закрываем клипы
            final_clip.close()
            for clip in clips:
                clip.close()
            
            # Проверяем результат
            if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
                if callback:
                    file_size = os.path.getsize(output_path) // 1024 // 1024
                    callback(f"✓ Видео успешно создано: {file_size} MB")
                return True
            else:
                if callback:
                    callback(f"❌ Выходной файл не создан или слишком мал")
                return False
                
        except Exception as e:
            if callback:
                callback(f"❌ Ошибка при склейке: {str(e)}")
            # Закрываем клипы
            for clip in clips:
                clip.close()
            return False
            
    except Exception as e:
        if callback:
            callback(f"❌ Неожиданная ошибка: {str(e)}")
            import traceback
            callback(f"❌ Трассировка:\n{traceback.format_exc()[:500]}")
        return False


def process_video(ishod_folder, ozv_folder, nalog_folder, redi_folder, num_videos=1):
    """
    Обрабатывает видео: склеивает случайные видео, добавляет звук и накладывает хромакей
    """
    # Получаем список всех видео из папки ishod
    ishod_path = Path(ishod_folder)
    video_files = list(ishod_path.glob("*.mp4"))
    
    if len(video_files) < 3:
        print(f"Ошибка: в папке {ishod_folder} недостаточно видео (нужно минимум 3, найдено {len(video_files)})")
        return
    
    # Получаем аудио файлы из папки ozv
    ozv_path = Path(ozv_folder)
    audio_files = list(ozv_path.glob("*.mp3")) + list(ozv_path.glob("*.wav"))
    
    if not audio_files:
        print(f"Ошибка: в папке {ozv_folder} не найдено аудио файлов")
        return
    
    # Получаем видео с хромакеем из папки nalog
    nalog_path = Path(nalog_folder)
    chromakey_files = list(nalog_path.glob("*.mp4"))
    
    if not chromakey_files:
        print(f"Ошибка: в папке {nalog_folder} не найдено видео с хромакеем")
        return
    
    # Создаем папку redi, если её нет
    redi_path = Path(redi_folder)
    redi_path.mkdir(exist_ok=True)
    
    # Позиции для наложения хромакея
    positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right']
    
    for i in range(num_videos):
        print(f"\nОбработка видео {i+1}/{num_videos}...")
        
        # Случайно выбираем 3 видео
        selected_videos = random.sample(video_files, 3)
        print(f"Выбраны видео: {[v.name for v in selected_videos]}")
        
        # Загружаем и склеиваем видео
        clips = []
        for video_path in selected_videos:
            clip = VideoFileClip(str(video_path))
            clips.append(clip)
        
        print("Склеивание видео...")
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # Выбираем случайный аудио файл
        audio_file = random.choice(audio_files)
        print(f"Добавление звука: {audio_file.name}")
        audio_clip = AudioFileClip(str(audio_file))
        
        # Обрезаем аудио под длину видео (без зацикливания)
        video_duration = final_clip.duration
        audio_duration = audio_clip.duration
        
        if audio_duration > video_duration:
            # Обрезаем аудио, если оно длиннее видео
            audio_clip = audio_clip.subclip(0, video_duration)
        elif audio_duration < video_duration:
            # Если аудио короче видео, добавляем тишину до конца видео
            silence_duration = video_duration - audio_duration
            # Создаем тихий аудио клип
            silence = AudioClip(lambda t: [0, 0], duration=silence_duration, fps=audio_clip.fps)
            # Склеиваем аудио и тишину
            audio_clip = concatenate_audioclips([audio_clip, silence])
        
        final_clip = final_clip.set_audio(audio_clip)
        
        # Выбираем случайное видео с хромакеем и позицию
        chromakey_file = random.choice(chromakey_files)
        position = random.choice(positions)
        print(f"Наложение хромакея: {chromakey_file.name} в позиции {position}")
        
        # Накладываем видео с хромакеем
        final_clip = create_video_with_chromakey(final_clip, chromakey_file, position)
        
        # Применяем случайные эффекты для уникальности
        final_clip = apply_random_effects(final_clip)
        
        # Генерируем уникальные метаданные
        metadata = generate_unique_metadata()
        print(f"Сгенерированы метаданные: ID={metadata['video_id'][:8]}, Title={metadata['title']}")
        
        # Сохраняем результат с рандомным названием
        random_name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
        output_path = redi_path / f"{random_name}.mp4"
        print(f"Сохранение видео: {output_path.name}")
        
        # Добавляем метаданные через ffmpeg_params
        ffmpeg_params = [
            '-metadata', f"title={metadata['title']}",
            '-metadata', f"description={metadata['description']}",
            '-metadata', f"comment={metadata['description']}",
            '-metadata', f"video_id={metadata['video_id']}",
            '-metadata', f"creation_time={metadata['creation_time']}",
            '-metadata', f"artist={metadata['artist']}",
            '-metadata', f"album={metadata['album']}",
            '-metadata', f"genre=Generated",
        ]
        
        final_clip.write_videofile(
            str(output_path),
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=24,
            ffmpeg_params=ffmpeg_params
        )
        
        # Закрываем клипы для освобождения памяти
        final_clip.close()
        audio_clip.close()
        for clip in clips:
            clip.close()
        
        print(f"Видео {i+1} готово!")
    
    print(f"\nВсе {num_videos} видео успешно обработаны и сохранены в папку {redi_folder}")


def main():
    parser = argparse.ArgumentParser(description='Обработка видео: склеивание, добавление звука и хромакей')
    parser.add_argument(
        '--num',
        type=int,
        default=1,
        help='Количество видео для создания (по умолчанию: 1)'
    )
    parser.add_argument(
        '--ishod',
        type=str,
        default='ishod',
        help='Папка с исходными видео (по умолчанию: ishod)'
    )
    parser.add_argument(
        '--ozv',
        type=str,
        default='ozv',
        help='Папка с аудио файлами (по умолчанию: ozv)'
    )
    parser.add_argument(
        '--nalog',
        type=str,
        default='nalog',
        help='Папка с видео хромакея (по умолчанию: nalog)'
    )
    parser.add_argument(
        '--redi',
        type=str,
        default='redi',
        help='Папка для сохранения готовых видео (по умолчанию: redi)'
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Обработчик видео")
    print("=" * 50)
    print(f"Количество видео для создания: {args.num}")
    print(f"Папка с исходными видео: {args.ishod}")
    print(f"Папка с аудио: {args.ozv}")
    print(f"Папка с хромакеем: {args.nalog}")
    print(f"Папка для результатов: {args.redi}")
    print("=" * 50)
    
    process_video(args.ishod, args.ozv, args.nalog, args.redi, args.num)


if __name__ == "__main__":
    main()

