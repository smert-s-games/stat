"""Runtime patches: design system, shell, theme, notifications, dashboard, video scripts, stats columns."""
import tkinter as tk
from tkinter import messagebox


def _change_theme(self, theme_name):
    """Смена темы без уничтожения UI."""
    self.config['theme'] = theme_name
    self.save_config()

    try:
        from modules.ui_design import THEMES
        theme = THEMES.get(theme_name, THEMES['light']).copy()
        if hasattr(self, 'theme_manager'):
            self.theme_manager.themes = THEMES
            self.theme_manager.current_theme = theme_name
    except Exception:
        theme = self.theme_manager.themes[theme_name]

    self.colors = theme.copy()
    self.theme_manager.apply_theme(self.root, theme_name)
    self.setup_ttk_styles()
    self.update_ui_colors(theme)

    if hasattr(self, '_app_header') and self._app_header.winfo_exists():
        pass
    elif hasattr(self, 'toolbar_outer') and self.toolbar_outer is not None:
        try:
            if self.toolbar_outer.winfo_exists():
                self.toolbar_outer.destroy()
                self.create_modern_toolbar()
        except Exception:
            pass

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

    if hasattr(self, '_build_dashboard_content') and hasattr(self, 'dashboard_inner'):
        try:
            self._build_dashboard_content()
        except Exception:
            pass

    self.set_status(f"Тема: {'тёмная' if theme_name == 'dark' else 'светлая'}")
    messagebox.showinfo("Успех", f"Тема изменена на: {'Светлую' if theme_name == 'light' else 'Тёмную'}")


def _check_notifications(self):
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
            if hasattr(self, 'refresh_dashboard'):
                try:
                    self.refresh_dashboard()
                except Exception:
                    pass
    except Exception as e:
        print(f"Ошибка при проверке уведомлений: {e}")


def apply_patches(app_cls):
    try:
        from modules.ui_design import install_ui_design
        install_ui_design(app_cls)
    except Exception as e:
        print(f"UI design patch skipped: {e}")

    try:
        from modules.ui_shell import install_ui_shell
        install_ui_shell(app_cls)
    except Exception as e:
        print(f"UI shell patch skipped: {e}")

    app_cls.change_theme = _change_theme
    app_cls.check_notifications = _check_notifications

    try:
        from modules.dashboard import install_dashboard
        install_dashboard(app_cls)
    except Exception as e:
        print(f"Dashboard patch skipped: {e}")

    try:
        from modules.dashboard_style import install_dashboard_style
        install_dashboard_style(app_cls)
    except Exception as e:
        print(f"Dashboard style patch skipped: {e}")

    try:
        from modules.video_scripts_ui import install_video_scripts
        install_video_scripts(app_cls)
    except Exception as e:
        print(f"Video scripts patch skipped: {e}")

    try:
        from modules.stats_columns import install_stats_columns
        install_stats_columns(app_cls)
    except Exception as e:
        print(f"Stats columns patch skipped: {e}")

    return app_cls
