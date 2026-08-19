const App = {
  selectedScript: null,
  parsing: false,
  viewMode: "project",
  _es: null,

  async api(method, ...args) {
    try {
      const res = await fetch("/api/rpc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method: method, args: args }),
      });
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        const err = (data && data.error) || res.statusText;
        App.setStatus("Ошибка: " + err);
        return data && data.result !== undefined ? data.result : { error: err };
      }
      return data.result;
    } catch (e) {
      console.error(method, e);
      App.setStatus("Ошибка сети: " + e);
      return null;
    }
  },

  connectEvents() {
    if (App._es) {
      try { App._es.close(); } catch (e) {}
    }
    const es = new EventSource("/api/events");
    App._es = es;
    es.addEventListener("parse_progress", function (ev) {
      try { App.onParseProgress(JSON.parse(ev.data)); } catch (e) {}
    });
    es.addEventListener("parse_done", function (ev) {
      try { App.onParseDone(JSON.parse(ev.data)); } catch (e) {}
    });
    es.addEventListener("video_log", function (ev) {
      try { App.onVideoLog(JSON.parse(ev.data)); } catch (e) {}
    });
    es.addEventListener("video_done", function (ev) {
      try { App.onVideoDone(JSON.parse(ev.data)); } catch (e) {}
    });
    es.addEventListener("bot_log", function (ev) {
      try { App.onBotLog(JSON.parse(ev.data)); } catch (e) {}
    });
  },

  setStatus(t) {
    const el = document.getElementById("status-text");
    if (el) el.textContent = "UI 20260819h · " + t;
  },

  navigate(page) {
    document.querySelectorAll(".page").forEach(function (p) { p.classList.remove("active"); });
    document.querySelectorAll(".nav-item").forEach(function (n) { n.classList.remove("active"); });
    const section = document.getElementById("page-" + page);
    if (section) section.classList.add("active");
    const nav = document.querySelector('.nav-item[data-page="' + page + '"]');
    if (nav) nav.classList.add("active");
    if (page === "expenses") App.loadExpenses();
  },

  async init() {
    try {
      App.connectEvents();
      document.querySelectorAll(".nav-item").forEach(function (btn) {
        btn.addEventListener("click", function () { App.navigate(btn.dataset.page); });
      });
      var el;
      el = document.getElementById("btn-parse"); if (el) el.onclick = function () { App.startParse(); };
      el = document.getElementById("btn-export"); if (el) el.onclick = function () { App.exportStats(); };
      el = document.getElementById("btn-theme"); if (el) el.onclick = function () { App.toggleTheme(); };
      el = document.getElementById("btn-new-project"); if (el) el.onclick = function () { App.newProject(); };
      el = document.getElementById("project-select"); if (el) el.onchange = function (e) { App.switchProject(e.target.value); };
      el = document.getElementById("stats-sort"); if (el) el.onchange = function (e) { App.applyStatsSort(e.target.value); };
      el = document.getElementById("accounts-sort"); if (el) el.onchange = function (e) { App.applyAccountsSort(e.target.value); };
      el = document.getElementById("btn-ch-select-all"); if (el) el.onclick = function () { App.selectAllChannels(true); };
      el = document.getElementById("btn-ch-select-none"); if (el) el.onclick = function () { App.selectAllChannels(false); };
      el = document.getElementById("btn-ch-delete"); if (el) el.onclick = function () { App.deleteSelectedChannels(); };
      el = document.getElementById("btn-ch-import"); if (el) el.onclick = function () { App.importChannels(); };
      el = document.getElementById("ch-check-all"); if (el) el.onchange = function () { App.selectAllChannels(!!el.checked); };
      el = document.getElementById("channels-search"); if (el) el.oninput = function () { App.filterChannels(); };
      el = document.getElementById("btn-acc-select-all"); if (el) el.onclick = function () { App.selectAllAccounts(true); };
      el = document.getElementById("btn-acc-select-none"); if (el) el.onclick = function () { App.selectAllAccounts(false); };
      el = document.getElementById("btn-acc-delete"); if (el) el.onclick = function () { App.deleteSelectedAccounts(); };
      el = document.getElementById("acc-check-all"); if (el) el.onchange = function () { App.selectAllAccounts(!!el.checked); };
      el = document.getElementById("accounts-search"); if (el) el.oninput = function () { App.filterAccounts(); };

      await App.loadProjects();
      await App.loadConfig();
      await App.loadCachedStats();
      await App.refreshHome();
      await App.refreshAccounts();
      await App.loadVideoScripts();
      await App.loadExpenses();
      App.setStatus("Готово");
    } catch (e) {
      console.error("init error", e);
      App.setStatus("Ошибка инициализации: " + e);
    }
  },

  async loadProjects() {
    const data = await App.api("list_projects");
    const sel = document.getElementById("project-select");
    if (!data || !sel) return;
    var opts = '<option value="__all__">Все проекты</option>';
    opts += (data.projects || []).map(function (p) {
      return '<option value="' + esc(p.id) + '"' + (p.id === data.active_id ? " selected" : "") + '>' + esc(p.name) + '</option>';
    }).join("");
    sel.innerHTML = opts;
  },

  async newProject() {
    var name = prompt("Имя проекта:");
    if (!name || !name.trim()) return;
    await App.api("create_project", name.trim());
    await App.loadProjects();
    await App.reloadAll();
  },

  async switchProject(pid) {
    if (!pid) return;
    if (pid === "__all__") {
      if (App.showAllProjectsStats) await App.showAllProjectsStats();
      return;
    }
    App.viewMode = "project";
    await App.api("switch_project", pid);
    await App.reloadAll();
  },

  async showAllProjectsStats() {
    App.viewMode = "all";
    App.navigate("home");
    var dash = await App.api("get_all_projects_dashboard");
    if (!dash || dash.error) {
      alert("Не удалось загрузить сводку: " + ((dash && dash.error) || ""));
      return;
    }
    var setT = function (id, val) {
      var e = document.getElementById(id);
      if (e) e.textContent = val != null ? val : "—";
    };
    setT("kpi-channels", dash.channels);
    setT("kpi-views", dash.views);
    setT("kpi-subs", dash.subs);
    setT("kpi-accounts", dash.accounts);
    var pn = document.getElementById("home-project-name");
    if (pn) pn.textContent = "· Все проекты (" + (dash.projects_count || 0) + ")";
    var hp = document.getElementById("home-proxy");
    if (hp) hp.innerHTML = dash.proxy_html || "";
  },

  async reloadAll() {
    await App.loadConfig();
    await App.loadCachedStats();
    await App.refreshAccounts();
    await App.refreshHome();
    await App.loadExpenses();
    await App.loadVideoScripts();
  },

  async loadConfig() {
    var cfg = await App.api("get_config");
    if (!cfg) return;
    if (cfg.theme || cfg.ui_theme) document.documentElement.setAttribute("data-theme", cfg.ui_theme || cfg.theme);
    var set = function (id, val) {
      var e = document.getElementById(id);
      if (e && val != null) e.value = val;
    };
    set("links-file", cfg.links_file);
    set("proxy-purchase", cfg.proxy && cfg.proxy.purchase_date);
    set("proxy-expiry", cfg.proxy && cfg.proxy.expiry_date);
    set("server-purchase", cfg.server && cfg.server.purchase_date);
    set("server-expiry", cfg.server && cfg.server.expiry_date);
    set("tg-token", cfg.telegram_bot_token);
    set("tg-chat", cfg.telegram_chat_id);
  },

  async loadCachedStats() {
    var results = await App.api("get_cached_stats");
    App.renderStats(Array.isArray(results) ? results : []);
  },

  async refreshHome() {
    var data = await App.api("get_dashboard");
    if (!data) return;
    var setT = function (id, val) {
      var e = document.getElementById(id);
      if (e) e.textContent = val != null ? val : "—";
    };
    setT("kpi-channels", data.channels);
    setT("kpi-views", data.views);
    setT("kpi-subs", data.subs);
    setT("kpi-accounts", data.accounts);
    var hp = document.getElementById("home-proxy");
    if (hp) hp.innerHTML = data.proxy_html || "";
    var pn = document.getElementById("home-project-name");
    if (pn) pn.textContent = data.project_name ? "· " + data.project_name : "";
  },

  async toggleTheme() {
    var res = await App.api("toggle_theme");
    if (!res) return;
    document.documentElement.setAttribute("data-theme", res.theme);
  },

  async startParse() {
    var links = (document.getElementById("links-file") || {}).value;
    if (links) await App.api("set_links_file", links);
    var res = await App.api("start_parse");
    if (res && res.error) alert(res.error);
  },

  onParseProgress(msg) {
    var log = document.getElementById("stats-log");
    if (log) {
      log.textContent += (typeof msg === "string" ? msg : (msg && msg.msg) || "") + "\n";
      log.scrollTop = log.scrollHeight;
    }
  },

  onParseDone(results) {
    App.renderStats(results || []);
    App.refreshHome();
    App.setStatus("Парсинг завершён");
  },

  renderStats(results) {
    App._channelsCache = Array.isArray(results) ? results.slice() : [];
    if (App._paintChannels) App._paintChannels(App._channelsCache);
    else {
      var tbody = document.getElementById("stats-tbody");
      if (!tbody) return;
      if (!results || !results.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty">Нет данных</td></tr>';
        return;
      }
      tbody.innerHTML = results.map(function (r) {
        return "<tr><td></td><td>" + esc(r.channel_name || "") + "</td><td>" + esc(r.subscribers || "0") +
          "</td><td>" + esc(r.total_views || "0") + "</td><td>" + esc(r.videos_count || "0") +
          "</td><td>" + esc(r.url || "") + "</td><td>" + esc(r.email || "—") + "</td><td></td><td></td></tr>";
      }).join("");
    }
  },

  async applyStatsSort(mode) {
    const results = await App.api("sort_stats_results", mode);
    if (results) App.renderStats(results);
  },

  openUrl(url) { App.api("open_url", url); return false; },

  async pickLinksFile() {
    var p = prompt("Путь к файлу ссылок:");
    if (!p) return;
    var inp = document.getElementById("links-file");
    if (inp) inp.value = p;
    await App.api("set_links_file", p);
  },

  async exportStats() {
    await App.api("export_stats");
  },

  async refreshAccounts() {
    const data = await App.api("refresh_accounts");
    if (!data) return;
    if (data.error) { alert(data.error); return; }
    App._accountsCache = data.accounts || [];
    if (App._paintAccounts) App._paintAccounts(App._accountsCache);
    App.refreshHome();
  },

  async applyAccountsSort(mode) {
    const accounts = await App.api("sort_accounts_results", mode);
    if (!accounts) return;
    App._accountsCache = accounts;
    if (App._paintAccounts) App._paintAccounts(accounts);
  },

  async addAccountsFolder() {
    var path = prompt("Путь к папке аккаунтов:");
    if (!path || !path.trim()) return;
    await App.api("add_accounts_folder", path.trim());
    App.refreshAccounts();
  },

  async removeFolder(path) {
    await App.api("remove_accounts_folder", path);
    App.refreshAccounts();
  },

  async loadVideoScripts() {
    const scripts = await App.api("get_video_scripts");
    var el = document.getElementById("video-scripts");
    if (!el) return;
    App._videoScripts = scripts || [];
    if (!scripts || !scripts.length) {
      el.innerHTML = '<div class="empty">Нет скриптов</div>';
      return;
    }
    el.innerHTML = scripts.map(function (s, i) {
      return '<div class="script-item" data-idx="' + i + '"><div><strong>' + esc(s.name) +
        '</strong><div class="script-path">' + esc(s.path) + '</div></div></div>';
    }).join("");
    el.querySelectorAll(".script-item").forEach(function (item) {
      item.onclick = function () {
        App.selectedScript = parseInt(item.getAttribute("data-idx"), 10);
        el.querySelectorAll(".script-item").forEach(function (x) { x.classList.remove("selected"); });
        item.classList.add("selected");
      };
    });
  },

  async addVideoScript() {
    var path = prompt("Путь к .py:");
    if (!path || !path.trim()) return;
    await App.api("add_video_script", path.trim());
    App.loadVideoScripts();
  },

  async runVideoScript() {
    if (App.selectedScript == null) { alert("Выберите скрипт"); return; }
    await App.api("run_video_script", App.selectedScript);
  },

  async stopVideoScript() { await App.api("stop_video_script"); },

  onVideoLog(line) {
    var log = document.getElementById("video-log");
    if (log) log.textContent += (typeof line === "string" ? line : (line && line.msg) || "") + "\n";
  },

  onVideoDone(ok) {
    App.setStatus(ok ? "Скрипт завершён" : "Скрипт остановлен");
  },

  async saveProxy() {
    var purchase = (document.getElementById("proxy-purchase") || {}).value || "";
    var expiry = (document.getElementById("proxy-expiry") || {}).value || "";
    await App.api("save_proxy_dates", purchase, expiry);
    var msg = document.getElementById("proxy-save-msg");
    if (msg) msg.textContent = "Сохранено";
  },

  async saveServer() {
    var purchase = (document.getElementById("server-purchase") || {}).value || "";
    var expiry = (document.getElementById("server-expiry") || {}).value || "";
    await App.api("save_server_dates", purchase, expiry);
    var msg = document.getElementById("server-save-msg");
    if (msg) msg.textContent = "Сохранено";
  },

  async saveTelegram() {
    var token = (document.getElementById("tg-token") || {}).value || "";
    var chat = (document.getElementById("tg-chat") || {}).value || "";
    await App.api("save_telegram", token, chat);
  },

  async loadExpenses() {
    var data = await App.api("get_expenses");
    var tbody = document.getElementById("expenses-tbody");
    if (!tbody) return;
    var items = (data && data.items) || [];
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty">Нет</td></tr>';
      return;
    }
    tbody.innerHTML = items.map(function (e) {
      return "<tr><td>" + esc(e.date) + "</td><td>" + esc(e.category) + "</td><td>" +
        esc(e.description) + "</td><td>" + esc(e.amount) + "</td><td></td></tr>";
    }).join("");
    var tot = document.getElementById("exp-total");
    if (tot) tot.textContent = "Итого: " + ((data && data.total) || 0);
  },

  async addExpense() {
    await App.api("add_expense", {
      amount: (document.getElementById("exp-amount") || {}).value,
      description: (document.getElementById("exp-desc") || {}).value,
      category: (document.getElementById("exp-cat") || {}).value,
      date: (document.getElementById("exp-date") || {}).value,
    });
    App.loadExpenses();
  },

  async startBot() { await App.api("start_bot"); },
  async stopBot() { await App.api("stop_bot"); },
  onBotLog(msg) {
    var log = document.getElementById("tg-log");
    if (log) log.textContent += (typeof msg === "string" ? msg : (msg && msg.msg) || "") + "\n";
  },
};

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&")
    .replace(/</g, "<")
    .replace(/>/g, ">")
    .replace(/"/g, """);
}

document.addEventListener("DOMContentLoaded", function () {
  App.init();
});
