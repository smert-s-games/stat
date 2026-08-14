"""
Вкладка «Главная» — панель с KPI, графиками роста и быстрыми действиями.
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from collections import defaultdict

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.dates as mdates
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def create_dashboard_tab(self):
    """Создаёт вкладку-дашборд и вставляет её первой."""
    dash = ttk.Frame(self.notebook)
    self.notebook.insert(0, dash, text="🏠 Главная")
    self.notebook.select(0)

    canvas = tk.Canvas(dash, bg=self.colors['bg'], highlightthickness=0)
    scrollbar = ttk.Scrollbar(dash, orient=tk.VERTICAL, command=canvas.yview)
    self.dashboard_inner = tk.Frame(canvas, bg=self.colors['bg'])

    self.dashboard_inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    self._dashboard_canvas_window = canvas.create_window(
        (0, 0), window=self.dashboard_inner, anchor="nw"
    )

    def _on_canvas_configure(event):
        canvas.itemconfig(self._dashboard_canvas_window, width=event.width)

    canvas.bind("<Configure>", _on_canvas_configure)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_mousewheel(event):
        try:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    self.dashboard_canvas = canvas
    self._dash_chart_canvases = []
    self._build_dashboard_content()


def _build_dashboard_content(self):
    """Собирает карточки и графики дашборда."""
    parent = self.dashboard_inner
    for w in parent.winfo_children():
        w.destroy()
    self._dash_chart_canvases = []

    header = tk.Frame(parent, bg=self.colors['bg'])
    header.pack(fill=tk.X, padx=20, pady=(20, 10))

    tk.Label(
        header,
        text="Панель управления",
        bg=self.colors['bg'],
        fg=self.colors['fg'],
        font=('Segoe UI', 18, 'bold')
    ).pack(side=tk.LEFT)

    self.create_modern_button(
        header, "🔄 Обновить", self.refresh_dashboard, self.colors['accent'], small=True
    ).pack(side=tk.RIGHT, padx=5)

    kpi_row = tk.Frame(parent, bg=self.colors['bg'])
    kpi_row.pack(fill=tk.X, padx=15, pady=5)

    self.dash_kpi_frames = {}
    kpis = [
        ("channels", "📺 Каналы", "—", self.colors['accent']),
        ("views", "👀 Просмотры", "—", self.colors['success']),
        ("subs", "👥 Подписчики", "—", self.colors['warning']),
        ("accounts", "👤 Аккаунты", "—", self.colors['text_secondary']),
    ]
    for key, title, value, color in kpis:
        card = self._dash_kpi_card(kpi_row, title, value, color)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.dash_kpi_frames[key] = card

    charts_row = tk.Frame(parent, bg=self.colors['bg'])
    charts_row.pack(fill=tk.X, padx=15, pady=5)
    charts_row.columnconfigure(0, weight=1)
    charts_row.columnconfigure(1, weight=1)

    self.dash_views_chart_frame = self._dash_chart_host(
        charts_row, "📈 Рост просмотров", self.colors['success'], 0
    )
    self.dash_subs_chart_frame = self._dash_chart_host(
        charts_row, "👥 Рост подписчиков", self.colors['accent'], 1
    )

    cols = tk.Frame(parent, bg=self.colors['bg'])
    cols.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
    cols.columnconfigure(0, weight=1)
    cols.columnconfigure(1, weight=1)

    left = tk.Frame(cols, bg=self.colors['bg'])
    left.grid(row=0, column=0, sticky="nsew", padx=5)
    right = tk.Frame(cols, bg=self.colors['bg'])
    right.grid(row=0, column=1, sticky="nsew", padx=5)

    proxy_content, _, _ = self.create_rounded_card(
        left, "🌐 Прокси и сервер", self.colors['accent'], fill=tk.X
    )
    self.dash_proxy_text = tk.Text(
        proxy_content, height=8, wrap=tk.WORD,
        bg=self.colors['card_bg'], fg=self.colors['fg'],
        font=('Segoe UI', 9), relief=tk.FLAT, padx=12, pady=10, borderwidth=0
    )
    self.dash_proxy_text.pack(fill=tk.BOTH, expand=True)
    self.dash_proxy_text.config(state=tk.DISABLED)

    notif_content, _, _ = self.create_rounded_card(
        left, "🔔 Уведомления", self.colors['warning'], fill=tk.X
    )
    self.dash_notif_text = tk.Text(
        notif_content, height=6, wrap=tk.WORD,
        bg=self.colors['card_bg'], fg=self.colors['fg'],
        font=('Segoe UI', 9), relief=tk.FLAT, padx=12, pady=10, borderwidth=0
    )
    self.dash_notif_text.pack(fill=tk.BOTH, expand=True)
    self.dash_notif_text.config(state=tk.DISABLED)

    actions_content, _, _ = self.create_rounded_card(
        right, "⚡ Быстрые действия", self.colors['success'], fill=tk.X
    )
    actions_inner = tk.Frame(actions_content, bg=self.colors['card_bg'])
    actions_inner.pack(fill=tk.X, padx=15, pady=15)

    buttons = [
        ("🔄 Парсинг статистики", self.run_stats_parser, self.colors['accent']),
        ("👤 Обновить аккаунты", self.refresh_accounts, self.colors['success']),
        ("💾 Экспорт", self.show_export_menu, self.colors['warning']),
        ("📅 Планировщик", self.open_scheduler, self.colors['text_secondary']),
        ("🎨 Сменить тему", self.show_theme_menu, self.colors['accent']),
        ("ℹ️ О программе", self.show_about, self.colors['text_secondary']),
    ]
    for text, cmd, color in buttons:
        self.create_modern_button(actions_inner, text, cmd, color).pack(fill=tk.X, pady=4)

    recent_content, _, _ = self.create_rounded_card(
        right, "📋 Последняя активность", self.colors['text_secondary'],
        fill=tk.BOTH, expand=True
    )
    self.dash_activity_text = tk.Text(
        recent_content, height=10, wrap=tk.WORD,
        bg=self.colors['card_bg'], fg=self.colors['fg'],
        font=('Consolas', 9), relief=tk.FLAT, padx=12, pady=10, borderwidth=0
    )
    self.dash_activity_text.pack(fill=tk.BOTH, expand=True)
    self.dash_activity_text.config(state=tk.DISABLED)

    self.refresh_dashboard()


def _dash_chart_host(self, parent, title, accent, column):
    """Карточка-контейнер под график (grid)."""
    outer = tk.Frame(parent, bg=self.colors['bg'])
    outer.grid(row=0, column=column, sticky="nsew", padx=8, pady=8)

    shadow = tk.Frame(outer, bg='#d0d0d0' if self.colors['bg'] == '#f8f9fa' else '#3a3a3a')
    shadow.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    card = tk.Frame(shadow, bg=self.colors['card_bg'])
    card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

    header = tk.Frame(card, bg=accent, height=36)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    tk.Label(
        header, text=title, bg=accent, fg='white',
        font=('Segoe UI', 10, 'bold')
    ).pack(side=tk.LEFT, padx=12, pady=6)

    body = tk.Frame(card, bg=self.colors['card_bg'], height=220)
    body.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    body.pack_propagate(False)
    outer._body = body
    return outer


def _dash_kpi_card(self, parent, title, value, accent):
    outer = tk.Frame(parent, bg=self.colors['bg'])
    shadow = tk.Frame(outer, bg='#d0d0d0' if self.colors['bg'] == '#f8f9fa' else '#3a3a3a')
    shadow.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    card = tk.Frame(shadow, bg=self.colors['card_bg'])
    card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

    bar = tk.Frame(card, bg=accent, height=4)
    bar.pack(fill=tk.X)

    body = tk.Frame(card, bg=self.colors['card_bg'])
    body.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

    tk.Label(
        body, text=title, bg=self.colors['card_bg'],
        fg=self.colors['text_secondary'], font=('Segoe UI', 9)
    ).pack(anchor=tk.W)

    val_label = tk.Label(
        body, text=value, bg=self.colors['card_bg'],
        fg=self.colors['fg'], font=('Segoe UI', 16, 'bold')
    )
    val_label.pack(anchor=tk.W, pady=(6, 0))
    outer._value_label = val_label
    return outer


def _set_kpi(self, key, value):
    card = self.dash_kpi_frames.get(key)
    if card and hasattr(card, '_value_label'):
        card._value_label.config(text=str(value))


def _dash_set_text(widget, text):
    widget.config(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget.insert("1.0", text)
    widget.config(state=tk.DISABLED)


def _get_growth_series(self, days=30):
    """Агрегирует историю: по датам суммирует views/subs по всем каналам."""
    try:
        history = self.database.get_all_channels_history(days)
    except Exception:
        return [], [], []

    if not history:
        return [], [], []

    by_day_channel = {}
    for rec in history:
        url = rec[1] or ""
        subs = rec[3] or 0
        views = rec[4] or 0
        raw_date = rec[6] or ""
        try:
            if isinstance(raw_date, str):
                day = raw_date[:10]
            else:
                day = str(raw_date)[:10]
            datetime.strptime(day, "%Y-%m-%d")
        except Exception:
            continue
        key = (day, url)
        by_day_channel[key] = (int(subs or 0), int(views or 0))

    day_totals = defaultdict(lambda: {"subs": 0, "views": 0})
    for (day, _url), (subs, views) in by_day_channel.items():
        day_totals[day]["subs"] += subs
        day_totals[day]["views"] += views

    days_sorted = sorted(day_totals.keys())
    dates = []
    subs_series = []
    views_series = []
    for d in days_sorted:
        try:
            dates.append(datetime.strptime(d, "%Y-%m-%d"))
        except Exception:
            continue
        subs_series.append(day_totals[d]["subs"])
        views_series.append(day_totals[d]["views"])

    return dates, views_series, subs_series


def _render_line_chart(self, host_frame, dates, values, color, ylabel):
    """Рисует линейный график в host_frame._body."""
    body = getattr(host_frame, '_body', None)
    if body is None:
        return

    for w in body.winfo_children():
        w.destroy()

    if not HAS_MPL:
        tk.Label(
            body,
            text="Установите matplotlib:\npip install matplotlib",
            bg=self.colors['card_bg'],
            fg=self.colors['text_secondary'],
            font=('Segoe UI', 9),
            justify=tk.CENTER
        ).pack(expand=True)
        return

    if len(dates) < 2:
        tk.Label(
            body,
            text="Недостаточно данных для графика.\nЗапустите парсинг несколько раз\nв разные дни.",
            bg=self.colors['card_bg'],
            fg=self.colors['text_secondary'],
            font=('Segoe UI', 9),
            justify=tk.CENTER
        ).pack(expand=True)
        return

    bg = self.colors['card_bg']
    fg = self.colors['fg']
    grid_c = self.colors.get('border', '#dee2e6')

    fig = Figure(figsize=(5.2, 2.4), dpi=100)
    fig.patch.set_facecolor(bg)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)

    ax.plot(dates, values, color=color, linewidth=2.2, marker='o', markersize=4)
    ax.fill_between(dates, values, alpha=0.15, color=color)

    ax.set_ylabel(ylabel, color=fg, fontsize=8)
    ax.tick_params(colors=fg, labelsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(grid_c)
    ax.spines['left'].set_color(grid_c)
    ax.grid(True, alpha=0.25, color=grid_c)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    if len(dates) > 8:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6))
    fig.autofmt_xdate(rotation=30, ha='right')
    fig.tight_layout(pad=0.6)

    canvas = FigureCanvasTkAgg(fig, master=body)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    self._dash_chart_canvases.append(canvas)


def refresh_dashboard(self):
    if not hasattr(self, 'dash_kpi_frames'):
        return

    results = getattr(self, 'current_stats_results', []) or []
    total_channels = 0
    total_views = 0
    total_subs = 0
    for r in results:
        if 'error' in r:
            continue
        total_channels += 1
        try:
            total_views += self.stats_parser.parse_number(r.get('total_views', '0'))
            total_subs += self.stats_parser.parse_number(r.get('subscribers', '0'))
        except Exception:
            pass

    fmt = self.stats_parser.format_large_number
    self._set_kpi('channels', total_channels if total_channels else "—")
    self._set_kpi('views', fmt(total_views) if total_channels else "—")
    self._set_kpi('subs', fmt(total_subs) if total_channels else "—")

    accounts = getattr(self, 'current_accounts_data', []) or []
    self._set_kpi('accounts', len(accounts) if accounts else "—")

    dates, views_s, subs_s = self._get_growth_series(30)
    if hasattr(self, 'dash_views_chart_frame'):
        self._render_line_chart(
            self.dash_views_chart_frame, dates, views_s,
            self.colors['success'], "Просмотры"
        )
    if hasattr(self, 'dash_subs_chart_frame'):
        self._render_line_chart(
            self.dash_subs_chart_frame, dates, subs_s,
            self.colors['accent'], "Подписчики"
        )

    proxy = self.config.get('proxy', {})
    server = self.config.get('server', {})
    lines = []

    def _days_left(expiry):
        if not expiry:
            return None
        try:
            return (datetime.strptime(expiry, "%d.%m.%Y") - datetime.now()).days
        except ValueError:
            return None

    pe = proxy.get('expiry_date', '')
    pd = _days_left(pe)
    lines.append("📡 Прокси")
    lines.append(f"   Окончание: {pe or 'не указано'}")
    if pd is not None:
        if pd > 0:
            flag = " ⚠️" if pd <= 7 else ""
            lines.append(f"   Осталось: {pd} дн.{flag}")
        else:
            lines.append("   ⚠️ Истёк!")
    lines.append("")
    se = server.get('expiry_date', '')
    sd = _days_left(se)
    lines.append("🖥️ Сервер")
    lines.append(f"   Окончание: {se or 'не указано'}")
    if sd is not None:
        if sd > 0:
            flag = " ⚠️" if sd <= 7 else ""
            lines.append(f"   Осталось: {sd} дн.{flag}")
        else:
            lines.append("   ⚠️ Истёк!")

    if hasattr(self, 'dash_proxy_text'):
        _dash_set_text(self.dash_proxy_text, "\n".join(lines))

    notif_lines = []
    try:
        notifications = self.database.get_unread_notifications()
        if notifications:
            for n in notifications[:8]:
                notif_lines.append(f"• {n[2]}")
            if len(notifications) > 8:
                notif_lines.append(f"... ещё {len(notifications) - 8}")
        else:
            notif_lines.append("Нет непрочитанных уведомлений")
    except Exception as e:
        notif_lines.append(f"Ошибка: {e}")

    if hasattr(self, 'dash_notif_text'):
        _dash_set_text(self.dash_notif_text, "\n".join(notif_lines))

    activity = []
    try:
        ops = self.database.get_operations_log(12)
        if ops:
            for op in ops:
                ts = (op[3] or "")[:16]
                otype = op[1] or ""
                desc = op[2] or ""
                activity.append(f"{ts}  {otype}: {desc}")
        else:
            activity.append("Пока нет операций. Запустите парсинг или обновите аккаунты.")
    except Exception as e:
        activity.append(f"Ошибка загрузки лога: {e}")

    if hasattr(self, 'dash_activity_text'):
        _dash_set_text(self.dash_activity_text, "\n".join(activity))

    self.set_status("Главная панель обновлена")


def install_dashboard(app_cls):
    """Добавляет методы дашборда и патчит create_ui."""
    app_cls.create_dashboard_tab = create_dashboard_tab
    app_cls._build_dashboard_content = _build_dashboard_content
    app_cls._dash_kpi_card = _dash_kpi_card
    app_cls._dash_chart_host = _dash_chart_host
    app_cls._set_kpi = _set_kpi
    app_cls._get_growth_series = _get_growth_series
    app_cls._render_line_chart = _render_line_chart
    app_cls.refresh_dashboard = refresh_dashboard

    original_create_ui = app_cls.create_ui

    def create_ui_with_dashboard(self):
        original_create_ui(self)
        try:
            self.create_dashboard_tab()
        except Exception as e:
            print(f"Dashboard init error: {e}")

    app_cls.create_ui = create_ui_with_dashboard

    if hasattr(app_cls, '_update_stats_ui'):
        orig_stats = app_cls._update_stats_ui

        def stats_and_refresh(self, results):
            orig_stats(self, results)
            try:
                self.refresh_dashboard()
            except Exception:
                pass

        app_cls._update_stats_ui = stats_and_refresh

    if hasattr(app_cls, 'refresh_accounts'):
        orig_acc = app_cls.refresh_accounts

        def accounts_and_refresh(self):
            orig_acc(self)
            try:
                if hasattr(self, 'dash_kpi_frames'):
                    self.refresh_dashboard()
            except Exception:
                pass

        app_cls.refresh_accounts = accounts_and_refresh

    return app_cls
