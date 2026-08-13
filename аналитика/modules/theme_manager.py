"""
Модуль для управления темами оформления
"""
import tkinter as tk
from tkinter import ttk

class ThemeManager:
    def __init__(self):
        self.current_theme = 'light'
        self.themes = {
            'light': {
                'bg': '#f8f9fa',
                'fg': '#212529',
                'select_bg': '#0d6efd',
                'select_fg': '#ffffff',
                'entry_bg': '#ffffff',
                'entry_fg': '#212529',
                'button_bg': '#f0f0f0',
                'button_fg': '#212529',
                'frame_bg': '#f8f9fa',
                'text_bg': '#ffffff',
                'text_fg': '#212529',
                'card_bg': '#ffffff',
                'border': '#dee2e6',
                'accent': '#0d6efd',
                'accent_hover': '#0b5ed7',
                'success': '#198754',
                'warning': '#ffc107',
                'danger': '#dc3545',
                'text_secondary': '#6c757d',
                'hover_bg': '#e9ecef'
            },
            'dark': {
                'bg': '#1a1a1a',
                'fg': '#e0e0e0',
                'select_bg': '#0d6efd',
                'select_fg': '#ffffff',
                'entry_bg': '#2d2d2d',
                'entry_fg': '#e0e0e0',
                'button_bg': '#404040',
                'button_fg': '#ffffff',
                'frame_bg': '#1a1a1a',
                'text_bg': '#2d2d2d',
                'text_fg': '#e0e0e0',
                'card_bg': '#2d2d2d',
                'border': '#404040',
                'accent': '#0d6efd',
                'accent_hover': '#0b5ed7',
                'success': '#198754',
                'warning': '#ffc107',
                'danger': '#dc3545',
                'text_secondary': '#9ca3af',
                'hover_bg': '#3a3a3a'
            }
        }
    
    def apply_theme(self, root, theme_name='light'):
        """Применение темы к приложению"""
        if theme_name not in self.themes:
            theme_name = 'light'
        
        self.current_theme = theme_name
        theme = self.themes[theme_name]
        
        # Настройка стиля ttk
        style = ttk.Style()
        style.theme_use('clam')
        
        # Настройка цветов для ttk виджетов
        style.configure('TFrame', background=theme['frame_bg'])
        style.configure('TLabel', background=theme['frame_bg'], foreground=theme['fg'])
        style.configure('TButton', background=theme['button_bg'], foreground=theme['button_fg'])
        style.configure('TEntry', fieldbackground=theme['entry_bg'], foreground=theme['entry_fg'])
        style.configure('TText', background=theme['text_bg'], foreground=theme['text_fg'])
        style.configure('TNotebook', background=theme['frame_bg'])
        style.configure('TNotebook.Tab', background=theme['button_bg'], foreground=theme['button_fg'])
        style.configure('Treeview', background=theme['card_bg'], foreground=theme['fg'],
                       fieldbackground=theme['card_bg'], borderwidth=0, font=('Segoe UI', 9))
        style.configure('Treeview.Heading', background=theme['hover_bg'], foreground=theme['fg'],
                       font=('Segoe UI', 9, 'bold'), relief=tk.FLAT)
        style.map('Treeview',
                 background=[('selected', theme['accent'])],
                 foreground=[('selected', 'white')])
        
        root.configure(bg=theme['bg'])
        self._apply_theme_recursive(root, theme)
    
    def _apply_theme_recursive(self, widget, theme):
        """Рекурсивное применение темы к виджетам"""
        widget_type = widget.winfo_class()
        
        try:
            if widget_type in ['Text', 'ScrolledText']:
                widget.configure(bg=theme['text_bg'], fg=theme['text_fg'],
                               selectbackground=theme['select_bg'],
                               selectforeground=theme['select_fg'],
                               insertbackground=theme['fg'])
            elif widget_type == 'Listbox':
                widget.configure(bg=theme['entry_bg'], fg=theme['entry_fg'],
                               selectbackground=theme['select_bg'],
                               selectforeground=theme['select_fg'])
            elif widget_type == 'Entry':
                widget.configure(bg=theme['entry_bg'], fg=theme['entry_fg'],
                               insertbackground=theme['fg'])
            elif widget_type == 'Frame':
                widget.configure(bg=theme['frame_bg'])
            elif widget_type == 'Label':
                widget.configure(bg=theme['frame_bg'], fg=theme['fg'])
            elif widget_type == 'Button':
                widget.configure(bg=theme['button_bg'], fg=theme['button_fg'],
                               activebackground=theme['select_bg'],
                               activeforeground=theme['select_fg'])
        except:
            pass
        
        # Применяем к дочерним виджетам
        for child in widget.winfo_children():
            self._apply_theme_recursive(child, theme)
    
    def get_current_theme(self):
        """Получение текущей темы"""
        return self.current_theme

