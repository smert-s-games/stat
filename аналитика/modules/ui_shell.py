"""
Современный layout в стиле web-dashboard:
верхняя шапка + левый сайдбар + контент (вкладки notebook скрыты).
"""
import tkinter as tk
from tkinter import ttk


NAV_ITEMS = [
    ("🏠", "Главная", 0),
    ("📊", "Статистика", 1),
    ("👤", "Аккаунты", 2),
    ("🎬", "Видео", 3),
    ("🌐", "Прокси", 4),
    ("📱", "Telegram", 5),
]


def create_ui(self):
    """Полный UI: header + sidebar + notebook без видимых табов."""
    style = ttk.Style()
    style.theme_use('clam')

    self.init_colors()
    self.setup_ttk_styles()
    self.root.configure(bg=self.colors['bg'])

    self._build_app_header()

    body = tk.Frame(self.root, bg=self.colors['bg'])
    body.pack(fill=tk.BOTH, expand=True)
    self._ui_body = body

    self._build_sidebar(body)

    content_wrap = tk.Frame(body, bg=self.colors['bg'])
    content_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    self._content_wrap = content_wrap

    self.notebook = ttk.Notebook(content_wrap)
    self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
    try:
        style.layout('TNotebook.Tab', [])
    except Exception:
        pass
    style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
    style.configure('TNotebook.Tab', width=0, height=0)

    self.create_stats_tab()
    self.create_accounts_tab()
    self.create_video_tab()
    self.create_proxy_tab()
    self.create_telegram_tab()

    self.create_status_bar()

    self.toolbar_outer = None
    self._sidebar_select(0)


def _build_app_header(self):
    c = self.colors
    header = tk.Frame(self.root, bg=c.get('toolbar_bg', c['card_bg']), height=56)
    header.pack(fill=tk.X, side=tk.TOP)
    header.pack_propagate(False)
    self._app_header = header

    tk.Frame(header, bg=c['border'], height=1).pack(side=tk.BOTTOM, fill=tk.X)

    inner = tk.Frame(header, bg=c.get('toolbar_bg', c['card_bg']))
    inner.pack(fill=tk.BOTH, expand=True, padx=16)

    logo = tk.Frame(inner, bg=c.get('toolbar_bg', c['card_bg']))
    logo.pack(side=tk.LEFT)
    tk.Label(
        logo, text="YT",
        bg=c['accent'], fg='white',
        font=('Segoe UI', 11, 'bold'),
        padx=8, pady=2
    ).pack(side=tk.LEFT, pady=12)
    tk.Label(
        logo, text="  Analytics",
        bg=c.get('toolbar_bg', c['card_bg']),
        fg=c['fg'],
        font=('Segoe UI', 13, 'bold')
    ).pack(side=tk.LEFT, pady=12)

    right = tk.Frame(inner, bg=c.get('toolbar_bg', c['card_bg']))
    right.pack(side=tk.RIGHT)

    def hbtn(text, cmd, color):
        b = self.create_modern_button(right, text, cmd, color, size='toolbar')
        b.pack(side=tk.LEFT, padx=4, pady=10)
        return b

    hbtn("📊 Статистика", self.run_stats_parser, c['accent'])
    hbtn("💾 Экспорт", self.show_export_menu, c['warning'])
    hbtn("🎨 Тема", self.show_theme_menu, c['text_secondary'])
    hbtn("ℹ️", self.show_about, c['text_secondary'])


def _build_sidebar(self, parent):
    c = self.colors
    side = tk.Frame(parent, bg=c.get('sidebar_bg', c['card_bg']), width=200)
    side.pack(side=tk.LEFT, fill=tk.Y)
    side.pack_propagate(False)
    self._sidebar = side

    tk.Frame(side, bg=c['border'], width=1).pack(side=tk.RIGHT, fill=tk.Y)

    tk.Label(
        side, text="МЕНЮ",
        bg=c.get('sidebar_bg', c['card_bg']),
        fg=c['text_secondary'],
        font=('Segoe UI', 8, 'bold'),
        anchor=tk.W
    ).pack(fill=tk.X, padx=18, pady=(18, 8))

    self._nav_buttons = []
    for i, (icon, label, idx) in enumerate(NAV_ITEMS):
        btn = tk.Frame(side, bg=c.get('sidebar_bg', c['card_bg']), cursor='hand2')
        btn.pack(fill=tk.X, padx=8, pady=2)

        inner = tk.Frame(btn, bg=c.get('sidebar_bg', c['card_bg']))
        inner.pack(fill=tk.X, padx=4, pady=6)

        icon_lbl = tk.Label(
            inner, text=icon,
            bg=c.get('sidebar_bg', c['card_bg']),
            fg=c['fg'], font=('Segoe UI', 12)
        )
        icon_lbl.pack(side=tk.LEFT, padx=(8, 6))

        text_lbl = tk.Label(
            inner, text=label,
            bg=c.get('sidebar_bg', c['card_bg']),
            fg=c['fg'], font=('Segoe UI', 10),
            anchor=tk.W
        )
        text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def make_handlers(frame, icon_l, text_l, index):
            def click(_e=None):
                self._sidebar_select(index)

            def enter(_e):
                if getattr(frame, '_active', False):
                    return
                for w in (frame, icon_l, text_l):
                    try:
                        w.config(bg=c['hover_bg'])
                    except Exception:
                        pass

            def leave(_e):
                if getattr(frame, '_active', False):
                    return
                bg = c.get('sidebar_bg', c['card_bg'])
                for w in (frame, icon_l, text_l):
                    try:
                        w.config(bg=bg)
                    except Exception:
                        pass

            return click, enter, leave

        click, enter, leave = make_handlers(inner, icon_lbl, text_lbl, idx)
        for w in (btn, inner, icon_lbl, text_lbl):
            w.bind('<Button-1>', click)
            w.bind('<Enter>', enter)
            w.bind('<Leave>', leave)

        self._nav_buttons.append({
            'frame': inner,
            'icon': icon_lbl,
            'text': text_lbl,
            'index': idx,
        })

    bottom = tk.Frame(side, bg=c.get('sidebar_bg', c['card_bg']))
    bottom.pack(side=tk.BOTTOM, fill=tk.X, pady=12, padx=8)
    self.create_modern_button(
        bottom, "🎨 Сменить тему", self.show_theme_menu, c['accent'], size='small'
    ).pack(fill=tk.X, padx=4)


def _sidebar_select(self, index):
    c = self.colors
    try:
        self.notebook.select(index)
    except Exception:
        pass

    for item in getattr(self, '_nav_buttons', []):
        active = item['index'] == index
        item['frame']._active = active
        if active:
            bg = c['accent']
            fg = 'white'
        else:
            bg = c.get('sidebar_bg', c['card_bg'])
            fg = c['fg']
        try:
            item['frame'].config(bg=bg)
            item['icon'].config(bg=bg, fg=fg)
            item['text'].config(bg=bg, fg=fg)
        except Exception:
            pass


def create_modern_toolbar(self):
    """Тулбар заменён шапкой — no-op."""
    self.toolbar_outer = tk.Frame(self.root)


def install_ui_shell(app_cls):
    app_cls.create_ui = create_ui
    app_cls._build_app_header = _build_app_header
    app_cls._build_sidebar = _build_sidebar
    app_cls._sidebar_select = _sidebar_select
    app_cls.create_modern_toolbar = create_modern_toolbar
    return app_cls
