#!/usr/bin/env python3
"""Apply theme + notification fixes to аналитика/main.py in place."""
from pathlib import Path

p = Path("аналитика/main.py")
if not p.exists():
    p = Path("main.py")
text = p.read_text(encoding="utf-8")

old = """        # Пересоздаем тулбар с новыми цветами
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.destroy()
        
        self.create_modern_toolbar()
        
        messagebox.showinfo("Успех", f"Тема изменена на: {'Светлую' if theme_name == 'light' else 'Темную'}")"""

new = """        # Пересоздаём только toolbar, не трогая notebook и status_bar
        if hasattr(self, 'toolbar_outer') and self.toolbar_outer.winfo_exists():
            self.toolbar_outer.destroy()
        self.create_modern_toolbar()

        if hasattr(self, 'status_theme_label') and self.status_theme_label.winfo_exists():
            self.status_theme_label.config(
                text=f"Тема: {'Тёмная' if theme_name == 'dark' else 'Светлая'}",
                bg=self.colors['card_bg'],
                fg=self.colors['text_secondary']
            )
        if hasattr(self, 'status_bar') and self.status_bar.winfo_exists():
            self.status_bar.config(bg=self.colors['card_bg'])
        if hasattr(self, 'status_label') and self.status_label.winfo_exists():
            self.status_label.config(bg=self.colors['card_bg'], fg=self.colors['text_secondary'])

        self.set_status(f"Тема: {'тёмная' if theme_name == 'dark' else 'светлая'}")
        messagebox.showinfo("Успех", f"Тема изменена на: {'Светлую' if theme_name == 'light' else 'Темную'}")"""

if old not in text:
    raise SystemExit("theme block not found — already fixed or different version")
text = text.replace(old, new)

old2 = '''                result = messagebox.showwarning("Уведомления", notification_text)
                # Можно отметить как прочитанные, если нужно'''
new2 = '''                messagebox.showwarning("Уведомления", notification_text)
                for notif in notifications:
                    try:
                        self.database.mark_notification_read(notif[0])
                    except Exception:
                        pass'''

if old2 not in text:
    print("warning: notif block not found (maybe already fixed)")
else:
    text = text.replace(old2, new2)

p.write_text(text, encoding="utf-8")
print("OK: applied fixes to", p)
