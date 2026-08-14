"""
Модуль для управления темами оформления (палитра v2).
"""
import tkinter as tk
from tkinter import ttk

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


class ThemeManager:
    def __init__(self):
        self.current_theme = 'light'
        self.themes = {k: v.copy() for k, v in THEMES.items()}

    def apply_theme(self, root, theme_name='light'):
        if theme_name not in self.themes:
            theme_name = 'light'

        self.current_theme = theme_name
        theme = self.themes[theme_name]

        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=theme['frame_bg'])
        style.configure('TLabel', background=theme['frame_bg'], foreground=theme['fg'])
        style.configure('TButton', background=theme['button_bg'], foreground=theme['button_fg'])
        style.configure('TEntry', fieldbackground=theme['entry_bg'], foreground=theme['entry_fg'])
        style.configure('TText', background=theme['text_bg'], foreground=theme['text_fg'])
        style.configure('TNotebook', background=theme['frame_bg'], borderwidth=0)
        style.configure(
            'TNotebook.Tab',
            background=theme.get('tab_bg', theme['button_bg']),
            foreground=theme['button_fg'],
            padding=[18, 10],
            font=('Segoe UI', 9, 'bold')
        )
        style.map(
            'TNotebook.Tab',
            background=[('selected', theme.get('tab_active', theme['accent'])), ('active', theme['hover_bg'])],
            foreground=[('selected', 'white'), ('active', theme['accent'])]
        )
        style.configure(
            'Treeview', background=theme['card_bg'], foreground=theme['fg'],
            fieldbackground=theme['card_bg'], borderwidth=0, font=('Segoe UI', 9), rowheight=28
        )
        style.configure(
            'Treeview.Heading', background=theme['hover_bg'], foreground=theme['fg'],
            font=('Segoe UI', 9, 'bold'), relief=tk.FLAT
        )
        style.map(
            'Treeview',
            background=[('selected', theme['accent'])],
            foreground=[('selected', 'white')]
        )

        root.configure(bg=theme['bg'])
        self._apply_theme_recursive(root, theme)

    def _apply_theme_recursive(self, widget, theme):
        widget_type = widget.winfo_class()
        try:
            if widget_type in ['Text', 'ScrolledText']:
                widget.configure(
                    bg=theme['text_bg'], fg=theme['text_fg'],
                    selectbackground=theme['select_bg'],
                    selectforeground=theme['select_fg'],
                    insertbackground=theme['fg']
                )
            elif widget_type == 'Listbox':
                widget.configure(
                    bg=theme['entry_bg'], fg=theme['entry_fg'],
                    selectbackground=theme['select_bg'],
                    selectforeground=theme['select_fg']
                )
            elif widget_type == 'Entry':
                widget.configure(
                    bg=theme['entry_bg'], fg=theme['entry_fg'],
                    insertbackground=theme['fg']
                )
            elif widget_type == 'Frame':
                widget.configure(bg=theme['frame_bg'])
            elif widget_type == 'Label':
                widget.configure(bg=theme['frame_bg'], fg=theme['fg'])
            elif widget_type == 'Button':
                pass
        except Exception:
            pass

        for child in widget.winfo_children():
            self._apply_theme_recursive(child, theme)

    def get_current_theme(self):
        return self.current_theme
