"""
Полная дизайн-система приложения: темы, кнопки, тулбар, карточки, ttk-стили.
Подключается через install_ui_design(AnalyticsApp).
"""
import tkinter as tk
from tkinter import ttk, messagebox
from modules.ui_utils import darken_hex


THEMES = {
    'light': {
        'bg': '#eef1f6',
        'fg': '#1a1d26',
        'select_bg': '#4f46e5',
        'select_fg': '#ffffff',
        'entry_bg': '#ffffff',
        'entry_fg': '#1a1d26',
        'button_bg': '#e2e8f0',
        'button_fg': '#1a1d26',
        'frame_bg': '#eef1f6',
        'text_bg': '#ffffff',
        'text_fg': '#1a1d26',
        'card_bg': '#ffffff',
        'border': '#d8dee9',
        'accent': '#4f46e5',
        'accent_hover': '#4338ca',
        'success': '#059669',
        'success_hover': '#047857',
        'warning': '#d97706',
        'warning_hover': '#b45309',
        'danger': '#dc2626',
        'danger_hover': '#b91c1c',
        'text_secondary': '#64748b',
        'hover_bg': '#e2e8f0',
        'toolbar_bg': '#ffffff',
        'toolbar_border': '#e2e8f0',
        'shadow': '#c5cdd8',
        'muted': '#94a3b8',
        'tab_bg': '#e2e8f0',
        'tab_active': '#4f46e5',
    },
    'dark': {
        'bg': '#0f1117',
        'fg': '#e8eaed',
        'select_bg': '#6366f1',
        'select_fg': '#ffffff',
        'entry_bg': '#1c1f2b',
        'entry_fg': '#e8eaed',
        'button_bg': '#2a2f3d',
        'button_fg': '#e8eaed',
        'frame_bg': '#0f1117',
        'text_bg': '#1c1f2b',
        'text_fg': '#e8eaed',
        'card_bg': '#171a23',
        'border': '#2a2f3d',
        'accent': '#6366f1',
        'accent_hover': '#818cf8',
        'success': '#10b981',
        'success_hover': '#34d399',
        'warning': '#f59e0b',
        'warning_hover': '#fbbf24',
        'danger': '#ef4444',
        'danger_hover': '#f87171',
        'text_secondary': '#9ca3af',
        'hover_bg': '#252a38',
        'toolbar_bg': '#141722',
        'toolbar_border': '#252a38',
        'shadow': '#000000',
        'muted': '#6b7280',
        'tab_bg': '#1c1f2b',
        'tab_active': '#6366f1',
    },
}

BTN = {
    'normal': {'padx': 14, 'pady': 7, 'font': ('Segoe UI', 9)},
    'small':  {'padx': 10, 'pady': 5, 'font': ('Segoe UI', 8)},
    'toolbar':{'padx': 12, 'pady': 6, 'font': ('Segoe UI', 9)},
}


def _contrast_fg(bg_hex):
    try:
        h = bg_hex.lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return '#ffffff' if luminance < 0.55 else '#1a1d26'
    except Exception:
        return '#ffffff'


def create_modern_button(self, parent, text, command, bg_color, small=False, size=None):
    if size is None:
        size = 'small' if small else 'normal'
    spec = BTN.get(size, BTN['normal'])

    fg = _contrast_fg(bg_color)
    hover = darken_hex(bg_color, 25) if bg_color else self.colors.get('accent_hover', '#4338ca')

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg_color,
        fg=fg,
        font=spec['font'],
        relief=tk.FLAT,
        padx=spec['padx'],
        pady=spec['pady'],
        cursor='hand2',
        activebackground=hover,
        activeforeground=fg,
        bd=0,
        highlightthickness=0,
    )

    def on_enter(e, b=btn, h=hover):
        try:
            b.config(bg=h)
        except Exception:
            pass

    def on_leave(e, b=btn, c=bg_color):
        try:
            b.config(bg=c)
        except Exception:
            pass

    btn.bind('<Enter>', on_enter)
    btn.bind('<Leave>', on_leave)
    btn.configure(width=max(8, min(22, len(text) + 2)))
    return btn


def create_rounded_card(self, parent, title=None, title_color=None, fill=tk.X, expand=False):
    outer = tk.Frame(parent, bg=self.colors['bg'], relief=tk.FLAT)
    outer.pack(fill=fill, expand=expand, padx=12, pady=8)

    shadow = tk.Frame(outer, bg=self.colors.get('shadow', self.colors['border']), relief=tk.FLAT)
    shadow.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

    card = tk.Frame(shadow, bg=self.colors['card_bg'], relief=tk.FLAT, bd=0)
    card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

    header = None
    content = card

    if title:
        accent = title_color or self.colors['accent']
        header = tk.Frame(card, bg=self.colors['card_bg'], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Frame(header, bg=accent, width=4).pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            header,
            text=title,
            bg=self.colors['card_bg'],
            fg=self.colors['fg'],
            font=('Segoe UI', 10, 'bold'),
            anchor=tk.W
        ).pack(side=tk.LEFT, padx=12, pady=8)

        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill=tk.X)

        content = tk.Frame(card, bg=self.colors['card_bg'])
        content.pack(fill=tk.BOTH, expand=True)

    return content, card, header


