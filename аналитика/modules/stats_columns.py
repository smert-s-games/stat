"""
Столбцы «Ссылка» и «Email» в таблице статистики.
"""
import webbrowser
import tkinter as tk
from tkinter import ttk


STATS_COLUMNS = ("Канал", "Подписчики", "Просмотры", "Видео", "Ссылка", "Email", "Статус")
STATS_WIDTHS = {
    "Канал": 160,
    "Подписчики": 100,
    "Просмотры": 110,
    "Видео": 80,
    "Ссылка": 220,
    "Email": 160,
    "Статус": 90,
}


def _row_values(result):
    if "error" in result:
        return (
            result.get("url", "Неизвестно"),
            "-",
            "-",
            "-",
            result.get("url", ""),
            "-",
            f"❌ {result.get('error', 'Ошибка')}",
        )
    return (
        result.get("channel_name", "Неизвестно"),
        result.get("subscribers", "0"),
        result.get("total_views", "0"),
        result.get("videos_count", "0"),
        result.get("url", ""),
        result.get("email") or "—",
        "✅",
    )


def _apply_stats_tree_columns(self):
    if not hasattr(self, "stats_tree"):
        return
    tree = self.stats_tree
    tree["columns"] = STATS_COLUMNS
    for col in STATS_COLUMNS:
        tree.heading(col, text=col)
        tree.column(col, width=STATS_WIDTHS.get(col, 120), minwidth=60)
    tree.bind("<Double-1>", self._on_stats_row_double_click)


def _on_stats_row_double_click(self, event=None):
    tree = self.stats_tree
    sel = tree.selection()
    if not sel:
        return
    vals = tree.item(sel[0], "values")
    if not vals or len(vals) < 5:
        return
    url = vals[4]
    if url and str(url).startswith("http"):
        try:
            webbrowser.open(url)
        except Exception:
            pass


def _update_stats_ui(self, results):
    self.current_stats_results = results

    try:
        self.stats_history.save_stats(results)
        self.database.log_operation("stats_parse", f"Парсинг статистики: {len(results)} каналов")
    except Exception:
        pass

    for item in self.stats_tree.get_children():
        self.stats_tree.delete(item)

    total_channels = 0
    total_views = 0
    total_subs = 0
    total_videos = 0

    for result in results:
        if "error" not in result:
            total_channels += 1
            try:
                total_views += self.stats_parser.parse_number(result.get("total_views", "0"))
                total_subs += self.stats_parser.parse_number(result.get("subscribers", "0"))
                total_videos += self.stats_parser.parse_number(result.get("videos_count", "0"))
            except Exception:
                pass
        self.stats_tree.insert("", tk.END, values=_row_values(result))

    if hasattr(self, "stats_summary_text"):
        try:
            self.stats_summary_text.config(state=tk.NORMAL)
            self.stats_summary_text.delete("1.0", tk.END)
            summary = (
                f"📊 ОБЩАЯ СТАТИСТИКА:\n\n"
                f"📈 Каналов обработано: {total_channels}\n"
                f"👀 Всего просмотров: {self.stats_parser.format_large_number(total_views)}\n"
                f"👥 Всего подписчиков: {self.stats_parser.format_large_number(total_subs)}\n"
                f"🎥 Всего видео: {self.stats_parser.format_large_number(total_videos)}\n"
            )
            self.stats_summary_text.insert("1.0", summary)
            self.stats_summary_text.config(state=tk.DISABLED)
        except Exception:
            pass

    if hasattr(self, "stats_log"):
        try:
            self.stats_log.config(state=tk.NORMAL)
            self.stats_log.insert(tk.END, f"\n✅ Парсинг завершен. Обработано каналов: {len(results)}\n")
            self.stats_log.config(state=tk.DISABLED)
        except Exception:
            pass


def filter_stats_table(self, event=None):
    search_text = ""
    if hasattr(self, "stats_search_entry"):
        search_text = self.stats_search_entry.get().lower().strip()

    for item in self.stats_tree.get_children():
        self.stats_tree.delete(item)

    for result in getattr(self, "current_stats_results", []) or []:
        if "error" not in result:
            blob = " ".join([
                str(result.get("channel_name", "")),
                str(result.get("url", "")),
                str(result.get("email", "")),
            ]).lower()
            if search_text and search_text not in blob:
                continue
            self.stats_tree.insert("", tk.END, values=_row_values(result))
        else:
            url = str(result.get("url", "")).lower()
            if search_text and search_text not in url:
                continue
            self.stats_tree.insert("", tk.END, values=_row_values(result))


def install_stats_columns(app_cls):
    original_create = app_cls.create_stats_tab

    def create_stats_tab_with_cols(self):
        original_create(self)
        try:
            _apply_stats_tree_columns(self)
        except Exception as e:
            print(f"stats columns apply error: {e}")

    app_cls.create_stats_tab = create_stats_tab_with_cols
    app_cls._apply_stats_tree_columns = _apply_stats_tree_columns
    app_cls._on_stats_row_double_click = _on_stats_row_double_click
    app_cls._update_stats_ui = _update_stats_ui
    app_cls.filter_stats_table = filter_stats_table
    return app_cls
