"""
Утилиты для работы с UI
"""
import tkinter as tk

def darken_hex(color, amount=20):
    """Затемняет hex-цвет для эффекта hover"""
    if not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
        return color
    try:
        r = max(0, int(color[1:3], 16) - amount)
        g = max(0, int(color[3:5], 16) - amount)
        b = max(0, int(color[5:7], 16) - amount)
        return f"#{r:02x}{g:02x}{b:02x}"
    except ValueError:
        return color

def create_themed_window(parent, title, width, height, colors):
    """Создаёт центрированное модальное окно в стиле приложения"""
    window = tk.Toplevel(parent)
    window.title(title)
    window.geometry(f"{width}x{height}")
    window.configure(bg=colors['bg'])
    window.transient(parent)
    window.grab_set()

    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")
    return window

def create_section_header(parent, title, color, colors):
    """Заголовок секции в стиле карточки"""
    header = tk.Frame(parent, bg=color, height=40)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    tk.Label(header, text=title, bg=color, fg='white',
             font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)
    return header

def style_scrolled_text(widget, colors, font=('Segoe UI', 9)):
    """Применяет тему к ScrolledText"""
    widget.configure(
        bg=colors['card_bg'],
        fg=colors['fg'],
        font=font,
        relief=tk.FLAT,
        padx=12,
        pady=12,
        insertbackground=colors['fg'],
        selectbackground=colors['accent'],
        selectforeground='white',
        borderwidth=0
    )

def apply_rounded_effect(frame, bg_color, shadow_color='#e0e0e0', radius=8):
    """Применяет визуальный эффект закругления к фрейму"""
    outer = tk.Frame(frame.master, bg=shadow_color, height=1)
    outer.pack(fill=tk.BOTH, expand=True, padx=radius//4, pady=radius//4, before=frame)
    inner = tk.Frame(outer, bg=bg_color, relief=tk.FLAT, bd=0)
    inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
    return inner

def create_rounded_card(parent, title=None, title_color=None, content_bg=None, 
                       fill=tk.X, expand=False, shadow=True):
    """Создает закругленную карточку"""
    container = tk.Frame(parent, bg=parent.cget('bg') if hasattr(parent, 'cget') else '#f8f9fa')
    
    if shadow:
        outer = tk.Frame(container, bg='#e0e0e0' if content_bg == '#ffffff' or content_bg is None else '#404040')
        outer.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        inner = tk.Frame(outer, bg=content_bg or '#ffffff', relief=tk.FLAT, bd=0)
        inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    else:
        inner = tk.Frame(container, bg=content_bg or '#ffffff', relief=tk.FLAT, bd=0)
        inner.pack(fill=tk.BOTH, expand=True)
    
    header = None
    content = inner
    if title:
        header = tk.Frame(inner, bg=title_color or '#0d6efd', height=45)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text=title, bg=title_color or '#0d6efd', fg='white',
                font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)
        content = tk.Frame(inner, bg=content_bg or '#ffffff')
        content.pack(fill=tk.BOTH, expand=True)
    
    container.pack(fill=fill, expand=expand, padx=15, pady=10)
    return content, inner, header, container
