"""
Фоновые задачи: парсинг, обновление аккаунтов — в отдельных потоках.
Защита от повторного запуска и зависания UI.
"""
import os
import threading
from tkinter import messagebox


def run_stats_parser(self):
    """Запуск парсинга в фоне с защитой от повторного старта."""
    if getattr(self, "_stats_running", False):
        messagebox.showwarning(
            "Уже выполняется",
            "Парсинг статистики уже идёт.\nДождитесь завершения."
        )
        return

    links_file = self.config.get("links_file", "links.txt")
    if not links_file or not os.path.exists(links_file):
        messagebox.showerror("Ошибка", f"Файл со ссылками не найден:\n{links_file}")
        return

    self._stats_running = True
    self._set_stats_busy_ui(True)
    self.set_status("Парсинг статистики...")

    thread = threading.Thread(target=self._run_stats_parser_thread, daemon=True)
    self._stats_thread = thread
    thread.start()


def _set_stats_busy_ui(self, busy):
    state = "disabled" if busy else "normal"
    for name in ("stats_start_btn", "stats_run_btn", "parse_btn"):
        btn = getattr(self, name, None)
        if btn is not None:
            try:
                btn.config(state=state)
            except Exception:
                pass


def _run_stats_parser_thread(self):
    try:
        self.root.after(0, lambda: self._append_stats_log("Начинаю парсинг статистики...\n", True))

        def progress_callback(current, total, link):
            msg = f"[{current}/{total}] {link}\n"
            self.root.after(0, lambda m=msg: self._append_stats_log(m))

        results = self.stats_parser.parse_channels(
            self.config.get("links_file", "links.txt"),
            progress_callback=progress_callback,
        )
        self.root.after(0, self._update_stats_ui, results)
        self.root.after(
            0,
            self.set_status,
            f"Парсинг завершён: {len(results) if results else 0} каналов",
        )
    except Exception as e:
        self.root.after(0, self._stats_error, str(e))
        self.root.after(0, self.set_status, "Ошибка парсинга")
    finally:
        self.root.after(0, self._stats_parse_finished)


def _stats_parse_finished(self):
    self._stats_running = False
    self._set_stats_busy_ui(False)


def refresh_accounts(self):
    """Сканирование папок аккаунтов в фоне."""
    if not hasattr(self, "accounts_summary_text"):
        return

    if getattr(self, "_accounts_running", False):
        messagebox.showwarning(
            "Уже выполняется",
            "Обновление аккаунтов уже идёт. Дождитесь завершения."
        )
        return

    folders = self.config.get("accounts_folders", [])
    if not folders:
        try:
            self.accounts_summary_text.config(state="normal")
            self.accounts_summary_text.delete("1.0", "end")
            self.accounts_summary_text.insert(
                "1.0",
                "Не добавлено ни одной папки с аккаунтами.\n"
                "Используйте кнопку '➕ Добавить папку' для добавления папок с профилями.",
            )
            self.accounts_summary_text.config(state="disabled")
        except Exception:
            pass
        if hasattr(self, "accounts_tree"):
            for item in self.accounts_tree.get_children():
                self.accounts_tree.delete(item)
        self.current_accounts_data = []
        return

    self._accounts_running = True
    self.set_status("Обновление аккаунтов...")

    def worker():
        try:
            accounts_data = self.account_manager.scan_multiple_folders(folders)
            self.root.after(0, self._apply_accounts_ui, accounts_data)
        except Exception as e:
            self.root.after(0, self._accounts_error, str(e))
        finally:
            self.root.after(0, self._accounts_finished)

    self._accounts_thread = threading.Thread(target=worker, daemon=True)
    self._accounts_thread.start()


