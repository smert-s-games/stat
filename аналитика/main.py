"""
Главное приложение для аналитики YouTube каналов
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import threading
import os
import json
from datetime import datetime
from pathlib import Path

# Импорт модулей
try:
    from modules.stats_parser import StatsParser
    from modules.account_manager import AccountManager
    from modules.video_creator import VideoCreator
    from modules.proxy_manager import ProxyManager
    from modules.telegram_bot import TelegramBotManager
    from modules.database import Database
    from modules.stats_history import StatsHistory
    from modules.export_manager import ExportManager
    from modules.scheduler import TaskScheduler
    from modules.theme_manager import ThemeManager
    from modules.report_generator import ReportGenerator
    from modules.ui_utils import darken_hex, create_themed_window, style_scrolled_text
except ImportError as e:
    import tkinter.messagebox as mb
    import sys
    mb.showerror("Ошибка импорта", f"Не удалось импортировать модули:\n{e}\n\nУбедитесь, что все файлы модулей находятся в папке 'modules'")
    sys.exit(1)

class AnalyticsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Analytics - Программа для аналитики")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # Загрузка конфигурации
        self.config_file = "config.json"
        self.config = self.load_config()
        
        # Инициализация модулей
        self.stats_parser = StatsParser()
        self.account_manager = AccountManager()
        self.video_creator = VideoCreator()
        self.proxy_manager = ProxyManager(self.config_file)
        self.telegram_bot = TelegramBotManager(self.config_file)
        self.database = Database()
        self.stats_history = StatsHistory(self.database)
        self.export_manager = ExportManager()
        self.scheduler = TaskScheduler()
        self.theme_manager = ThemeManager()
        self.report_generator = ReportGenerator()
        
        # Инициализация цветов
        self.init_colors()
        
        # Применение темы
        theme = self.config.get('theme', 'light')
        self.theme_manager.apply_theme(self.root, theme)
        self.update_colors_from_theme(theme)
        
        # Запуск планировщика
        self.scheduler.start()
        
        # Переменные для хранения данных
        self.current_stats_results = []
        self.current_accounts_data = []
        
        # Создание интерфейса
        self.create_ui()
        
        # Загрузка данных при запуске (после создания всех виджетов)
        self.refresh_accounts()
        
        # Проверка уведомлений при запуске
        self.check_notifications()
        
        # Планирование проверки прокси/сервера
        self.scheduler.add_task('proxy_check', 'daily', '09:00', self.update_proxy_status)
        
    def load_config(self):
        """Загрузка конфигурации из файла"""
        default_config = {
            "accounts_folders": [],  # Список папок с аккаунтами
            "accounts_folder": "accounts",  # Для обратной совместимости
            "links_file": "links.txt",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "proxy": {
                "purchase_date": "",
                "expiry_date": ""
            },
            "server": {
                "purchase_date": "",
                "expiry_date": ""
            },
            "theme": "light",  # Тема оформления
            "scheduled_tasks": {}  # Запланированные задачи
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Объединяем с дефолтными значениями
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    # Миграция старой конфигурации (accounts_folder -> accounts_folders)
                    if 'accounts_folder' in config and 'accounts_folders' not in config:
                        if config['accounts_folder']:
                            config['accounts_folders'] = [config['accounts_folder']]
                    elif 'accounts_folders' not in config:
                        config['accounts_folders'] = []
                    return config
            except Exception:
                return default_config
        else:
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config=None):
        """Сохранение конфигурации в файл"""
        if config is None:
            config = self.config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить конфигурацию: {e}")
    
    def create_ui(self):
        """Создание пользовательского интерфейса"""
        # Настройка стиля
        style = ttk.Style()
        style.theme_use('clam')
        
        # Инициализация цветов
        self.init_colors()
        
        # Настройка стилей ttk
        self.setup_ttk_styles()
        
        # Современная панель инструментов вместо меню
        self.create_modern_toolbar()
        
        # Вкладки с современным стилем
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладка 1: Статистика по заливам
        self.create_stats_tab()
        
        # Вкладка 2: Аккаунты
        self.create_accounts_tab()
        
        # Вкладка 3: Создание видео
        self.create_video_tab()
        
        # Вкладка 4: Прокси и сервер
        self.create_proxy_tab()
        
        # Вкладка 5: Telegram бот
        self.create_telegram_tab()

        # Строка состояния
        self.create_status_bar()
    
    def create_status_bar(self):
        """Строка состояния внизу окна"""
        self.status_bar = tk.Frame(self.root, bg=self.colors['card_bg'], height=28, relief=tk.FLAT)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        tk.Frame(self.status_bar, bg=self.colors['border'], height=1).pack(fill=tk.X, side=tk.TOP)

        self.status_label = tk.Label(
            self.status_bar,
            text="Готово",
            bg=self.colors['card_bg'],
            fg=self.colors['text_secondary'],
            font=('Segoe UI', 9),
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, padx=15, pady=4)

        theme_label = tk.Label(
            self.status_bar,
            text=f"Тема: {'Тёмная' if self.config.get('theme') == 'dark' else 'Светлая'}",
            bg=self.colors['card_bg'],
            fg=self.colors['text_secondary'],
            font=('Segoe UI', 9)
        )
        theme_label.pack(side=tk.RIGHT, padx=15, pady=4)
        self.status_theme_label = theme_label

    def set_status(self, message):
        """Обновление строки состояния"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
    
    def init_colors(self):
        """Инициализация цветов из текущей темы"""
        theme_name = self.config.get('theme', 'light')
        theme = self.theme_manager.themes.get(theme_name, self.theme_manager.themes['light'])
        self.colors = theme.copy()
    
    def update_colors_from_theme(self, theme_name):
        """Обновление цветов из темы"""
        theme = self.theme_manager.themes.get(theme_name, self.theme_manager.themes['light'])
        self.colors = theme.copy()
    
    def create_rounded_card(self, parent, title=None, title_color=None, fill=tk.X, expand=False):
        """Создание закругленной карточки с заголовком и эффектом тени/закругления"""
        # Внешний контейнер
        outer_frame = tk.Frame(parent, bg=self.colors['bg'], relief=tk.FLAT)
        outer_frame.pack(fill=fill, expand=expand, padx=15, pady=10)
        
        # Фрейм для эффекта тени и закругления (более выраженный эффект)
        shadow_color = '#d0d0d0' if self.colors['bg'] == '#f8f9fa' else '#3a3a3a'
        shadow_frame = tk.Frame(outer_frame, bg=shadow_color, relief=tk.FLAT)
        shadow_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        
        # Промежуточный фрейм для более плавного закругления
        mid_frame = tk.Frame(shadow_frame, bg=self.colors['border'], relief=tk.FLAT)
        mid_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Внутренняя карточка
        inner_frame = tk.Frame(mid_frame, bg=self.colors['card_bg'], relief=tk.FLAT, bd=0)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Заголовок если есть
        header = None
        content = inner_frame
        if title:
            title_color = title_color or self.colors['accent']
            header = tk.Frame(inner_frame, bg=title_color, height=45)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            
            tk.Label(header, text=title, bg=title_color, fg='white',
                    font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)
            
            content = tk.Frame(inner_frame, bg=self.colors['card_bg'])
            content.pack(fill=tk.BOTH, expand=True)
        
        return content, inner_frame, header
    
    def setup_ttk_styles(self):
        """Настройка стилей ttk"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Настройка цветов для ttk
        style.configure('TFrame', background=self.colors['bg'], relief=tk.FLAT)
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'], 
                       font=('Segoe UI', 9))
        style.configure('TLabelFrame', background=self.colors['bg'], foreground=self.colors['fg'],
                       borderwidth=1, relief=tk.FLAT, font=('Segoe UI', 9, 'bold'))
        style.configure('TLabelFrame.Label', background=self.colors['card_bg'], 
                       foreground=self.colors['accent'], font=('Segoe UI', 9, 'bold'))
        
        # Современные кнопки
        style.configure('TButton', background=self.colors['accent'], foreground='white', 
                       borderwidth=0, focuscolor='none', padding=(15, 8), font=('Segoe UI', 9),
                       relief=tk.FLAT)
        style.map('TButton', 
                 background=[('active', self.colors['accent_hover']), ('pressed', self.colors['accent_hover'])],
                 relief=[('pressed', 'flat')])
        
        # Вкладки
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=self.colors['card_bg'], foreground=self.colors['fg'],
                       padding=[25, 12], font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.map('TNotebook.Tab', 
                 background=[('selected', self.colors['accent']), ('active', self.colors['hover_bg'])],
                 foreground=[('selected', 'white'), ('active', self.colors['accent'])],
                 expand=[('selected', [1, 1, 1, 0])])
        
        # Поля ввода
        style.configure('TEntry', fieldbackground=self.colors['card_bg'], 
                       foreground=self.colors['fg'], borderwidth=1, relief=tk.FLAT,
                       padding=8, font=('Segoe UI', 9))
        style.map('TEntry', 
                 fieldbackground=[('focus', self.colors['card_bg'])],
                 bordercolor=[('focus', self.colors['accent'])])
        
        # Спинбоксы
        style.configure('TSpinbox', fieldbackground=self.colors['card_bg'], 
                       foreground=self.colors['fg'], borderwidth=1, relief=tk.FLAT,
                       padding=8, font=('Segoe UI', 9))
        
        # Скроллбары
        style.configure('TScrollbar', background=self.colors['border'], 
                       troughcolor=self.colors['bg'], borderwidth=0,
                       arrowcolor=self.colors['text_secondary'], width=12)
        style.map('TScrollbar', background=[('active', self.colors['accent'])])

        # Таблицы
        style.configure('Treeview', background=self.colors['card_bg'],
                       foreground=self.colors['fg'], fieldbackground=self.colors['card_bg'],
                       font=('Segoe UI', 9), borderwidth=0, rowheight=28)
        style.configure('Treeview.Heading', background=self.colors['hover_bg'],
                       foreground=self.colors['fg'], font=('Segoe UI', 9, 'bold'), relief=tk.FLAT)
        style.map('Treeview',
                 background=[('selected', self.colors['accent'])],
                 foreground=[('selected', 'white')])
        
        self.root.configure(bg=self.colors['bg'])
    
    def create_stats_tab(self):
        """Вкладка со статистикой по заливам"""
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="📊 Статистика")
        
        # Верхняя панель с кнопками - современный дизайн
        control_frame = tk.Frame(stats_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        control_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Группа основных действий
        actions_frame = tk.Frame(control_frame, bg=self.colors['card_bg'])
        actions_frame.pack(side=tk.LEFT, padx=5)
        
        self.create_modern_button(actions_frame, "🔄 Обновить", self.run_stats_parser, 
                                 self.colors['accent']).pack(side=tk.LEFT, padx=3)
        self.create_modern_button(actions_frame, "📁 Файл", self.select_links_file, 
                                 self.colors['text_secondary']).pack(side=tk.LEFT, padx=3)
        self.create_modern_button(actions_frame, "📊 История", self.show_stats_history, 
                                 self.colors['success']).pack(side=tk.LEFT, padx=3)
        self.create_modern_button(actions_frame, "💾 Экспорт", self.export_stats_menu, 
                                 self.colors['warning']).pack(side=tk.LEFT, padx=3)
        
        # Информация о файле справа
        info_frame = tk.Frame(control_frame, bg=self.colors['card_bg'])
        info_frame.pack(side=tk.RIGHT, padx=10)
        
        self.links_file_label = tk.Label(info_frame, 
                                         text=f"📄 {os.path.basename(self.config.get('links_file', 'links.txt'))}",
                                         bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
                                         font=('Segoe UI', 9))
        self.links_file_label.pack()
        
        # Панель фильтров и поиска - в закругленной карточке
        filter_content, _, _ = self.create_rounded_card(stats_frame, fill=tk.X)
        filter_frame = tk.Frame(filter_content, bg=self.colors['card_bg'], relief=tk.FLAT)
        filter_frame.pack(fill=tk.X, padx=15, pady=15)
        
        search_label = tk.Label(filter_frame, text="🔍 Поиск:", 
                               bg=self.colors['card_bg'], fg=self.colors['fg'],
                               font=('Segoe UI', 9, 'bold'))
        search_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.stats_search_entry = tk.Entry(filter_frame, width=40, 
                                           font=('Segoe UI', 9),
                                           bg=self.colors['card_bg'], fg=self.colors['fg'],
                                           relief=tk.FLAT, bd=1, highlightthickness=1,
                                           highlightbackground=self.colors['border'],
                                           highlightcolor=self.colors['accent'])
        self.stats_search_entry.pack(side=tk.LEFT, padx=5, pady=10, ipady=5)
        self.stats_search_entry.bind('<KeyRelease>', self.filter_stats_table)
        
        self.create_modern_button(filter_frame, "Найти", self.filter_stats_table, 
                                 self.colors['accent'], small=True).pack(side=tk.LEFT, padx=3, pady=10)
        self.create_modern_button(filter_frame, "Сброс", self.reset_stats_filter, 
                                 self.colors['text_secondary'], small=True).pack(side=tk.LEFT, padx=3, pady=10)
        
        # Общая статистика - карточка с закруглением
        summary_content, _, _ = self.create_rounded_card(stats_frame, "📈 Общая статистика", 
                                                         self.colors['accent'], fill=tk.X)
        
        self.stats_summary_text = tk.Text(summary_content, height=8, wrap=tk.WORD,
                                         bg=self.colors['card_bg'], fg=self.colors['fg'],
                                         font=('Segoe UI', 9), relief=tk.FLAT,
                                         padx=15, pady=15, borderwidth=0)
        self.stats_summary_text.pack(fill=tk.BOTH, expand=True)
        self.stats_summary_text.insert("1.0", "Нажмите 'Обновить' для получения данных")
        self.stats_summary_text.config(state=tk.DISABLED)
        
        # Детальная статистика по каналам - карточка с закруглением
        table_frame, _, _ = self.create_rounded_card(stats_frame, "📋 Детальная статистика по каналам",
                                                     self.colors['accent'], fill=tk.BOTH, expand=True)
        
        columns = ("Канал", "Подписчики", "Просмотры", "Видео", "Статус")
        self.stats_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        # Стилизация таблицы
        style = ttk.Style()
        style.configure("Treeview", background=self.colors['card_bg'], 
                       foreground=self.colors['fg'], fieldbackground=self.colors['card_bg'],
                       font=('Segoe UI', 9))
        style.configure("Treeview.Heading", background=self.colors['hover_bg'],
                       foreground=self.colors['fg'], font=('Segoe UI', 9, 'bold'),
                       relief=tk.FLAT)
        style.map("Treeview", background=[('selected', self.colors['accent'])])
        
        for col in columns:
            self.stats_tree.heading(col, text=col)
            self.stats_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.stats_tree.yview)
        self.stats_tree.configure(yscrollcommand=scrollbar.set)
        
        self.stats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=15)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=15)
        
        # Лог выполнения - карточка
        log_frame = tk.Frame(stats_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Заголовок лога
        log_header = tk.Frame(log_frame, bg=self.colors['text_secondary'], height=40)
        log_header.pack(fill=tk.X)
        log_header.pack_propagate(False)
        
        tk.Label(log_header, text="📝 Лог выполнения", 
                bg=self.colors['text_secondary'], fg='white',
                font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)
        
        # Содержимое лога
        log_content = tk.Frame(log_frame, bg=self.colors['card_bg'])
        log_content.pack(fill=tk.BOTH, expand=True)
        
        self.stats_log = scrolledtext.ScrolledText(log_content, height=8, wrap=tk.WORD,
                                                   bg=self.colors['card_bg'], fg=self.colors['fg'],
                                                   font=('Consolas', 9), relief=tk.FLAT,
                                                   padx=15, pady=15, borderwidth=0)
        self.stats_log.pack(fill=tk.BOTH, expand=True)
    
    def create_accounts_tab(self):
        """Вкладка с информацией об аккаунтах"""
        accounts_frame = ttk.Frame(self.notebook)
        self.notebook.add(accounts_frame, text="👤 Аккаунты")
        
        # Верхняя панель управления - современный дизайн
        control_frame = tk.Frame(accounts_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        control_frame.pack(fill=tk.X, padx=15, pady=15)
        
        actions_frame = tk.Frame(control_frame, bg=self.colors['card_bg'])
        actions_frame.pack(side=tk.LEFT, padx=5)
        
        self.create_modern_button(actions_frame, "🔄 Обновить", self.refresh_accounts, 
                                 self.colors['accent']).pack(side=tk.LEFT, padx=3)
        self.create_modern_button(actions_frame, "➕ Добавить папку", self.add_accounts_folder, 
                                 self.colors['success']).pack(side=tk.LEFT, padx=3)
        self.create_modern_button(actions_frame, "🗑️ Удалить", self.delete_selected_account, 
                                 self.colors['danger']).pack(side=tk.LEFT, padx=3)
        self.create_modern_button(actions_frame, "📋 Массовые", self.open_bulk_operations, 
                                 self.colors['warning']).pack(side=tk.LEFT, padx=3)
        self.create_modern_button(actions_frame, "🏷️ Теги", self.manage_account_tags, 
                                 self.colors['text_secondary']).pack(side=tk.LEFT, padx=3)
        
        # Панель со списком папок - карточка
        folders_frame = tk.Frame(accounts_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        folders_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # Заголовок
        folders_header = tk.Frame(folders_frame, bg=self.colors['success'], height=40)
        folders_header.pack(fill=tk.X)
        folders_header.pack_propagate(False)
        
        tk.Label(folders_header, text="📁 Добавленные папки с профилями", 
                bg=self.colors['success'], fg='white',
                font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)
        
        # Список папок с прокруткой
        folders_content = tk.Frame(folders_frame, bg=self.colors['card_bg'])
        folders_content.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        folders_list_frame = tk.Frame(folders_content, bg=self.colors['card_bg'])
        folders_list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        self.folders_listbox = tk.Listbox(folders_list_frame, height=4,
                                         bg=self.colors['card_bg'], fg=self.colors['fg'],
                                         font=('Segoe UI', 9), relief=tk.FLAT,
                                         selectbackground=self.colors['accent'],
                                         selectforeground='white',
                                         borderwidth=1, highlightthickness=1,
                                         highlightbackground=self.colors['border'],
                                         highlightcolor=self.colors['accent'])
        self.folders_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        folders_scrollbar = ttk.Scrollbar(folders_list_frame, orient=tk.VERTICAL, command=self.folders_listbox.yview)
        self.folders_listbox.configure(yscrollcommand=folders_scrollbar.set)
        folders_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопки управления папками
        folders_buttons_frame = tk.Frame(folders_content, bg=self.colors['card_bg'])
        folders_buttons_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        self.create_modern_button(folders_buttons_frame, "➖ Удалить папку", 
                                 self.remove_selected_folder, self.colors['danger'], small=True).pack(side=tk.LEFT, padx=3)
        self.create_modern_button(folders_buttons_frame, "🗑️ Очистить все", 
                                 self.clear_all_folders, self.colors['text_secondary'], small=True).pack(side=tk.LEFT, padx=3)
        
        # Общая статистика по аккаунтам - карточка
        summary_frame = tk.Frame(accounts_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        summary_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # Заголовок
        summary_header = tk.Frame(summary_frame, bg=self.colors['accent'], height=40)
        summary_header.pack(fill=tk.X)
        summary_header.pack_propagate(False)
        
        tk.Label(summary_header, text="📊 Общая статистика", 
                bg=self.colors['accent'], fg='white',
                font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)
        
        # Содержимое
        summary_content = tk.Frame(summary_frame, bg=self.colors['card_bg'])
        summary_content.pack(fill=tk.BOTH, expand=True)
        
        self.accounts_summary_text = tk.Text(summary_content, height=6, wrap=tk.WORD,
                                            bg=self.colors['card_bg'], fg=self.colors['fg'],
                                            font=('Segoe UI', 9), relief=tk.FLAT,
                                            padx=15, pady=15, borderwidth=0)
        self.accounts_summary_text.pack(fill=tk.BOTH, expand=True)
        self.accounts_summary_text.config(state=tk.DISABLED)
        
        # Таблица аккаунтов - карточка
        details_frame = tk.Frame(accounts_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Заголовок таблицы
        table_header = tk.Frame(details_frame, bg=self.colors['success'], height=40)
        table_header.pack(fill=tk.X)
        table_header.pack_propagate(False)
        
        tk.Label(table_header, text="👥 Список аккаунтов (из всех папок)", 
                bg=self.colors['success'], fg='white',
                font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)
        
        # Таблица
        table_content = tk.Frame(details_frame, bg=self.colors['card_bg'])
        table_content.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Аккаунт", "Папка", "Материалов", "Размер", "Дата изменения", "Качество")
        self.accounts_tree = ttk.Treeview(table_content, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.accounts_tree.heading(col, text=col)
            if col == "Папка":
                self.accounts_tree.column(col, width=200)
            else:
                self.accounts_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(table_content, orient=tk.VERTICAL, command=self.accounts_tree.yview)
        self.accounts_tree.configure(yscrollcommand=scrollbar.set)
        
        self.accounts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=15)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=15)
        
        # Двойной клик для просмотра деталей
        self.accounts_tree.bind("<Double-1>", self.view_account_details)
        
        # Обновляем список папок при создании вкладки
        self.update_folders_list()
    
    def create_video_tab(self):
        """Вкладка для создания видео"""
        video_frame = ttk.Frame(self.notebook)
        self.notebook.add(video_frame, text="🎬 Видео")

        control_frame = tk.Frame(video_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        control_frame.pack(fill=tk.X, padx=15, pady=15)

        actions_frame = tk.Frame(control_frame, bg=self.colors['card_bg'])
        actions_frame.pack(side=tk.LEFT, padx=5)

        self.video_start_btn = self.create_modern_button(
            actions_frame, "▶️ Запустить", self.start_video_creation, self.colors['accent']
        )
        self.video_start_btn.pack(side=tk.LEFT, padx=3)

        self.video_stop_btn = self.create_modern_button(
            actions_frame, "⏹️ Остановить", self.stop_video_creation, self.colors['danger']
        )
        self.video_stop_btn.pack(side=tk.LEFT, padx=3)
        self.video_stop_btn.config(state=tk.DISABLED)

        settings_content, _, _ = self.create_rounded_card(
            video_frame, "⚙️ Настройки", self.colors['accent'], fill=tk.X
        )
        settings_inner = tk.Frame(settings_content, bg=self.colors['card_bg'])
        settings_inner.pack(fill=tk.X, padx=15, pady=15)

        def add_setting_row(row, label_text, widget_factory):
            tk.Label(settings_inner, text=label_text, bg=self.colors['card_bg'], fg=self.colors['fg'],
                     font=('Segoe UI', 9, 'bold')).grid(row=row, column=0, sticky=tk.W, padx=5, pady=8)
            widget_factory().grid(row=row, column=1, sticky=tk.EW, padx=5, pady=8)

        settings_inner.columnconfigure(1, weight=1)

        self.video_input_entry = tk.Entry(
            settings_inner, font=('Segoe UI', 9), bg=self.colors['card_bg'], fg=self.colors['fg'],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=self.colors['border'], highlightcolor=self.colors['accent']
        )
        self.video_input_entry.insert(0, "video_from_pinterest")
        add_setting_row(0, "📁 Исходные видео:", lambda: self.video_input_entry)
        self.create_modern_button(
            settings_inner, "...", self.select_video_input_folder, self.colors['text_secondary'], small=True
        ).grid(row=0, column=2, padx=5, pady=8)

        self.video_output_entry = tk.Entry(
            settings_inner, font=('Segoe UI', 9), bg=self.colors['card_bg'], fg=self.colors['fg'],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=self.colors['border'], highlightcolor=self.colors['accent']
        )
        self.video_output_entry.insert(0, "ready_videos")
        add_setting_row(1, "📤 Готовые видео:", lambda: self.video_output_entry)
        self.create_modern_button(
            settings_inner, "...", self.select_video_output_folder, self.colors['text_secondary'], small=True
        ).grid(row=1, column=2, padx=5, pady=8)

        spin_frame = tk.Frame(settings_inner, bg=self.colors['card_bg'])
        self.videos_per_group = tk.Spinbox(
            spin_frame, from_=2, to=10, width=8, font=('Segoe UI', 9),
            bg=self.colors['card_bg'], fg=self.colors['fg'], relief=tk.FLAT,
            highlightthickness=1, highlightbackground=self.colors['border']
        )
        self.videos_per_group.delete(0, tk.END)
        self.videos_per_group.insert(0, "3")
        self.videos_per_group.pack(side=tk.LEFT)
        tk.Label(spin_frame, text=" (макс. 500 перестановок)", bg=self.colors['card_bg'],
                 fg=self.colors['text_secondary'], font=('Segoe UI', 8)).pack(side=tk.LEFT, padx=8)
        add_setting_row(2, "🎞️ Видео в группе:", lambda: spin_frame)

        progress_content, _, _ = self.create_rounded_card(
            video_frame, "📊 Прогресс", self.colors['success'], fill=tk.X
        )
        progress_inner = tk.Frame(progress_content, bg=self.colors['card_bg'])
        progress_inner.pack(fill=tk.X, padx=15, pady=15)

        self.video_progress = ttk.Progressbar(progress_inner, mode='determinate')
        self.video_progress.pack(fill=tk.X, pady=(0, 8))

        self.video_status_label = tk.Label(
            progress_inner, text="Готов к запуску", bg=self.colors['card_bg'],
            fg=self.colors['text_secondary'], font=('Segoe UI', 9)
        )
        self.video_status_label.pack(anchor=tk.W)

        log_content, _, _ = self.create_rounded_card(
            video_frame, "📝 Лог выполнения", self.colors['text_secondary'], fill=tk.BOTH, expand=True
        )
        self.video_log = scrolledtext.ScrolledText(log_content, height=12, wrap=tk.WORD)
        style_scrolled_text(self.video_log, self.colors, font=('Consolas', 9))
        self.video_log.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.video_thread = None
        self.video_stop_flag = False
    
    def create_proxy_tab(self):
        """Вкладка для управления прокси и сервером"""
        proxy_frame = ttk.Frame(self.notebook)
        self.notebook.add(proxy_frame, text="🌐 Прокси")

        proxy_content, _, _ = self.create_rounded_card(
            proxy_frame, "📡 Прокси", self.colors['accent'], fill=tk.X
        )
        proxy_form = tk.Frame(proxy_content, bg=self.colors['card_bg'])
        proxy_form.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(proxy_form, text="Дата покупки (ДД.ММ.ГГГГ):", bg=self.colors['card_bg'],
                 fg=self.colors['fg'], font=('Segoe UI', 9)).grid(row=0, column=0, sticky=tk.W, pady=6)
        self.proxy_purchase_entry = tk.Entry(
            proxy_form, width=30, font=('Segoe UI', 9), bg=self.colors['card_bg'], fg=self.colors['fg'],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=self.colors['border'], highlightcolor=self.colors['accent']
        )
        self.proxy_purchase_entry.insert(0, self.config.get('proxy', {}).get('purchase_date', ''))
        self.proxy_purchase_entry.grid(row=0, column=1, padx=10, pady=6)

        tk.Label(proxy_form, text="Дата окончания:", bg=self.colors['card_bg'],
                 fg=self.colors['fg'], font=('Segoe UI', 9)).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.proxy_expiry_entry = tk.Entry(
            proxy_form, width=30, font=('Segoe UI', 9), bg=self.colors['card_bg'], fg=self.colors['fg'],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=self.colors['border'], highlightcolor=self.colors['accent']
        )
        self.proxy_expiry_entry.insert(0, self.config.get('proxy', {}).get('expiry_date', ''))
        self.proxy_expiry_entry.grid(row=1, column=1, padx=10, pady=6)

        self.create_modern_button(
            proxy_form, "💾 Сохранить прокси", self.save_proxy_info, self.colors['success'], small=True
        ).grid(row=2, column=1, sticky=tk.W, pady=10)

        server_content, _, _ = self.create_rounded_card(
            proxy_frame, "🖥️ Сервер", self.colors['success'], fill=tk.X
        )
        server_form = tk.Frame(server_content, bg=self.colors['card_bg'])
        server_form.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(server_form, text="Дата покупки (ДД.ММ.ГГГГ):", bg=self.colors['card_bg'],
                 fg=self.colors['fg'], font=('Segoe UI', 9)).grid(row=0, column=0, sticky=tk.W, pady=6)
        self.server_purchase_entry = tk.Entry(
            server_form, width=30, font=('Segoe UI', 9), bg=self.colors['card_bg'], fg=self.colors['fg'],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=self.colors['border'], highlightcolor=self.colors['accent']
        )
        self.server_purchase_entry.insert(0, self.config.get('server', {}).get('purchase_date', ''))
        self.server_purchase_entry.grid(row=0, column=1, padx=10, pady=6)

        tk.Label(server_form, text="Дата окончания:", bg=self.colors['card_bg'],
                 fg=self.colors['fg'], font=('Segoe UI', 9)).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.server_expiry_entry = tk.Entry(
            server_form, width=30, font=('Segoe UI', 9), bg=self.colors['card_bg'], fg=self.colors['fg'],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=self.colors['border'], highlightcolor=self.colors['accent']
        )
        self.server_expiry_entry.insert(0, self.config.get('server', {}).get('expiry_date', ''))
        self.server_expiry_entry.grid(row=1, column=1, padx=10, pady=6)

        self.create_modern_button(
            server_form, "💾 Сохранить сервер", self.save_server_info, self.colors['success'], small=True
        ).grid(row=2, column=1, sticky=tk.W, pady=10)

        status_content, _, _ = self.create_rounded_card(
            proxy_frame, "📋 Статус", self.colors['warning'], fill=tk.BOTH, expand=True
        )
        self.proxy_status_text = scrolledtext.ScrolledText(status_content, height=10, wrap=tk.WORD)
        style_scrolled_text(self.proxy_status_text, self.colors)
        self.proxy_status_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.update_proxy_status()
    
    def create_telegram_tab(self):
        """Вкладка для управления Telegram ботом"""
        telegram_frame = ttk.Frame(self.notebook)
        self.notebook.add(telegram_frame, text="📱 Telegram")

        settings_content, _, _ = self.create_rounded_card(
            telegram_frame, "⚙️ Настройки бота", self.colors['accent'], fill=tk.X
        )
        settings_form = tk.Frame(settings_content, bg=self.colors['card_bg'])
        settings_form.pack(fill=tk.X, padx=15, pady=15)
        settings_form.columnconfigure(1, weight=1)

        tk.Label(settings_form, text="Bot Token:", bg=self.colors['card_bg'],
                 fg=self.colors['fg'], font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.bot_token_entry = tk.Entry(
            settings_form, show="*", font=('Segoe UI', 9), bg=self.colors['card_bg'], fg=self.colors['fg'],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=self.colors['border'], highlightcolor=self.colors['accent']
        )
        self.bot_token_entry.insert(0, self.config.get('telegram_bot_token', ''))
        self.bot_token_entry.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=8)

        tk.Label(settings_form, text="Chat ID:", bg=self.colors['card_bg'],
                 fg=self.colors['fg'], font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.chat_id_entry = tk.Entry(
            settings_form, font=('Segoe UI', 9), bg=self.colors['card_bg'], fg=self.colors['fg'],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=self.colors['border'], highlightcolor=self.colors['accent']
        )
        self.chat_id_entry.insert(0, self.config.get('telegram_chat_id', ''))
        self.chat_id_entry.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=8)

        btn_frame = tk.Frame(settings_form, bg=self.colors['card_bg'])
        btn_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.create_modern_button(
            btn_frame, "💾 Сохранить", self.save_telegram_settings, self.colors['success'], small=True
        ).pack(side=tk.LEFT, padx=(0, 8))

        control_frame = tk.Frame(telegram_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        control_frame.pack(fill=tk.X, padx=15, pady=10)

        self.bot_start_btn = self.create_modern_button(
            control_frame, "▶️ Запустить", self.start_telegram_bot, self.colors['accent']
        )
        self.bot_start_btn.pack(side=tk.LEFT, padx=3)

        self.bot_stop_btn = self.create_modern_button(
            control_frame, "⏹️ Остановить", self.stop_telegram_bot, self.colors['danger']
        )
        self.bot_stop_btn.pack(side=tk.LEFT, padx=3)
        self.bot_stop_btn.config(state=tk.DISABLED)

        self.create_modern_button(
            control_frame, "📤 Тест", self.send_test_message, self.colors['warning'], small=True
        ).pack(side=tk.LEFT, padx=3)

        status_content, _, _ = self.create_rounded_card(
            telegram_frame, "📋 Статус бота", self.colors['text_secondary'], fill=tk.BOTH, expand=True
        )
        self.bot_status_text = scrolledtext.ScrolledText(status_content, height=15, wrap=tk.WORD)
        style_scrolled_text(self.bot_status_text, self.colors)
        self.bot_status_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.bot_status_text.insert("1.0", "Бот не запущен")
        self.bot_status_text.config(state=tk.DISABLED)
    
    # Методы для работы со статистикой
    def select_links_file(self):
        """Выбор файла со ссылками"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title="Выберите файл со ссылками",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.config['links_file'] = filename
            self.links_file_label.config(text=f"📄 {os.path.basename(filename)}")
            self.save_config()
    
    def run_stats_parser(self):
        """Запуск парсера статистики в отдельном потоке"""
        links_file = self.config.get('links_file', 'links.txt')
        if not os.path.exists(links_file):
            messagebox.showerror("Ошибка", f"Файл со ссылками не найден:\n{links_file}")
            return

        self.set_status("Парсинг статистики...")
        thread = threading.Thread(target=self._run_stats_parser_thread, daemon=True)
        thread.start()
    
    def _append_stats_log(self, message, clear=False):
        """Безопасное обновление лога парсинга из главного потока"""
        self.stats_log.config(state=tk.NORMAL)
        if clear:
            self.stats_log.delete("1.0", tk.END)
        self.stats_log.insert(tk.END, message)
        self.stats_log.see(tk.END)
        self.stats_log.config(state=tk.DISABLED)

    def _run_stats_parser_thread(self):
        """Поток для выполнения парсинга статистики"""
        self.root.after(0, self._append_stats_log, "Начинаю парсинг статистики...\n", True)
        
        def progress_callback(current, total, link):
            self.root.after(0, self._append_stats_log, f"[{current}/{total}] {link}\n")

        try:
            results = self.stats_parser.parse_channels(
                self.config.get('links_file', 'links.txt'),
                progress_callback=progress_callback
            )
            self.root.after(0, self._update_stats_ui, results)
            self.root.after(0, self.set_status, f"Парсинг завершён: {len(results)} каналов")
        except Exception as e:
            self.root.after(0, self._stats_error, str(e))
            self.root.after(0, self.set_status, "Ошибка парсинга")
    
    def _update_stats_ui(self, results):
        """Обновление UI со статистикой"""
        # Сохраняем результаты
        self.current_stats_results = results
        
        # Сохраняем в базу данных
        self.stats_history.save_stats(results)
        self.database.log_operation('stats_parse', f'Парсинг статистики: {len(results)} каналов')
        
        # Очистка таблицы
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        
        # Подсчет общей статистики
        total_channels = 0
        total_views = 0
        total_subs = 0
        total_videos = 0
        
        for result in results:
            if 'error' not in result:
                total_channels += 1
                views = self.stats_parser.parse_number(result.get('total_views', '0'))
                subs = self.stats_parser.parse_number(result.get('subscribers', '0'))
                videos = self.stats_parser.parse_number(result.get('videos_count', '0'))
                
                total_views += views
                total_subs += subs
                total_videos += videos
                
                self.stats_tree.insert("", tk.END, values=(
                    result.get('channel_name', 'Неизвестно'),
                    result.get('subscribers', '0'),
                    result.get('total_views', '0'),
                    result.get('videos_count', '0'),
                    "✅"
                ))
            else:
                self.stats_tree.insert("", tk.END, values=(
                    result.get('url', 'Неизвестно'),
                    "-",
                    "-",
                    "-",
                    f"❌ {result.get('error', 'Ошибка')}"
                ))
        
        # Обновление общей статистики
        self.stats_summary_text.config(state=tk.NORMAL)
        self.stats_summary_text.delete("1.0", tk.END)
        summary = f"""📊 ОБЩАЯ СТАТИСТИКА:
        
📈 Каналов обработано: {total_channels}
👀 Всего просмотров: {self.stats_parser.format_large_number(total_views)}
👥 Всего подписчиков: {self.stats_parser.format_large_number(total_subs)}
🎥 Всего видео: {self.stats_parser.format_large_number(total_videos)}

📊 Средние показатели на канал:
   👀 Просмотры: {self.stats_parser.format_large_number(total_views // max(1, total_channels))}
   👥 Подписчики: {self.stats_parser.format_large_number(total_subs // max(1, total_channels))}
   🎥 Видео: {self.stats_parser.format_large_number(total_videos // max(1, total_channels))}
"""
        self.stats_summary_text.insert("1.0", summary)
        self.stats_summary_text.config(state=tk.DISABLED)
        
        # Обновление лога
        self.stats_log.config(state=tk.NORMAL)
        self.stats_log.insert(tk.END, f"\n✅ Парсинг завершен. Обработано каналов: {len(results)}\n")
        self.stats_log.config(state=tk.DISABLED)
    
    def _stats_error(self, error_msg):
        """Обработка ошибки парсинга"""
        self._append_stats_log(f"\n❌ Ошибка: {error_msg}\n")
        messagebox.showerror("Ошибка", f"Ошибка при парсинге статистики:\n{error_msg}")
    
    # Методы для работы с аккаунтами
    def update_folders_list(self):
        """Обновление списка папок в интерфейсе"""
        self.folders_listbox.delete(0, tk.END)
        folders = self.config.get('accounts_folders', [])
        for folder in folders:
            self.folders_listbox.insert(tk.END, folder)
    
    def add_accounts_folder(self):
        """Добавление новой папки с аккаунтами"""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Выберите папку с профилями аккаунтов")
        if folder:
            if 'accounts_folders' not in self.config:
                self.config['accounts_folders'] = []
            
            # Проверяем, не добавлена ли уже эта папка
            if folder not in self.config['accounts_folders']:
                self.config['accounts_folders'].append(folder)
                self.save_config()
                self.update_folders_list()
                self.refresh_accounts()
                messagebox.showinfo("Успех", f"Папка добавлена:\n{folder}")
            else:
                messagebox.showwarning("Предупреждение", "Эта папка уже добавлена")
    
    def remove_selected_folder(self):
        """Удаление выбранной папки из списка"""
        selection = self.folders_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите папку для удаления из списка")
            return
        
        folder_to_remove = self.folders_listbox.get(selection[0])
        
        if messagebox.askyesno("Подтверждение", f"Удалить папку из списка?\n{folder_to_remove}\n\n(Аккаунты не будут удалены, только папка будет убрана из списка)"):
            if 'accounts_folders' in self.config:
                if folder_to_remove in self.config['accounts_folders']:
                    self.config['accounts_folders'].remove(folder_to_remove)
                    self.save_config()
                    self.update_folders_list()
                    self.refresh_accounts()
                    messagebox.showinfo("Успех", "Папка удалена из списка")
    
    def clear_all_folders(self):
        """Очистка всех папок из списка"""
        if messagebox.askyesno("Подтверждение", "Удалить все папки из списка?\n\n(Аккаунты не будут удалены, только папки будут убраны из списка)"):
            self.config['accounts_folders'] = []
            self.save_config()
            self.update_folders_list()
            self.refresh_accounts()
            messagebox.showinfo("Успех", "Все папки удалены из списка")
    
    def refresh_accounts(self):
        """Обновление списка аккаунтов из всех добавленных папок"""
        # Проверка, что виджеты созданы
        if not hasattr(self, 'accounts_summary_text'):
            return
        
        folders = self.config.get('accounts_folders', [])
        
        if not folders:
            self.accounts_summary_text.config(state=tk.NORMAL)
            self.accounts_summary_text.delete("1.0", tk.END)
            self.accounts_summary_text.insert("1.0", "Не добавлено ни одной папки с аккаунтами.\nИспользуйте кнопку '➕ Добавить папку' для добавления папок с профилями.")
            self.accounts_summary_text.config(state=tk.DISABLED)
            
            # Очистка таблицы
            if hasattr(self, 'accounts_tree'):
                for item in self.accounts_tree.get_children():
                    self.accounts_tree.delete(item)
            return
        
        # Сканируем все папки
        accounts_data = self.account_manager.scan_multiple_folders(folders)
        
        # Проверка существования виджета таблицы
        if not hasattr(self, 'accounts_tree'):
            return
        
        # Очистка таблицы
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        
        # Сохраняем данные
        self.current_accounts_data = accounts_data
        
        # Заполнение таблицы
        total_materials = 0
        total_size = 0
        
        for account in accounts_data:
            # Получаем короткое имя папки для отображения
            folder_display = os.path.basename(account.get('folder', '')) or account.get('folder', 'Неизвестно')
            
            self.accounts_tree.insert("", tk.END, values=(
                account['name'],
                folder_display,
                account['materials_count'],
                account['size'],
                account['modified_date'],
                account['quality_score']
            ), tags=(account['name'],))
            
            total_materials += account['materials_count']
            total_size += account['size_bytes']
        
        # Обновление общей статистики
        if hasattr(self, 'accounts_summary_text'):
            self.accounts_summary_text.config(state=tk.NORMAL)
            self.accounts_summary_text.delete("1.0", tk.END)
            summary = f"""📊 СТАТИСТИКА ПО АККАУНТАМ:

📁 Папок добавлено: {len(folders)}
👤 Всего аккаунтов: {len(accounts_data)}
📁 Всего материалов: {total_materials}
💾 Общий размер: {self.account_manager.format_size(total_size)}
📊 Среднее материалов на аккаунт: {total_materials // max(1, len(accounts_data))}
"""
            self.accounts_summary_text.insert("1.0", summary)
            self.accounts_summary_text.config(state=tk.DISABLED)
    
    def view_account_details(self, event):
        """Просмотр деталей аккаунта"""
        selection = self.accounts_tree.selection()
        if selection:
            item = self.accounts_tree.item(selection[0])
            account_name = item['values'][0]
            messagebox.showinfo("Детали аккаунта", f"Аккаунт: {account_name}\n\nДетальная информация будет доступна в будущих версиях")
    
    def delete_selected_account(self):
        """Удаление выбранного аккаунта"""
        selection = self.accounts_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите аккаунт для удаления")
            return
        
        item = self.accounts_tree.item(selection[0])
        values = item['values']
        account_name = values[0]
        folder_display = values[1] if len(values) > 1 else ""  # Короткое имя папки
        
        # Находим полный путь к папке
        folders = self.config.get('accounts_folders', [])
        account_path = None
        
        # Ищем папку по короткому имени или полному пути
        for folder in folders:
            if os.path.basename(folder) == folder_display or folder == folder_display:
                potential_path = os.path.join(folder, account_name)
                if os.path.exists(potential_path):
                    account_path = potential_path
                    break
        
        # Если не нашли, пробуем найти в любой из папок
        if not account_path:
            for folder in folders:
                potential_path = os.path.join(folder, account_name)
                if os.path.exists(potential_path):
                    account_path = potential_path
                    break
        
        if not account_path or not os.path.exists(account_path):
            messagebox.showerror("Ошибка", f"Не удалось найти папку аккаунта '{account_name}'")
            return
        
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить аккаунт '{account_name}'?\n\nПапка: {account_path}\n\nЭто действие нельзя отменить!"):
            try:
                import shutil
                shutil.rmtree(account_path)
                messagebox.showinfo("Успех", f"Аккаунт '{account_name}' удален")
                self.refresh_accounts()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить аккаунт: {e}")
    
    # Методы для работы с видео
    def select_video_input_folder(self):
        """Выбор папки с исходными видео"""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Выберите папку с исходными видео")
        if folder:
            self.video_input_entry.delete(0, tk.END)
            self.video_input_entry.insert(0, folder)
    
    def select_video_output_folder(self):
        """Выбор папки для готовых видео"""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Выберите папку для готовых видео")
        if folder:
            self.video_output_entry.delete(0, tk.END)
            self.video_output_entry.insert(0, folder)
    
    def start_video_creation(self):
        """Запуск создания видео"""
        input_folder = self.video_input_entry.get().strip()
        output_folder = self.video_output_entry.get().strip()

        try:
            videos_per_group = int(self.videos_per_group.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Укажите корректное количество видео в группе")
            return

        if not input_folder or not os.path.exists(input_folder):
            messagebox.showerror("Ошибка", "Папка с исходными видео не найдена!")
            return

        if not output_folder:
            messagebox.showerror("Ошибка", "Укажите папку для готовых видео")
            return
        
        self.video_start_btn.config(state=tk.DISABLED)
        self.video_stop_btn.config(state=tk.NORMAL)
        self.video_progress.config(mode='determinate', value=0)
        self.video_status_label.config(text="Создание видео...")
        self.video_stop_flag = False
        self.set_status("Создание видео...")
        
        self.video_log.config(state=tk.NORMAL)
        self.video_log.delete("1.0", tk.END)
        self.video_log.insert("1.0", "Запуск создания видео...\n")
        self.video_log.config(state=tk.DISABLED)
        
        self.video_thread = threading.Thread(
            target=self._video_creation_thread,
            args=(input_folder, output_folder, videos_per_group),
            daemon=True
        )
        self.video_thread.start()
    
    def _video_creation_thread(self, input_folder, output_folder, videos_per_group):
        """Поток для создания видео"""
        try:
            self.video_creator.create_videos(
                input_folder, output_folder, videos_per_group,
                self._video_log_callback, self._video_progress_callback
            )
            self.root.after(0, self._video_creation_complete)
        except Exception as e:
            self.root.after(0, self._video_creation_error, str(e))
    
    def _video_log_callback(self, message):
        """Callback для лога видео"""
        self.root.after(0, lambda: self._append_video_log(message))
    
    def _append_video_log(self, message):
        """Добавление сообщения в лог видео"""
        self.video_log.config(state=tk.NORMAL)
        self.video_log.insert(tk.END, message + "\n")
        self.video_log.see(tk.END)
        self.video_log.config(state=tk.DISABLED)
    
    def _video_progress_callback(self, current, total):
        """Callback для прогресса видео"""
        self.root.after(0, lambda: self._update_video_progress(current, total))
    
    def _update_video_progress(self, current, total):
        """Обновление прогресса видео"""
        if total > 0:
            self.video_progress.config(mode='determinate', maximum=total, value=current)
            self.video_status_label.config(text=f"Обработано: {current}/{total}")
    
    def _video_creation_complete(self):
        """Завершение создания видео"""
        self.video_progress.config(mode='determinate', value=100)
        self.video_status_label.config(text="Готово!")
        self.video_start_btn.config(state=tk.NORMAL)
        self.video_stop_btn.config(state=tk.DISABLED)
        self.set_status("Создание видео завершено")
        messagebox.showinfo("Успех", "Создание видео завершено!")
    
    def _video_creation_error(self, error_msg):
        """Ошибка при создании видео"""
        self.video_status_label.config(text="Ошибка")
        self.video_start_btn.config(state=tk.NORMAL)
        self.video_stop_btn.config(state=tk.DISABLED)
        self.set_status("Ошибка создания видео")
        self._append_video_log(f"❌ Ошибка: {error_msg}")
        messagebox.showerror("Ошибка", f"Ошибка при создании видео:\n{error_msg}")
    
    def stop_video_creation(self):
        """Остановка создания видео"""
        self.video_stop_flag = True
        self.video_creator.stop()
        self._append_video_log("⏹️ Остановка создания видео...")
    
    # Методы для работы с прокси
    def _validate_date(self, date_str, field_name):
        """Проверка формата даты ДД.ММ.ГГГГ"""
        if not date_str.strip():
            return True
        try:
            datetime.strptime(date_str.strip(), "%d.%m.%Y")
            return True
        except ValueError:
            messagebox.showerror("Ошибка", f"{field_name}: неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return False

    def _notify_if_expiring(self, notif_type, message):
        """Добавляет уведомление только если такого ещё не было за последние 24 часа"""
        if not self.database.has_recent_notification(notif_type, message, hours=24):
            self.database.add_notification(notif_type, message)

    def save_proxy_info(self):
        """Сохранение информации о прокси"""
        purchase = self.proxy_purchase_entry.get().strip()
        expiry = self.proxy_expiry_entry.get().strip()
        if not self._validate_date(purchase, "Дата покупки прокси"):
            return
        if not self._validate_date(expiry, "Дата окончания прокси"):
            return

        if 'proxy' not in self.config:
            self.config['proxy'] = {}
        
        self.config['proxy']['purchase_date'] = purchase
        self.config['proxy']['expiry_date'] = expiry
        self.save_config()
        self.update_proxy_status()
        self.set_status("Настройки прокси сохранены")
        messagebox.showinfo("Успех", "Информация о прокси сохранена")
    
    def save_server_info(self):
        """Сохранение информации о сервере"""
        purchase = self.server_purchase_entry.get().strip()
        expiry = self.server_expiry_entry.get().strip()
        if not self._validate_date(purchase, "Дата покупки сервера"):
            return
        if not self._validate_date(expiry, "Дата окончания сервера"):
            return

        if 'server' not in self.config:
            self.config['server'] = {}
        
        self.config['server']['purchase_date'] = purchase
        self.config['server']['expiry_date'] = expiry
        self.save_config()
        self.update_proxy_status()
        self.set_status("Настройки сервера сохранены")
        messagebox.showinfo("Успех", "Информация о сервере сохранена")
    
    def update_proxy_status(self):
        """Обновление статуса прокси и сервера"""
        self.proxy_status_text.config(state=tk.NORMAL)
        self.proxy_status_text.delete("1.0", tk.END)
        
        proxy_info = self.config.get('proxy', {})
        server_info = self.config.get('server', {})
        
        status = "🌐 ИНФОРМАЦИЯ О ПРОКСИ И СЕРВЕРЕ\n\n"
        
        # Прокси
        status += "📡 ПРОКСИ:\n"
        purchase_date = proxy_info.get('purchase_date', 'Не указана')
        expiry_date = proxy_info.get('expiry_date', 'Не указана')
        status += f"   Дата покупки: {purchase_date}\n"
        status += f"   Дата окончания: {expiry_date}\n"
        
        proxy_days_left = None
        if expiry_date and expiry_date != 'Не указана':
            try:
                exp_date = datetime.strptime(expiry_date, "%d.%m.%Y")
                proxy_days_left = (exp_date - datetime.now()).days
                if proxy_days_left > 0:
                    status += f"   ⏰ Осталось дней: {proxy_days_left}\n"
                    if proxy_days_left <= 7:
                        status += f"   ⚠️ ВНИМАНИЕ: Прокси истекает через {proxy_days_left} дней!\n"
                        self._notify_if_expiring(
                            'proxy_expiry', f'Прокси истекает через {proxy_days_left} дней'
                        )
                else:
                    status += f"   ⚠️ Прокси истек!\n"
                    self._notify_if_expiring('proxy_expired', 'Прокси истек!')
            except ValueError:
                status += "   ⚠️ Неверный формат даты окончания\n"
        
        status += "\n🖥️ СЕРВЕР:\n"
        purchase_date = server_info.get('purchase_date', 'Не указана')
        expiry_date = server_info.get('expiry_date', 'Не указана')
        status += f"   Дата покупки: {purchase_date}\n"
        status += f"   Дата окончания: {expiry_date}\n"
        
        server_days_left = None
        if expiry_date and expiry_date != 'Не указана':
            try:
                exp_date = datetime.strptime(expiry_date, "%d.%m.%Y")
                server_days_left = (exp_date - datetime.now()).days
                if server_days_left > 0:
                    status += f"   ⏰ Осталось дней: {server_days_left}\n"
                    # Напоминание за 7 дней
                    if server_days_left <= 7:
                        status += f"   ⚠️ ВНИМАНИЕ: Сервер истекает через {server_days_left} дней!\n"
                        self.database.add_notification('server_expiry', f'Сервер истекает через {server_days_left} дней')
                else:
                    status += f"   ⚠️ Сервер истек!\n"
                    self.database.add_notification('server_expired', 'Сервер истек!')
            except:
                pass
        
        self.proxy_status_text.insert("1.0", status)
        self.proxy_status_text.config(state=tk.DISABLED)
        
        # Проверка уведомлений при обновлении статуса
        self.check_notifications()
    
    # Методы для работы с Telegram ботом
    def save_telegram_settings(self):
        """Сохранение настроек Telegram"""
        self.config['telegram_bot_token'] = self.bot_token_entry.get()
        self.config['telegram_chat_id'] = self.chat_id_entry.get()
        self.save_config()
        messagebox.showinfo("Успех", "Настройки Telegram сохранены")
    
    def start_telegram_bot(self):
        """Запуск Telegram бота"""
        token = self.bot_token_entry.get()
        chat_id = self.chat_id_entry.get()
        
        if not token or not chat_id:
            messagebox.showerror("Ошибка", "Укажите Bot Token и Chat ID!")
            return
        
        self.bot_start_btn.config(state=tk.DISABLED)
        self.bot_stop_btn.config(state=tk.NORMAL)
        
        self.bot_status_text.config(state=tk.NORMAL)
        self.bot_status_text.delete("1.0", tk.END)
        self.bot_status_text.insert("1.0", "Запуск бота...\n")
        self.bot_status_text.config(state=tk.DISABLED)
        
        # Запуск бота в отдельном потоке
        thread = threading.Thread(target=self._telegram_bot_thread, daemon=True)
        thread.start()
    
    def _telegram_bot_thread(self):
        """Поток для работы Telegram бота"""
        try:
            self.telegram_bot.start(self._bot_status_callback)
        except Exception as e:
            self.root.after(0, lambda: self._bot_error(str(e)))
    
    def _bot_status_callback(self, message):
        """Callback для статуса бота"""
        self.root.after(0, lambda: self._append_bot_status(message))
    
    def _append_bot_status(self, message):
        """Добавление сообщения в статус бота"""
        self.bot_status_text.config(state=tk.NORMAL)
        self.bot_status_text.insert(tk.END, message + "\n")
        self.bot_status_text.see(tk.END)
        self.bot_status_text.config(state=tk.DISABLED)
    
    def _bot_error(self, error_msg):
        """Ошибка бота"""
        self._append_bot_status(f"❌ Ошибка: {error_msg}")
        self.bot_start_btn.config(state=tk.NORMAL)
        self.bot_stop_btn.config(state=tk.DISABLED)
        messagebox.showerror("Ошибка", f"Ошибка при запуске бота:\n{error_msg}")
    
    def stop_telegram_bot(self):
        """Остановка Telegram бота"""
        self.telegram_bot.stop()
        self.bot_start_btn.config(state=tk.NORMAL)
        self.bot_stop_btn.config(state=tk.DISABLED)
        self._append_bot_status("⏹️ Бот остановлен")
    
    def send_test_message(self):
        """Отправка тестового сообщения"""
        token = self.bot_token_entry.get()
        chat_id = self.chat_id_entry.get()
        
        if not token or not chat_id:
            messagebox.showerror("Ошибка", "Укажите Bot Token и Chat ID!")
            return
        
        try:
            self.telegram_bot.send_message("🧪 Тестовое сообщение из программы аналитики")
            messagebox.showinfo("Успех", "Тестовое сообщение отправлено!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить сообщение:\n{e}")
    
    def create_modern_button(self, parent, text, command, bg_color, small=False):
        """Создание современной кнопки"""
        if small:
            padx, pady, font_size = 12, 6, 8
        else:
            padx, pady, font_size = 15, 8, 9
        
        btn = tk.Button(parent, text=text, command=command,
                       bg=bg_color, fg='white',
                       font=('Segoe UI', font_size), relief=tk.FLAT,
                       padx=padx, pady=pady, cursor='hand2',
                       activebackground=bg_color, activeforeground='white',
                       bd=0, highlightthickness=0)
        
        # Эффект при наведении
        def on_enter(e):
            btn.config(bg=darken_hex(bg_color))
        
        def on_leave(e):
            btn.config(bg=bg_color)
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def create_modern_toolbar(self):
        """Создание современной панели инструментов"""
        self.toolbar_outer = tk.Frame(self.root, bg=self.colors['bg'], height=65, relief=tk.FLAT)
        self.toolbar_outer.pack(fill=tk.X, padx=0, pady=0, before=self.notebook if hasattr(self, 'notebook') else None)
        self.toolbar_outer.pack_propagate(False)
        
        toolbar_frame = tk.Frame(self.toolbar_outer, bg=self.colors['card_bg'], relief=tk.FLAT)
        toolbar_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Логотип/название слева
        title_frame = tk.Frame(toolbar_frame, bg=self.colors['card_bg'])
        title_frame.pack(side=tk.LEFT, padx=20, pady=15)
        
        title_label = tk.Label(title_frame, text="📊 YouTube Analytics", 
                              bg=self.colors['card_bg'], fg=self.colors['accent'],
                              font=('Segoe UI', 14, 'bold'))
        title_label.pack()
        
        # Группы кнопок справа
        buttons_frame = tk.Frame(toolbar_frame, bg=self.colors['card_bg'])
        buttons_frame.pack(side=tk.RIGHT, padx=15, pady=10)
        
        # Группа: Экспорт
        export_frame = tk.Frame(buttons_frame, bg=self.colors['card_bg'])
        export_frame.pack(side=tk.LEFT, padx=5)
        
        export_btn = tk.Button(export_frame, text="💾 Экспорт", 
                              bg=self.colors['success'], fg='white',
                              font=('Segoe UI', 9), relief=tk.FLAT, padx=15, pady=8,
                              cursor='hand2', command=self.show_export_menu)
        export_btn.pack()
        export_btn.bind('<Enter>', lambda e: export_btn.config(bg='#229954'))
        export_btn.bind('<Leave>', lambda e: export_btn.config(bg=self.colors['success']))
        
        # Группа: Задачи
        tasks_frame = tk.Frame(buttons_frame, bg=self.colors['card_bg'])
        tasks_frame.pack(side=tk.LEFT, padx=5)
        
        tasks_btn = tk.Button(tasks_frame, text="📅 Задачи", 
                             bg=self.colors['accent'], fg='white',
                             font=('Segoe UI', 9), relief=tk.FLAT, padx=15, pady=8,
                             cursor='hand2', command=self.show_tasks_menu)
        tasks_btn.pack()
        tasks_btn.bind('<Enter>', lambda e: tasks_btn.config(bg=self.colors['accent_hover']))
        tasks_btn.bind('<Leave>', lambda e: tasks_btn.config(bg=self.colors['accent']))
        
        # Группа: Тема
        theme_frame = tk.Frame(buttons_frame, bg=self.colors['card_bg'])
        theme_frame.pack(side=tk.LEFT, padx=5)
        
        theme_btn = tk.Button(theme_frame, text="🎨 Тема", 
                             bg=self.colors['warning'], fg='white',
                             font=('Segoe UI', 9), relief=tk.FLAT, padx=15, pady=8,
                             cursor='hand2', command=self.show_theme_menu)
        theme_btn.pack()
        theme_btn.bind('<Enter>', lambda e: theme_btn.config(bg='#e67e22'))
        theme_btn.bind('<Leave>', lambda e: theme_btn.config(bg=self.colors['warning']))
        
        # Группа: Справка
        help_frame = tk.Frame(buttons_frame, bg=self.colors['card_bg'])
        help_frame.pack(side=tk.LEFT, padx=5)
        
        help_btn = tk.Button(help_frame, text="ℹ️ О программе", 
                            bg=self.colors['text_secondary'], fg='white',
                            font=('Segoe UI', 9), relief=tk.FLAT, padx=15, pady=8,
                            cursor='hand2', command=self.show_about)
        help_btn.pack()
        help_btn.bind('<Enter>', lambda e: help_btn.config(bg='#5d6d7e'))
        help_btn.bind('<Leave>', lambda e: help_btn.config(bg=self.colors['text_secondary']))
        
        # Разделитель с закруглением
        separator = tk.Frame(self.toolbar_outer, bg=self.colors['border'], height=1)
        separator.pack(side=tk.BOTTOM, fill=tk.X, padx=10)
    
    def show_export_menu(self):
        """Показать меню экспорта"""
        menu_window = tk.Toplevel(self.root)
        menu_window.title("Экспорт данных")
        menu_window.geometry("300x200")
        menu_window.configure(bg=self.colors['bg'])
        menu_window.transient(self.root)
        menu_window.grab_set()
        
        # Центрирование окна
        menu_window.update_idletasks()
        x = (menu_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (menu_window.winfo_screenheight() // 2) - (200 // 2)
        menu_window.geometry(f"300x200+{x}+{y}")
        
        tk.Label(menu_window, text="Экспорт данных", 
                bg=self.colors['bg'], fg=self.colors['fg'],
                font=('Segoe UI', 12, 'bold')).pack(pady=15)
        
        buttons_frame = tk.Frame(menu_window, bg=self.colors['bg'])
        buttons_frame.pack(pady=10)
        
        tk.Button(buttons_frame, text="📊 Экспорт статистики", 
                 bg=self.colors['accent'], fg='white', relief=tk.FLAT,
                 padx=20, pady=10, cursor='hand2',
                 command=lambda: [self.export_stats_menu(), menu_window.destroy()]).pack(pady=5, fill=tk.X)
        
        tk.Button(buttons_frame, text="👤 Экспорт аккаунтов", 
                 bg=self.colors['accent'], fg='white', relief=tk.FLAT,
                 padx=20, pady=10, cursor='hand2',
                 command=lambda: [self.export_accounts_menu(), menu_window.destroy()]).pack(pady=5, fill=tk.X)
        
        tk.Button(buttons_frame, text="📄 Генерация отчета", 
                 bg=self.colors['success'], fg='white', relief=tk.FLAT,
                 padx=20, pady=10, cursor='hand2',
                 command=lambda: [self.generate_report(), menu_window.destroy()]).pack(pady=5, fill=tk.X)
        
        tk.Button(buttons_frame, text="Отмена", 
                 bg=self.colors['text_secondary'], fg='white', relief=tk.FLAT,
                 padx=20, pady=8, cursor='hand2',
                 command=menu_window.destroy).pack(pady=5, fill=tk.X)
    
    def show_tasks_menu(self):
        """Показать меню задач"""
        menu_window = tk.Toplevel(self.root)
        menu_window.title("Задачи")
        menu_window.geometry("300x150")
        menu_window.configure(bg=self.colors['bg'])
        menu_window.transient(self.root)
        menu_window.grab_set()
        
        # Центрирование окна
        menu_window.update_idletasks()
        x = (menu_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (menu_window.winfo_screenheight() // 2) - (150 // 2)
        menu_window.geometry(f"300x150+{x}+{y}")
        
        tk.Label(menu_window, text="Задачи и история", 
                bg=self.colors['bg'], fg=self.colors['fg'],
                font=('Segoe UI', 12, 'bold')).pack(pady=15)
        
        buttons_frame = tk.Frame(menu_window, bg=self.colors['bg'])
        buttons_frame.pack(pady=10)
        
        tk.Button(buttons_frame, text="📅 Планировщик задач", 
                 bg=self.colors['accent'], fg='white', relief=tk.FLAT,
                 padx=20, pady=10, cursor='hand2',
                 command=lambda: [self.open_scheduler(), menu_window.destroy()]).pack(pady=5, fill=tk.X)
        
        tk.Button(buttons_frame, text="📋 История операций", 
                 bg=self.colors['accent'], fg='white', relief=tk.FLAT,
                 padx=20, pady=10, cursor='hand2',
                 command=lambda: [self.open_operations_log(), menu_window.destroy()]).pack(pady=5, fill=tk.X)
        
        tk.Button(buttons_frame, text="Отмена", 
                 bg=self.colors['text_secondary'], fg='white', relief=tk.FLAT,
                 padx=20, pady=8, cursor='hand2',
                 command=menu_window.destroy).pack(pady=5, fill=tk.X)
    
    def show_theme_menu(self):
        """Показать меню темы"""
        menu_window = tk.Toplevel(self.root)
        menu_window.title("Тема оформления")
        menu_window.geometry("300x150")
        menu_window.configure(bg=self.colors['bg'])
        menu_window.transient(self.root)
        menu_window.grab_set()
        
        # Центрирование окна
        menu_window.update_idletasks()
        x = (menu_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (menu_window.winfo_screenheight() // 2) - (150 // 2)
        menu_window.geometry(f"300x150+{x}+{y}")
        
        tk.Label(menu_window, text="Выберите тему", 
                bg=self.colors['bg'], fg=self.colors['fg'],
                font=('Segoe UI', 12, 'bold')).pack(pady=15)
        
        buttons_frame = tk.Frame(menu_window, bg=self.colors['bg'])
        buttons_frame.pack(pady=10)
        
        tk.Button(buttons_frame, text="☀️ Светлая тема", 
                 bg='#ecf0f1', fg=self.colors['fg'], relief=tk.FLAT,
                 padx=20, pady=10, cursor='hand2',
                 command=lambda: [self.change_theme('light'), menu_window.destroy()]).pack(pady=5, fill=tk.X)
        
        tk.Button(buttons_frame, text="🌙 Темная тема", 
                 bg='#34495e', fg='white', relief=tk.FLAT,
                 padx=20, pady=10, cursor='hand2',
                 command=lambda: [self.change_theme('dark'), menu_window.destroy()]).pack(pady=5, fill=tk.X)
        
        tk.Button(buttons_frame, text="Отмена", 
                 bg=self.colors['text_secondary'], fg='white', relief=tk.FLAT,
                 padx=20, pady=8, cursor='hand2',
                 command=menu_window.destroy).pack(pady=5, fill=tk.X)
    
    def open_settings(self):
        """Открытие окна настроек"""
        messagebox.showinfo("Настройки", "Настройки доступны в соответствующих вкладках")
    
    # Новые методы для экспорта и фильтрации
    def filter_stats_table(self, event=None):
        """Фильтрация таблицы статистики"""
        search_text = self.stats_search_entry.get().lower()
        
        # Очистка таблицы
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        
        # Фильтрация и добавление результатов
        for result in self.current_stats_results:
            if 'error' not in result:
                channel_name = result.get('channel_name', '').lower()
                url = result.get('url', '').lower()
                
                if search_text in channel_name or search_text in url:
                    self.stats_tree.insert("", tk.END, values=(
                        result.get('channel_name', 'Неизвестно'),
                        result.get('subscribers', '0'),
                        result.get('total_views', '0'),
                        result.get('videos_count', '0'),
                        "✅"
                    ))
            else:
                url = result.get('url', '').lower()
                if search_text in url:
                    self.stats_tree.insert("", tk.END, values=(
                        result.get('url', 'Неизвестно'),
                        "-",
                        "-",
                        "-",
                        f"❌ {result.get('error', 'Ошибка')}"
                    ))
    
    def reset_stats_filter(self):
        """Сброс фильтра статистики"""
        self.stats_search_entry.delete(0, tk.END)
        self._update_stats_ui(self.current_stats_results)
    
    def export_stats_menu(self):
        """Меню экспорта статистики"""
        if not self.current_stats_results:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта. Сначала выполните парсинг статистики.")
            return
        
        from tkinter import filedialog
        
        export_window = tk.Toplevel(self.root)
        export_window.title("Экспорт статистики")
        export_window.geometry("400x200")
        
        ttk.Label(export_window, text="Выберите формат экспорта:").pack(pady=10)
        
        ttk.Button(export_window, text="📄 Экспорт в CSV", 
                  command=lambda: self._export_stats('csv', export_window)).pack(pady=5, padx=20, fill=tk.X)
        ttk.Button(export_window, text="📊 Экспорт в Excel", 
                  command=lambda: self._export_stats('excel', export_window)).pack(pady=5, padx=20, fill=tk.X)
        ttk.Button(export_window, text="📋 Экспорт в JSON", 
                  command=lambda: self._export_stats('json', export_window)).pack(pady=5, padx=20, fill=tk.X)
        ttk.Button(export_window, text="Отмена", 
                  command=export_window.destroy).pack(pady=5, padx=20, fill=tk.X)
    
    def _export_stats(self, format_type, window):
        """Экспорт статистики в выбранный формат"""
        from tkinter import filedialog
        
        try:
            if format_type == 'csv':
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
                )
                if filename:
                    self.export_manager.export_stats_to_csv(self.current_stats_results, filename)
                    messagebox.showinfo("Успех", f"Статистика экспортирована в {filename}")
            elif format_type == 'excel':
                filename = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
                )
                if filename:
                    self.export_manager.export_stats_to_excel(self.current_stats_results, filename)
                    messagebox.showinfo("Успех", f"Статистика экспортирована в {filename}")
            elif format_type == 'json':
                filename = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
                if filename:
                    self.export_manager.export_stats_to_json(self.current_stats_results, filename)
                    messagebox.showinfo("Успех", f"Статистика экспортирована в {filename}")
            
            window.destroy()
            self.database.log_operation('export', f'Экспорт статистики в {format_type}')
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {e}")
    
    def export_accounts_menu(self):
        """Меню экспорта аккаунтов"""
        if not self.current_accounts_data:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта. Сначала обновите список аккаунтов.")
            return
        
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.export_manager.export_accounts_to_csv(self.current_accounts_data, filename)
                messagebox.showinfo("Успех", f"Аккаунты экспортированы в {filename}")
                self.database.log_operation('export', 'Экспорт аккаунтов')
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при экспорте: {e}")
    
    def generate_report(self):
        """Генерация отчета"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.report_generator.generate_stats_report(
                    self.current_stats_results,
                    self.current_accounts_data,
                    filename
                )
                messagebox.showinfo("Успех", f"Отчет создан: {filename}")
                self.database.log_operation('report', 'Генерация отчета')
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при создании отчета: {e}")
    
    def show_stats_history(self):
        """Показать историю статистики"""
        history_window = tk.Toplevel(self.root)
        history_window.title("История статистики")
        history_window.geometry("800x600")
        
        ttk.Label(history_window, text="История статистики каналов").pack(pady=10)
        
        # Таблица истории
        columns = ("Дата", "Канал", "Подписчики", "Просмотры", "Видео")
        history_tree = ttk.Treeview(history_window, columns=columns, show="headings", height=20)
        
        for col in columns:
            history_tree.heading(col, text=col)
            history_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(history_window, orient=tk.VERTICAL, command=history_tree.yview)
        history_tree.configure(yscrollcommand=scrollbar.set)
        
        history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Загрузка истории
        try:
            history = self.database.get_all_channels_history(30)
            for record in history:
                history_tree.insert("", tk.END, values=(
                    record[6][:10] if record[6] else '',  # Дата
                    record[2] or '',  # Название канала
                    record[3] or 0,  # Подписчики
                    record[4] or 0,  # Просмотры
                    record[5] or 0   # Видео
                ))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке истории: {e}")
    
    def change_theme(self, theme_name):
        """Изменение темы оформления"""
        self.config['theme'] = theme_name
        self.save_config()
        
        # Получаем цвета темы
        theme = self.theme_manager.themes[theme_name]
        
        # Обновляем цвета в приложении
        self.colors = theme.copy()
        
        # Применяем тему через theme_manager
        self.theme_manager.apply_theme(self.root, theme_name)
        
        # Обновляем стили ttk
        self.setup_ttk_styles()
        
        # Обновляем все элементы интерфейса
        self.update_ui_colors(theme)
        
        # Пересоздаем тулбар с новыми цветами
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.destroy()
        
        self.create_modern_toolbar()
        
        messagebox.showinfo("Успех", f"Тема изменена на: {'Светлую' if theme_name == 'light' else 'Темную'}")
    
    def update_ui_colors(self, theme):
        """Обновление цветов всех элементов интерфейса"""
        # Обновляем стили ttk
        style = ttk.Style()
        style.configure('TFrame', background=theme['bg'], relief=tk.FLAT)
        style.configure('TLabel', background=theme['bg'], foreground=theme['fg'])
        style.configure('TLabelFrame', background=theme['bg'], foreground=theme['fg'])
        style.configure('TNotebook', background=theme['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=theme['card_bg'], foreground=theme['fg'],
                       padding=[25, 12], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', 
                 background=[('selected', theme['accent']), ('active', theme['hover_bg'])],
                 foreground=[('selected', 'white'), ('active', theme['accent'])])
        style.configure('TEntry', fieldbackground=theme['card_bg'], foreground=theme['fg'],
                       bordercolor=theme['border'])
        style.configure('TText', background=theme['card_bg'], foreground=theme['fg'])
        style.configure('Treeview', background=theme['card_bg'], foreground=theme['fg'],
                       fieldbackground=theme['card_bg'], bordercolor=theme['border'])
        style.configure('Treeview.Heading', background=theme['hover_bg'], foreground=theme['fg'],
                       relief=tk.FLAT)
        style.map('Treeview', 
                 background=[('selected', theme['accent'])],
                 foreground=[('selected', 'white')])
        style.configure('TScrollbar', background=theme['border'], troughcolor=theme['bg'],
                       arrowcolor=theme['text_secondary'])
        
        # Обновляем корневой виджет
        self.root.configure(bg=theme['bg'])
        
        # Рекурсивно обновляем все виджеты (более агрессивно)
        self._update_widget_colors_recursive(self.root, theme)
    
    def _update_widget_colors_recursive(self, widget, theme):
        """Рекурсивное обновление цветов виджетов для темной темы"""
        try:
            widget_type = widget.winfo_class()
            
            # Получаем текущие цвета для сравнения
            try:
                current_bg = widget.cget('bg')
                current_fg = widget.cget('fg')
            except:
                current_bg = ''
                current_fg = ''
            
            # Цветные заголовки и специальные элементы, которые не нужно менять
            protected_colors = [
                theme.get('accent', '#0d6efd'),
                theme.get('success', '#198754'),
                theme.get('warning', '#ffc107'),
                theme.get('danger', '#dc3545'),
                '#ffffff',  # Белый текст на цветных кнопках
                'white'     # Альтернативное написание
            ]
            
            # Светлые цвета, которые нужно заменить на темные
            light_colors = ['#ffffff', '#f8f9fa', '#f5f5f5', '#e9ecef', '#dee2e6', '#ffffff']
            # Темные цвета карточек
            dark_card_colors = ['#2d2d2d', '#3a3a3a']
            
            if widget_type in ['Text', 'ScrolledText']:
                widget.configure(bg=theme['card_bg'], fg=theme['fg'],
                               selectbackground=theme['accent'],
                               selectforeground='white',
                               insertbackground=theme['fg'])
            elif widget_type == 'Entry':
                widget.configure(bg=theme['card_bg'], fg=theme['fg'],
                               insertbackground=theme['fg'],
                               highlightbackground=theme['border'],
                               highlightcolor=theme['accent'])
            elif widget_type == 'Listbox':
                widget.configure(bg=theme['card_bg'], fg=theme['fg'],
                               selectbackground=theme['accent'],
                               selectforeground='white',
                               highlightbackground=theme['border'],
                               highlightcolor=theme['accent'])
            elif widget_type == 'Frame':
                # Более агрессивное обновление фреймов
                if current_bg not in protected_colors:
                    # Если это светлый цвет или карточка - меняем на card_bg
                    if current_bg in light_colors or current_bg in dark_card_colors:
                        widget.configure(bg=theme['card_bg'])
                    # Если это фон приложения - меняем на bg
                    elif current_bg in ['#1a1a1a', '#f8f9fa', '#f5f5f5'] or current_bg == self.colors.get('bg', ''):
                        widget.configure(bg=theme['bg'])
                    # Если это граница - меняем на border
                    elif current_bg in ['#dee2e6', '#404040', '#d0d0d0', '#3a3a3a']:
                        widget.configure(bg=theme['border'])
            elif widget_type == 'Label':
                # Обновляем все лейблы, кроме цветных заголовков
                if current_bg not in protected_colors:
                    # Всегда обновляем цвет текста
                    if current_fg not in ['white', '#ffffff'] or current_bg in protected_colors:
                        widget.configure(fg=theme['fg'])
                    # Обновляем фон
                    if current_bg in light_colors or current_bg in dark_card_colors:
                        widget.configure(bg=theme['card_bg'])
                    elif current_bg in ['#1a1a1a', '#f8f9fa', '#f5f5f5'] or current_bg == self.colors.get('bg', ''):
                        widget.configure(bg=theme['bg'])
                    elif current_bg in ['#dee2e6', '#404040']:
                        widget.configure(bg=theme['border'])
            elif widget_type == 'Button':
                # Обновляем только обычные кнопки, не цветные
                if current_bg not in protected_colors:
                    try:
                        # Если кнопка имеет светлый фон - обновляем
                        if current_bg in light_colors or current_bg in ['#f0f0f0', '#e9ecef']:
                            widget.configure(bg=theme['button_bg'], fg=theme['button_fg'])
                    except:
                        pass
        except Exception as e:
            pass
        
        # Обновляем дочерние виджеты
        for child in widget.winfo_children():
            try:
                self._update_widget_colors_recursive(child, theme)
            except:
                continue
    
    def open_scheduler(self):
        """Открытие окна планировщика задач"""
        scheduler_window = tk.Toplevel(self.root)
        scheduler_window.title("Планировщик задач")
        scheduler_window.geometry("600x500")
        
        ttk.Label(scheduler_window, text="Планировщик задач").pack(pady=10)
        
        # Список задач
        tasks_frame = ttk.LabelFrame(scheduler_window, text="Запланированные задачи")
        tasks_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tasks_listbox = tk.Listbox(tasks_frame, height=15)
        tasks_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки управления
        buttons_frame = ttk.Frame(scheduler_window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(buttons_frame, text="➕ Добавить задачу", 
                  command=lambda: self._add_scheduled_task(scheduler_window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🗑️ Удалить задачу", 
                  command=lambda: self._remove_scheduled_task(tasks_listbox)).pack(side=tk.LEFT, padx=5)
        
        # Загрузка задач
        tasks = self.scheduler.get_tasks_list()
        for task_id in tasks:
            tasks_listbox.insert(tk.END, task_id)
    
    def _add_scheduled_task(self, parent):
        """Добавление новой задачи в планировщик"""
        task_window = tk.Toplevel(parent)
        task_window.title("Добавить задачу")
        task_window.geometry("400x300")
        
        ttk.Label(task_window, text="Тип задачи:").pack(pady=5)
        task_type = ttk.Combobox(task_window, values=["Парсинг статистики", "Создание видео"], state="readonly")
        task_type.pack(pady=5, padx=20, fill=tk.X)
        task_type.set("Парсинг статистики")
        
        ttk.Label(task_window, text="Время выполнения (ЧЧ:ММ):").pack(pady=5)
        time_entry = ttk.Entry(task_window)
        time_entry.pack(pady=5, padx=20, fill=tk.X)
        time_entry.insert(0, "09:00")
        
        def save_task():
            task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            schedule_time = time_entry.get()
            
            if task_type.get() == "Парсинг статистики":
                self.scheduler.add_task(task_id, 'daily', schedule_time, self.run_stats_parser)
            elif task_type.get() == "Создание видео":
                # Здесь можно добавить логику для создания видео
                pass
            
            messagebox.showinfo("Успех", "Задача добавлена")
            task_window.destroy()
        
        ttk.Button(task_window, text="Сохранить", command=save_task).pack(pady=10)
    
    def _remove_scheduled_task(self, listbox):
        """Удаление задачи из планировщика"""
        selection = listbox.curselection()
        if selection:
            task_id = listbox.get(selection[0])
            self.scheduler.remove_task(task_id)
            listbox.delete(selection[0])
            messagebox.showinfo("Успех", "Задача удалена")
    
    def open_operations_log(self):
        """Открытие лога операций"""
        log_window = tk.Toplevel(self.root)
        log_window.title("История операций")
        log_window.geometry("800x600")
        
        ttk.Label(log_window, text="История операций").pack(pady=10)
        
        # Таблица лога
        columns = ("Дата", "Тип операции", "Описание")
        log_tree = ttk.Treeview(log_window, columns=columns, show="headings", height=25)
        
        for col in columns:
            log_tree.heading(col, text=col)
            log_tree.column(col, width=200)
        
        scrollbar = ttk.Scrollbar(log_window, orient=tk.VERTICAL, command=log_tree.yview)
        log_tree.configure(yscrollcommand=scrollbar.set)
        
        log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Загрузка лога
        try:
            operations = self.database.get_operations_log(100)
            for op in operations:
                log_tree.insert("", tk.END, values=(
                    op[3][:19] if op[3] else '',  # Дата
                    op[1] or '',  # Тип
                    op[2] or ''   # Описание
                ))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке лога: {e}")
    
    def check_notifications(self):
        """Проверка и отображение уведомлений"""
        try:
            notifications = self.database.get_unread_notifications()
            if notifications:
                notification_text = "У вас есть непрочитанные уведомления:\n\n"
                for notif in notifications[:5]:  # Показываем первые 5
                    notification_text += f"• {notif[2]}\n"
                
                if len(notifications) > 5:
                    notification_text += f"\n... и еще {len(notifications) - 5} уведомлений"
                
                result = messagebox.showwarning("Уведомления", notification_text)
                # Можно отметить как прочитанные, если нужно
        except Exception as e:
            print(f"Ошибка при проверке уведомлений: {e}")
    
    def show_about(self):
        """Показать информацию о программе"""
        about_text = """YouTube Analytics - Программа для аналитики

Версия: 2.0

Возможности:
• Парсинг статистики YouTube каналов
• Управление аккаунтами
• Создание видео
• Управление прокси и сервером
• Telegram бот
• История статистики
• Экспорт данных
• Планировщик задач
• Темная тема

© 2024"""
        messagebox.showinfo("О программе", about_text)
    
    def open_bulk_operations(self):
        """Открытие окна массовых операций"""
        bulk_window = tk.Toplevel(self.root)
        bulk_window.title("Массовые операции")
        bulk_window.geometry("500x400")
        
        ttk.Label(bulk_window, text="Выберите операцию:").pack(pady=10)
        
        operations_frame = ttk.Frame(bulk_window)
        operations_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        ttk.Button(operations_frame, text="🗑️ Массовое удаление", 
                  command=lambda: self._bulk_delete_accounts(bulk_window)).pack(pady=5, fill=tk.X)
        ttk.Button(operations_frame, text="📋 Экспорт выбранных", 
                  command=lambda: self._bulk_export_accounts(bulk_window)).pack(pady=5, fill=tk.X)
        ttk.Button(operations_frame, text="🏷️ Добавить тег к выбранным", 
                  command=lambda: self._bulk_add_tag(bulk_window)).pack(pady=5, fill=tk.X)
        
        ttk.Label(bulk_window, text="Выберите аккаунты в таблице, удерживая Ctrl или Shift").pack(pady=10)
    
    def _bulk_delete_accounts(self, parent):
        """Массовое удаление аккаунтов"""
        selections = self.accounts_tree.selection()
        if not selections:
            messagebox.showwarning("Предупреждение", "Выберите аккаунты для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить {len(selections)} аккаунтов?\n\nЭто действие нельзя отменить!"):
            deleted = 0
            errors = 0
            
            for selection in selections:
                item = self.accounts_tree.item(selection)
                values = item['values']
                account_name = values[0]
                folder_display = values[1]
                
                # Находим полный путь
                folders = self.config.get('accounts_folders', [])
                account_path = None
                
                for folder in folders:
                    if os.path.basename(folder) == folder_display or folder == folder_display:
                        account_path = os.path.join(folder, account_name)
                        if os.path.exists(account_path):
                            break
                
                if account_path and os.path.exists(account_path):
                    try:
                        import shutil
                        shutil.rmtree(account_path)
                        deleted += 1
                    except Exception as e:
                        errors += 1
                        print(f"Ошибка при удалении {account_name}: {e}")
            
            messagebox.showinfo("Результат", f"Удалено: {deleted}\nОшибок: {errors}")
            self.refresh_accounts()
            self.database.log_operation('bulk_delete', f'Массовое удаление: {deleted} аккаунтов')
            parent.destroy()
    
    def _bulk_export_accounts(self, parent):
        """Массовый экспорт аккаунтов"""
        selections = self.accounts_tree.selection()
        if not selections:
            messagebox.showwarning("Предупреждение", "Выберите аккаунты для экспорта")
            return
        
        selected_accounts = []
        for selection in selections:
            item = self.accounts_tree.item(selection)
            values = item['values']
            # Находим аккаунт в данных
            for account in self.current_accounts_data:
                if account['name'] == values[0]:
                    selected_accounts.append(account)
                    break
        
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.export_manager.export_accounts_to_csv(selected_accounts, filename)
                messagebox.showinfo("Успех", f"Экспортировано {len(selected_accounts)} аккаунтов")
                self.database.log_operation('bulk_export', f'Массовый экспорт: {len(selected_accounts)} аккаунтов')
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при экспорте: {e}")
        
        parent.destroy()
    
    def _bulk_add_tag(self, parent):
        """Массовое добавление тега"""
        selections = self.accounts_tree.selection()
        if not selections:
            messagebox.showwarning("Предупреждение", "Выберите аккаунты")
            return
        
        tag = simpledialog.askstring("Тег", "Введите тег:")
        if tag:
            added = 0
            for selection in selections:
                item = self.accounts_tree.item(selection)
                values = item['values']
                account_name = values[0]
                folder_display = values[1]
                
                # Находим полный путь к папке
                folders = self.config.get('accounts_folders', [])
                for folder in folders:
                    if os.path.basename(folder) == folder_display or folder == folder_display:
                        self.database.add_account_tag(account_name, folder, tag)
                        added += 1
                        break
            
            messagebox.showinfo("Успех", f"Тег '{tag}' добавлен к {added} аккаунтам")
            self.database.log_operation('bulk_tag', f'Массовое добавление тега: {tag}')
        
        parent.destroy()
    
    def manage_account_tags(self):
        """Управление тегами аккаунтов"""
        selection = self.accounts_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите аккаунт")
            return
        
        item = self.accounts_tree.item(selection[0])
        values = item['values']
        account_name = values[0]
        folder_display = values[1]
        
        # Находим полный путь к папке
        folders = self.config.get('accounts_folders', [])
        account_folder = None
        for folder in folders:
            if os.path.basename(folder) == folder_display or folder == folder_display:
                account_folder = folder
                break
        
        if not account_folder:
            messagebox.showerror("Ошибка", "Не удалось найти папку аккаунта")
            return
        
        tags_window = tk.Toplevel(self.root)
        tags_window.title(f"Теги аккаунта: {account_name}")
        tags_window.geometry("400x300")
        
        ttk.Label(tags_window, text=f"Теги для: {account_name}").pack(pady=10)
        
        # Список тегов
        tags_listbox = tk.Listbox(tags_window, height=10)
        tags_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Загрузка тегов
        tags = self.database.get_account_tags(account_name, account_folder)
        for tag in tags:
            tags_listbox.insert(tk.END, tag)
        
        # Кнопки управления
        buttons_frame = ttk.Frame(tags_window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def add_tag():
            tag = tk.simpledialog.askstring("Добавить тег", "Введите тег:")
            if tag:
                self.database.add_account_tag(account_name, account_folder, tag)
                tags_listbox.insert(tk.END, tag)
        
        def remove_tag():
            selection = tags_listbox.curselection()
            if selection:
                tag = tags_listbox.get(selection[0])
                self.database.remove_account_tag(account_name, account_folder, tag)
                tags_listbox.delete(selection[0])
        
        ttk.Button(buttons_frame, text="➕ Добавить", command=add_tag).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="➖ Удалить", command=remove_tag).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Закрыть", command=tags_window.destroy).pack(side=tk.LEFT, padx=5)

def main():
    root = tk.Tk()
    app = AnalyticsApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
