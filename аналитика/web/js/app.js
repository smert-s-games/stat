const App = {
  selectedScript: null, parsing: false, _es: null,
  async api(method, ...args) {
    try {
      const res = await fetch("/api/rpc", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ method, args }) });
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        const err = (data && data.error) || res.statusText;
        App.setStatus("Ошибка: " + err);
        return data && data.result !== undefined ? data.result : { error: err };
      }
      return data.result;
    } catch (e) { console.error(method, e); App.setStatus("Ошибка сети: " + e); return null; }
  },
  connectEvents() {
    if (App._es) try { App._es.close(); } catch (_) {}
    const es = new EventSource("/api/events"); App._es = es;
    es.addEventListener("parse_progress", (ev) => { try { App.onParseProgress(JSON.parse(ev.data)); } catch (_) {} });
    es.addEventListener("parse_done", (ev) => { try { App.onParseDone(JSON.parse(ev.data)); } catch (_) {} });
    es.addEventListener("video_log", (ev) => { try { App.onVideoLog(JSON.parse(ev.data)); } catch (_) {} });
    es.addEventListener("video_done", (ev) => { try { App.onVideoDone(JSON.parse(ev.data)); } catch (_) {} });
    es.addEventListener("bot_log", (ev) => { try { App.onBotLog(JSON.parse(ev.data)); } catch (_) {} });
  },
  setStatus(t) { const el = document.getElementById("status-text"); if (el) el.textContent = t; },
  navigate(page) {
    document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
    const section = document.getElementById("page-" + page); if (section) section.classList.add("active");
    const nav = document.querySelector(`.nav-item[data-page="${page}"]`); if (nav) nav.classList.add("active");
    if (page === "expenses") App.loadExpenses();
  },
  async init() {
    App.connectEvents();
    document.querySelectorAll(".nav-item").forEach((btn) => btn.addEventListener("click", () => App.navigate(btn.dataset.page)));
    document.getElementById("btn-parse").onclick = () => App.startParse();
    document.getElementById("btn-export").onclick = () => App.exportStats();
    document.getElementById("btn-theme").onclick = () => App.toggleTheme();
    const np = document.getElementById("btn-new-project"); if (np) np.onclick = () => App.newProject();
    const ps = document.getElementById("project-select"); if (ps) ps.onchange = (e) => App.switchProject(e.target.value);
    const ss = document.getElementById("stats-sort"); if (ss) ss.onchange = (e) => App.applyStatsSort(e.target.value);
    const as = document.getElementById("accounts-sort"); if (as) as.onchange = (e) => App.applyAccountsSort(e.target.value);
    await App.loadProjects(); await App.loadConfig(); await App.loadCachedStats();
    await App.refreshHome(); await App.refreshAccounts(); await App.loadVideoScripts(); await App.loadExpenses();
  },
  async loadProjects() {
    const data = await App.api("list_projects"); const sel = document.getElementById("project-select");
    if (!data || !sel) return;
    sel.innerHTML = (data.projects || []).map((p) => `<option value="${esc(p.id)}" ${p.id === data.active_id ? "selected" : ""}>${esc(p.name)}</option>`).join("");
  },
  async newProject() { const name = prompt("Название проекта:"); if (!name || !name.trim()) return; await App.api("create_project", name.trim()); await App.reloadAll(); },
  async switchProject(pid) { if (!pid) return; await App.api("switch_project", pid); await App.reloadAll(); },
  async reloadAll() {
    await App.loadProjects(); await App.loadConfig(); await App.loadCachedStats();
    await App.refreshHome(); await App.refreshAccounts(); await App.loadVideoScripts(); await App.loadExpenses();
    App.setStatus("Проект переключён");
  },
  async loadConfig() {
    const cfg = await App.api("get_config"); if (!cfg) return;
    document.documentElement.setAttribute("data-theme", cfg.theme || "light");
    document.getElementById("status-theme").textContent = "Тема: " + (cfg.theme === "dark" ? "Тёмная" : "Светлая");
    document.getElementById("links-file").value = cfg.links_file || "";
    document.getElementById("proxy-purchase").value = (cfg.proxy && cfg.proxy.purchase_date) || "";
    document.getElementById("proxy-expiry").value = (cfg.proxy && cfg.proxy.expiry_date) || "";
    document.getElementById("server-purchase").value = (cfg.server && cfg.server.purchase_date) || "";
    document.getElementById("server-expiry").value = (cfg.server && cfg.server.expiry_date) || "";
    document.getElementById("tg-token").value = cfg.telegram_bot_token || "";
    document.getElementById("tg-chat").value = cfg.telegram_chat_id || "";
    if (cfg.stats_sort && document.getElementById("stats-sort")) document.getElementById("stats-sort").value = cfg.stats_sort;
    if (cfg.accounts_sort && document.getElementById("accounts-sort")) document.getElementById("accounts-sort").value = cfg.accounts_sort;
    const pn = document.getElementById("home-project-name"); if (pn) pn.textContent = cfg.project_name ? "· " + cfg.project_name : "";
  },
  async loadCachedStats() {
    const results = await App.api("get_cached_stats");
    if (results && results.length) {
      App.renderStats(results);
      const log = document.getElementById("stats-log");
      if (log) log.textContent = "Сохранённая сессия: " + results.length + " каналов.\n";
    }
  },
  async refreshHome() {
    const data = await App.api("get_dashboard"); if (!data) return;
    document.getElementById("kpi-channels").textContent = data.channels ?? "—";
    document.getElementById("kpi-views").textContent = data.views ?? "—";
    document.getElementById("kpi-subs").textContent = data.subs ?? "—";
    document.getElementById("kpi-accounts").textContent = data.accounts ?? "—";
    document.getElementById("home-proxy").innerHTML = data.proxy_html || "<span class='empty'>Нет данных</span>";
  },
  async toggleTheme() {
    const res = await App.api("toggle_theme"); if (!res) return;
    document.documentElement.setAttribute("data-theme", res.theme);
    document.getElementById("status-theme").textContent = "Тема: " + (res.theme === "dark" ? "Тёмная" : "Светлая");
  },
  async startParse() {
    if (App.parsing) { alert("Парсинг уже выполняется"); return; }
    const links = document.getElementById("links-file").value.trim();
    if (links) await App.api("set_links_file", links);
    App.parsing = true;
    const btn = document.getElementById("stats-parse-btn"); if (btn) btn.disabled = true;
    document.getElementById("stats-log").textContent = "Запуск парсинга…\n";
    App.setStatus("Парсинг…"); App.navigate("stats");
    const res = await App.api("start_parse");
    if (res && res.error) {
      document.getElementById("stats-log").textContent += "\n❌ " + res.error;
      App.setStatus("Ошибка"); App.parsing = false; if (btn) btn.disabled = false;
    }
  },
  onParseProgress(msg) { const log = document.getElementById("stats-log"); log.textContent += msg; log.scrollTop = log.scrollHeight; },
  onParseDone(results) {
    App.parsing = false; const btn = document.getElementById("stats-parse-btn"); if (btn) btn.disabled = false;
    App.renderStats(results || []); App.refreshHome();
    App.setStatus("Парсинг завершён: " + (results ? results.length : 0) + " (сохранено)");
  },
  renderStats(results) {
    const tbody = document.getElementById("stats-tbody");
    if (!results || !results.length) { tbody.innerHTML = '<tr><td colspan="7" class="empty">Нет данных</td></tr>'; return; }
    tbody.innerHTML = results.map((r) => {
      if (r.error) return `<tr><td>${esc(r.channel_name||r.url||"")}</td><td>—</td><td>—</td><td>—</td><td>${esc(r.url||"")}</td><td>—</td><td><span class="badge badge-err">❌ ${esc(String(r.error))}</span></td></tr>`;
      return `<tr><td>${esc(r.channel_name||"")}</td><td>${esc(r.subscribers||"0")}</td><td>${esc(r.total_views||"0")}</td><td>${esc(r.videos_count||"0")}</td><td><a href="#" onclick="return App.openUrl('${esc(r.url||"")}')">${esc(r.url||"")}</a></td><td>${esc(r.email||"—")}</td><td><span class="badge badge-ok">✅</span></td></tr>`;
    }).join("");
  },
  async applyStatsSort(mode) { const results = await App.api("sort_stats_results", mode); if (results) App.renderStats(results); },
  openUrl(url) { App.api("open_url", url); return false; },
  async pickLinksFile() {
    const path = prompt("Полный путь к links.txt:", document.getElementById("links-file").value || "");
    if (path === null || !path.trim()) return;
    document.getElementById("links-file").value = path.trim();
    await App.api("set_links_file", path.trim());
  },
  async exportStats() {
    const res = await App.api("export_stats");
    if (res && res.ok) App.setStatus("Экспорт: " + res.path); else if (res && res.error) alert(res.error);
  },
  async refreshAccounts() {
    const data = await App.api("refresh_accounts"); if (!data) return;
    if (data.error) { alert(data.error); return; }
    const foldersEl = document.getElementById("accounts-folders");
    if (data.folders && data.folders.length) {
      foldersEl.innerHTML = data.folders.map((f) => `<div class="script-item"><div class="script-path">${esc(f)}</div><button class="btn btn-ghost btn-sm" onclick='App.removeFolder(${JSON.stringify(f)})'>➖</button></div>`).join("");
    } else foldersEl.innerHTML = '<div class="empty">Нет папок</div>';
    const tbody = document.getElementById("accounts-tbody");
    if (!data.accounts || !data.accounts.length) tbody.innerHTML = '<tr><td colspan="6" class="empty">Нет данных</td></tr>';
    else tbody.innerHTML = data.accounts.map((a) => `<tr><td>${esc(a.name)}</td><td>${esc(a.folder_short||a.folder||"")}</td><td>${esc(a.materials_count)}</td><td>${esc(a.size)}</td><td>${esc(a.modified_date)}</td><td>${esc(a.quality_score)}</td></tr>`).join("");
    App.refreshHome();
  },
  async applyAccountsSort(mode) {
    const accounts = await App.api("sort_accounts_results", mode); if (!accounts) return;
    document.getElementById("accounts-tbody").innerHTML = accounts.map((a) => `<tr><td>${esc(a.name)}</td><td>${esc(a.folder_short||a.folder||"")}</td><td>${esc(a.materials_count)}</td><td>${esc(a.size)}</td><td>${esc(a.modified_date)}</td><td>${esc(a.quality_score)}</td></tr>`).join("") || '<tr><td colspan="6" class="empty">Нет данных</td></tr>';
  },
  async addAccountsFolder() { const path = prompt("Путь к папке аккаунтов:"); if (!path || !path.trim()) return; await App.api("add_accounts_folder", path.trim()); App.refreshAccounts(); },
  async removeFolder(path) { await App.api("remove_accounts_folder", path); App.refreshAccounts(); },
  async loadVideoScripts() {
    const scripts = await App.api("get_video_scripts"); const el = document.getElementById("video-scripts"); App.selectedScript = null;
    if (!scripts || !scripts.length) { el.innerHTML = '<div class="empty">Нет скриптов</div>'; return; }
    el.innerHTML = scripts.map((s, i) => `<div class="script-item" onclick="App.selectScript(${i}, this)"><div><strong>${esc(s.name)}</strong><div class="script-path">${esc(s.path)}</div></div><button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();App.removeScript(${i})">➖</button></div>`).join("");
  },
  selectScript(idx, el) { document.querySelectorAll("#video-scripts .script-item").forEach((x) => x.classList.remove("selected")); el.classList.add("selected"); App.selectedScript = idx; },
  async addVideoScript() { const path = prompt("Путь к .py:"); if (!path || !path.trim()) return; await App.api("add_video_script", path.trim()); App.loadVideoScripts(); },
  async removeScript(idx) { await App.api("remove_video_script", idx); App.loadVideoScripts(); },
  async runVideoScript() {
    if (App.selectedScript === null) { alert("Выберите скрипт"); return; }
    document.getElementById("video-run-btn").disabled = true; document.getElementById("video-stop-btn").disabled = false;
    document.getElementById("video-log").textContent = "Запуск…\n"; await App.api("run_video_script", App.selectedScript);
  },
  async stopVideoScript() { await App.api("stop_video_script"); },
  onVideoLog(line) { const log = document.getElementById("video-log"); log.textContent += line + "\n"; log.scrollTop = log.scrollHeight; },
  onVideoDone(ok) { document.getElementById("video-run-btn").disabled = false; document.getElementById("video-stop-btn").disabled = true; App.setStatus(ok ? "Скрипт завершён" : "Остановлен"); },
  async saveProxy() {
    const res = await App.api("save_proxy", { purchase_date: document.getElementById("proxy-purchase").value.trim(), expiry_date: document.getElementById("proxy-expiry").value.trim() });
    const msg = document.getElementById("proxy-save-msg");
    if (res && res.ok) { if (msg) msg.textContent = "✓ Сохранено"; App.setStatus("Прокси сохранён"); App.refreshHome(); }
    else if (msg) msg.textContent = "Ошибка";
  },
  async saveServer() {
    const res = await App.api("save_server", { purchase_date: document.getElementById("server-purchase").value.trim(), expiry_date: document.getElementById("server-expiry").value.trim() });
    const msg = document.getElementById("server-save-msg");
    if (res && res.ok) { if (msg) msg.textContent = "✓ Сохранено"; App.setStatus("Сервер сохранён"); App.refreshHome(); }
    else if (msg) msg.textContent = "Ошибка";
  },
  async saveTelegram() { await App.api("save_telegram", { token: document.getElementById("tg-token").value, chat_id: document.getElementById("tg-chat").value }); App.setStatus("Telegram сохранён"); },
  async loadExpenses() {
    const data = await App.api("get_expenses"); if (!data) return;
    const tot = document.getElementById("exp-total"); if (tot) tot.textContent = "Итого: " + (data.total || 0).toFixed(2) + " · " + (data.count || 0);
    const tbody = document.getElementById("expenses-tbody"); if (!tbody) return;
    const items = data.items || [];
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="5" class="empty">Нет расходов</td></tr>'; return; }
    tbody.innerHTML = items.slice().reverse().map((e) => `<tr><td>${esc(e.date)}</td><td>${esc(e.category||"—")}</td><td>${esc(e.description||"")}</td><td>${Number(e.amount).toFixed(2)}</td><td><button class="btn btn-ghost btn-sm" onclick="App.deleteExpense('${esc(e.id)}')">🗑️</button></td></tr>`).join("");
  },
  async addExpense() {
    const res = await App.api("add_expense", document.getElementById("exp-amount").value, document.getElementById("exp-desc").value, document.getElementById("exp-cat").value, document.getElementById("exp-date").value);
    if (res && res.error) { alert(res.error); return; }
    document.getElementById("exp-amount").value = ""; document.getElementById("exp-desc").value = "";
    App.loadExpenses(); App.refreshHome();
  },
  async deleteExpense(id) { await App.api("delete_expense", id); App.loadExpenses(); App.refreshHome(); },
  async startBot() { document.getElementById("tg-start").disabled = true; document.getElementById("tg-stop").disabled = false; await App.api("start_bot"); },
  async stopBot() { await App.api("stop_bot"); document.getElementById("tg-start").disabled = false; document.getElementById("tg-stop").disabled = true; },
  onBotLog(msg) { const log = document.getElementById("tg-log"); log.textContent += msg + "\n"; log.scrollTop = log.scrollHeight; },
};
function esc(s) { return String(s ?? "").replace(/&/g,"&").replace(/</g,"<").replace(/>/g,">").replace(/"/g,"""); }
document.addEventListener("DOMContentLoaded", () => App.init());