def setup_ttk_styles(self):
    style = ttk.Style()
    style.theme_use('clam')
    c = self.colors

    style.configure('TFrame', background=c['bg'], relief=tk.FLAT)
    style.configure('TLabel', background=c['bg'], foreground=c['fg'], font=('Segoe UI', 9))
    style.configure(
        'TLabelFrame', background=c['bg'], foreground=c['fg'],
        borderwidth=1, relief=tk.FLAT, font=('Segoe UI', 9, 'bold')
    )
    style.configure(
        'TLabelFrame.Label', background=c['card_bg'],
        foreground=c['accent'], font=('Segoe UI', 9, 'bold')
    )

    style.configure(
        'TButton', background=c['accent'], foreground='white',
        borderwidth=0, focuscolor='none', padding=(14, 7),
        font=('Segoe UI', 9), relief=tk.FLAT
    )
    style.map(
        'TButton',
        background=[('active', c['accent_hover']), ('pressed', c['accent_hover'])],
        relief=[('pressed', 'flat')]
    )

    style.configure('TNotebook', background=c['bg'], borderwidth=0, tabmargins=[4, 4, 4, 0])
    style.configure(
        'TNotebook.Tab',
        background=c.get('tab_bg', c['card_bg']),
        foreground=c['text_secondary'],
        padding=[18, 10],
        font=('Segoe UI', 9, 'bold'),
        borderwidth=0
    )
    style.map(
        'TNotebook.Tab',
        background=[('selected', c.get('tab_active', c['accent'])), ('active', c['hover_bg'])],
        foreground=[('selected', 'white'), ('active', c['accent'])],
        expand=[('selected', [1, 1, 1, 0])]
    )

    style.configure(
        'TEntry', fieldbackground=c['entry_bg'], foreground=c['entry_fg'],
        borderwidth=1, relief=tk.FLAT, padding=8, font=('Segoe UI', 9)
    )
    style.map('TEntry', fieldbackground=[('focus', c['entry_bg'])],
              bordercolor=[('focus', c['accent'])])

    style.configure(
        'TSpinbox', fieldbackground=c['entry_bg'], foreground=c['entry_fg'],
        borderwidth=1, relief=tk.FLAT, padding=8, font=('Segoe UI', 9)
    )

    style.configure(
        'Treeview',
        background=c['card_bg'], foreground=c['fg'],
        fieldbackground=c['card_bg'], borderwidth=0,
        font=('Segoe UI', 9), rowheight=28
    )
    style.configure(
        'Treeview.Heading',
        background=c['hover_bg'], foreground=c['fg'],
        font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, borderwidth=0,
        padding=(8, 6)
    )
    style.map(
        'Treeview',
        background=[('selected', c['accent'])],
        foreground=[('selected', 'white')]
    )

    style.configure(
        'TScrollbar',
        background=c['border'], troughcolor=c['bg'],
        arrowcolor=c['text_secondary'], borderwidth=0, relief=tk.FLAT
    )
    style.map('TScrollbar', background=[('active', c['muted'])])

    style.configure(
        'Horizontal.TProgressbar',
        troughcolor=c['hover_bg'], background=c['accent'],
        borderwidth=0, thickness=8, lightcolor=c['accent'], darkcolor=c['accent']
    )
    style.configure(
        'TProgressbar',
        troughcolor=c['hover_bg'], background=c['accent'],
        borderwidth=0, thickness=8
    )


def create_status_bar(self):
    self.status_bar = tk.Frame(self.root, bg=self.colors['card_bg'], height=30, relief=tk.FLAT)
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
    self.status_label.pack(side=tk.LEFT, padx=16, pady=4)

    theme_name = self.config.get('theme', 'light')
    self.status_theme_label = tk.Label(
        self.status_bar,
        text=f"Тема: {'Тёмная' if theme_name == 'dark' else 'Светлая'}",
        bg=self.colors['card_bg'],
        fg=self.colors['text_secondary'],
        font=('Segoe UI', 9)
    )
    self.status_theme_label.pack(side=tk.RIGHT, padx=16, pady=4)


