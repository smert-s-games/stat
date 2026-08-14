"""Стили KPI как на web-dashboard — цветные карточки."""
import tkinter as tk


def _dash_kpi_card(self, parent, title, value, accent):
    outer = tk.Frame(parent, bg=self.colors['bg'])
    card = tk.Frame(outer, bg=accent, height=110)
    card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
    card.pack_propagate(False)

    body = tk.Frame(card, bg=accent)
    body.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

    tk.Label(body, text=title, bg=accent, fg='#ffffff', font=('Segoe UI', 9)).pack(anchor=tk.W)
    val_label = tk.Label(body, text=value, bg=accent, fg='#ffffff', font=('Segoe UI', 22, 'bold'))
    val_label.pack(anchor=tk.W, pady=(8, 0))
    outer._value_label = val_label
    return outer


def _build_dashboard_content_colored(self):
    parent = self.dashboard_inner
    for w in parent.winfo_children():
        w.destroy()
    self._dash_chart_canvases = []

    header = tk.Frame(parent, bg=self.colors['bg'])
    header.pack(fill=tk.X, padx=20, pady=(20, 10))
    tk.Label(
        header, text="Панель управления",
        bg=self.colors['bg'], fg=self.colors['fg'],
        font=('Segoe UI', 18, 'bold')
    ).pack(side=tk.LEFT)
    self.create_modern_button(
        header, "🔄 Обновить", self.refresh_dashboard, self.colors['accent'], small=True
    ).pack(side=tk.RIGHT, padx=5)

    kpi_row = tk.Frame(parent, bg=self.colors['bg'])
    kpi_row.pack(fill=tk.X, padx=15, pady=5)
    self.dash_kpi_frames = {}
    kpis = [
        ("channels", "📺 Каналы", "—", "#4f46e5"),
        ("views", "👀 Просмотры", "—", "#06b6d4"),
        ("subs", "👥 Подписчики", "—", "#f59e0b"),
        ("accounts", "👤 Аккаунты", "—", "#10b981"),
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


def install_dashboard_style(app_cls):
    app_cls._dash_kpi_card = _dash_kpi_card
    app_cls._build_dashboard_content = _build_dashboard_content_colored
    return app_cls