def _apply_accounts_ui(self, accounts_data):
    if not hasattr(self, "accounts_tree"):
        return

    for item in self.accounts_tree.get_children():
        self.accounts_tree.delete(item)

    self.current_accounts_data = accounts_data or []
    total_materials = 0
    total_size = 0

    for account in self.current_accounts_data:
        folder_display = (
            os.path.basename(account.get("folder", ""))
            or account.get("folder", "Неизвестно")
        )
        try:
            total_materials += int(account.get("materials_count") or 0)
        except Exception:
            pass
        try:
            total_size += int(account.get("size_bytes") or 0)
        except Exception:
            pass

        self.accounts_tree.insert(
            "",
            "end",
            values=(
                account.get("name", ""),
                folder_display,
                account.get("materials_count", 0),
                account.get("size", ""),
                account.get("modified_date", ""),
                account.get("quality_score", ""),
            ),
            tags=(account.get("name", ""),),
        )

    if hasattr(self, "accounts_summary_text"):
        try:
            size_str = self.account_manager.format_size(total_size) if total_size else "—"
            text = (
                f"👤 Аккаунтов: {len(self.current_accounts_data)}\n"
                f"📁 Папок: {len(self.config.get('accounts_folders', []))}\n"
                f"📦 Материалов: {total_materials}\n"
                f"💾 Общий размер: {size_str}\n"
            )
            self.accounts_summary_text.config(state="normal")
            self.accounts_summary_text.delete("1.0", "end")
            self.accounts_summary_text.insert("1.0", text)
            self.accounts_summary_text.config(state="disabled")
        except Exception:
            pass

    if hasattr(self, "refresh_dashboard"):
        try:
            self.refresh_dashboard()
        except Exception:
            pass

    self.set_status(f"Аккаунты обновлены: {len(self.current_accounts_data)}")


def _accounts_error(self, error_msg):
    messagebox.showerror("Ошибка", f"Ошибка при обновлении аккаунтов:\n{error_msg}")
    self.set_status("Ошибка обновления аккаунтов")


def _accounts_finished(self):
    self._accounts_running = False


def start_telegram_bot(self):
    if getattr(self, "_bot_running", False):
        messagebox.showwarning("Уже запущен", "Telegram-бот уже работает.")
        return

    token = self.bot_token_entry.get().strip() if hasattr(self, "bot_token_entry") else ""
    chat_id = self.chat_id_entry.get().strip() if hasattr(self, "chat_id_entry") else ""

    if not token or not chat_id:
        messagebox.showerror("Ошибка", "Укажите Bot Token и Chat ID!")
        return

    self._bot_running = True
    try:
        self.bot_start_btn.config(state="disabled")
        self.bot_stop_btn.config(state="normal")
    except Exception:
        pass

    try:
        self.bot_status_text.config(state="normal")
        self.bot_status_text.delete("1.0", "end")
        self.bot_status_text.insert("1.0", "Запуск бота...\n")
        self.bot_status_text.config(state="disabled")
    except Exception:
        pass

    thread = threading.Thread(target=self._telegram_bot_thread, daemon=True)
    self._bot_thread = thread
    thread.start()


def _telegram_bot_thread(self):
    try:
        self.telegram_bot.start(self._bot_status_callback)
    except Exception as e:
        self.root.after(0, lambda: self._bot_error(str(e)))
    finally:
        self.root.after(0, self._bot_thread_finished)


def _bot_thread_finished(self):
    self._bot_running = False
    try:
        self.bot_start_btn.config(state="normal")
        self.bot_stop_btn.config(state="disabled")
    except Exception:
        pass


def stop_telegram_bot(self):
    try:
        self.telegram_bot.stop()
    except Exception:
        pass
    self._bot_running = False
    try:
        self.bot_start_btn.config(state="normal")
        self.bot_stop_btn.config(state="disabled")
    except Exception:
        pass
    self.set_status("Telegram-бот остановлен")


def install_background_jobs(app_cls):
    app_cls.run_stats_parser = run_stats_parser
    app_cls._set_stats_busy_ui = _set_stats_busy_ui
    app_cls._run_stats_parser_thread = _run_stats_parser_thread
    app_cls._stats_parse_finished = _stats_parse_finished

    app_cls.refresh_accounts = refresh_accounts
    app_cls._apply_accounts_ui = _apply_accounts_ui
    app_cls._accounts_error = _accounts_error
    app_cls._accounts_finished = _accounts_finished

    app_cls.start_telegram_bot = start_telegram_bot
    app_cls._telegram_bot_thread = _telegram_bot_thread
    app_cls._bot_thread_finished = _bot_thread_finished
    app_cls.stop_telegram_bot = stop_telegram_bot

    return app_cls
