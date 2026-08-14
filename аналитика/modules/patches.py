"""Runtime patches for AnalyticsApp (theme + notifications).
Import this after AnalyticsApp is defined, or call apply_patches(AnalyticsApp).
"""
import tkinter as tk
from tkinter import messagebox


def _change_theme(self, theme_name):
    """Изменение темы оформления без уничтожения UI"""
    self.config['theme'] = theme_name
    self.save_config()

    theme = self.theme_manager.themes[theme_name]
    self.colors = theme.copy()

    self.theme_manager.apply_theme(self.root, theme_name)
    self.setup_ttk_styles()
    self.update_ui_colors(theme)

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
    messagebox.showinfo("Успех", f"Тема изменена на: {'Светлую' if theme_name == 'light' else 'Темную'}")


def _check_notifications(self):
    """Проверка и отображение уведомлений"""
    try:
        notifications = self.database.get_unread_notifications()
        if notifications:
            notification_text = "У вас есть непрочитанные уведомления:\n\n"
            for notif in notifications[:5]:
                notification_text += f"• {notif[2]}\n"

            if len(notifications) > 5:
                notification_text += f"\n... и еще {len(notifications) - 5} уведомлений"

            messagebox.showwarning("Уведомления", notification_text)
            for notif in notifications:
                try:
                    self.database.mark_notification_read(notif[0])
                except Exception:
                    pass
    except Exception as e:
        print(f"Ошибка при проверке уведомлений: {e}")


def apply_patches(app_cls):
    """Monkey-patch AnalyticsApp methods."""
    app_cls.change_theme = _change_theme
    app_cls.check_notifications = _check_notifications
    return app_cls