def create_modern_toolbar(self):
    self.toolbar_outer = tk.Frame(self.root, bg=self.colors.get('toolbar_bg', self.colors['card_bg']))
    self.toolbar_outer.pack(fill=tk.X, side=tk.TOP)

    tk.Frame(
        self.toolbar_outer,
        bg=self.colors.get('toolbar_border', self.colors['border']),
        height=1
    ).pack(side=tk.BOTTOM, fill=tk.X)

    bar = tk.Frame(self.toolbar_outer, bg=self.colors.get('toolbar_bg', self.colors['card_bg']), height=48)
    bar.pack(fill=tk.X, padx=10, pady=6)
    bar.pack_propagate(False)

    left = tk.Frame(bar, bg=self.colors.get('toolbar_bg', self.colors['card_bg']))
    left.pack(side=tk.LEFT, fill=tk.Y)

    right = tk.Frame(bar, bg=self.colors.get('toolbar_bg', self.colors['card_bg']))
    right.pack(side=tk.RIGHT, fill=tk.Y)

    def group_sep(parent):
        sep = tk.Frame(parent, bg=self.colors['border'], width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=6)

    def add_btn(parent, text, cmd, color):
        b = self.create_modern_button(parent, text, cmd, color, size='toolbar')
        b.pack(side=tk.LEFT, padx=3, pady=2)
        return b

    add_btn(left, "📊 Статистика", self.run_stats_parser, self.colors['accent'])
    add_btn(left, "👤 Аккаунты", self.refresh_accounts, self.colors['success'])
    group_sep(left)
    add_btn(left, "💾 Экспорт", self.show_export_menu, self.colors['warning'])
    add_btn(left, "📅 Планировщик", self.open_scheduler, self.colors['text_secondary'])

    add_btn(right, "🎨 Тема", self.show_theme_menu, self.colors['accent'])
    add_btn(right, "ℹ️ О программе", self.show_about, self.colors['text_secondary'])


def show_theme_menu(self):
    menu_window = tk.Toplevel(self.root)
    menu_window.title("Тема оформления")
    menu_window.geometry("320x220")
    menu_window.resizable(False, False)
    menu_window.configure(bg=self.colors['bg'])
    menu_window.transient(self.root)
    menu_window.grab_set()

    try:
        menu_window.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - 320) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - 220) // 2
        menu_window.geometry(f"+{x}+{y}")
    except Exception:
        pass

    card = tk.Frame(menu_window, bg=self.colors['card_bg'])
    card.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

    tk.Label(
        card, text="Выберите тему",
        bg=self.colors['card_bg'], fg=self.colors['fg'],
        font=('Segoe UI', 12, 'bold')
    ).pack(pady=(8, 16))

    btn_frame = tk.Frame(card, bg=self.colors['card_bg'])
    btn_frame.pack(fill=tk.X, padx=20)

    light_btn = self.create_modern_button(
        btn_frame, "☀️  Светлая",
        lambda: [self.change_theme('light'), menu_window.destroy()],
        self.colors['accent'], size='normal'
    )
    light_btn.pack(fill=tk.X, pady=4)
    light_btn.configure(width=22)

    dark_btn = self.create_modern_button(
        btn_frame, "🌙  Тёмная",
        lambda: [self.change_theme('dark'), menu_window.destroy()],
        '#1e293b', size='normal'
    )
    dark_btn.pack(fill=tk.X, pady=4)
    dark_btn.configure(width=22)

    cancel = self.create_modern_button(
        btn_frame, "Отмена", menu_window.destroy,
        self.colors['text_secondary'], size='normal'
    )
    cancel.pack(fill=tk.X, pady=(12, 4))
    cancel.configure(width=22)


def init_colors(self):
    theme_name = self.config.get('theme', 'light')
    theme = THEMES.get(theme_name, THEMES['light'])
    self.colors = theme.copy()
    if hasattr(self, 'theme_manager'):
        self.theme_manager.themes = THEMES
        self.theme_manager.current_theme = theme_name


def install_ui_design(app_cls):
    app_cls.create_modern_button = create_modern_button
    app_cls.create_rounded_card = create_rounded_card
    app_cls.setup_ttk_styles = setup_ttk_styles
    app_cls.create_status_bar = create_status_bar
    app_cls.create_modern_toolbar = create_modern_toolbar
    app_cls.show_theme_menu = show_theme_menu
    app_cls.init_colors = init_colors

    try:
        from modules import theme_manager as tm_mod
        _orig_init = tm_mod.ThemeManager.__init__

        def _new_init(self, *a, **k):
            _orig_init(self, *a, **k)
            self.themes = {k2: v.copy() for k2, v in THEMES.items()}

        tm_mod.ThemeManager.__init__ = _new_init
    except Exception as e:
        print(f"ThemeManager patch note: {e}")

    return app_cls
