const App = {
  selectedScript: null,
  parsing: false,
  viewMode: "project",

  async api(method, ...args) {
    try {
      const r = await fetch("/api/rpc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method: method, args: args }),
      });
      const j = await r.json();
      if (!j.ok) {
        const err = j.error || "error";
        App.setStatus("Ошибка: " + err);
        return { error: err };
      }
      return j.result;
    } catch (e) {
      App.setStatus("Ошибка сети: " + e);
      return null;
    }
  },

  setStatus(t) {
    const el = document.getElementById("status-text");
    if (el) el.textContent = t;
  },

  navigate(page) {
    document.querySelectorAll(".page").forEach(function (p) {
      p.classList.toggle("active", p.id === "page-" + page);
    });
    document.querySelectorAll(".nav-item").forEach(function (b) {
      b.classList.toggle("active", b.getAttribute("data-page") === page);
    });
  },

  async init() {
    try {
      document.querySelectorAll(".nav-item").forEach(function (btn) {
        btn.onclick = function () {
          App.navigate(btn.getAttribute("data-page"));
        };
      });
      var el;
      el = document.getElementById("btn-theme");
      if (el) el.onclick = function () { App.toggleTheme(); };
      el = document.getElementById("btn-new-project");
      if (el) el.onclick = function () { App.createProject(); };
      el = document.getElementById("project-select");
      if (el) el.onchange = function () { App.switchProject(el.value); };
      el = document.getElementById("stats-sort");
      if (el) el.onchange = function () { App.applyStatsSort(el.value); };
      el = document.getElementById("btn-ch-select-all");
      if (el) el.onclick = function () { App.selectAllChannels(true); };
      el = document.getElementById("btn-ch-select-none");
      if (el) el.onclick = function () { App.selectAllChannels(false); };
      el = document.getElementById("btn-ch-delete");
      if (el) el.onclick = function () { App.deleteSelectedChannels(); };
      el = document.getElementById("btn-ch-import");
      if (el) el.onclick = function () { App.importChannels(); };
      el = document.getElementById("ch-check-all");
      if (el) el.onchange = function () { App.selectAllChannels(!!el.checked); };
      el = document.getElementById("channels-search");
      if (el) el.oninput = function () { App.filterChannels(); };
      el = document.getElementById("btn-acc-select-all");
      if (el) el.onclick = function () { App.selectAllAccounts(true); };
      el = document.getElementById("btn-acc-select-none");
      if (el) el.onclick = function () { App.selectAllAccounts(false); };
      el = document.getElementById("btn-acc-delete");
      if (el) el.onclick = function () { App.deleteSelectedAccounts(); };
      el = document.getElementById("acc-check-all");
      if (el) el.onchange = function () { App.selectAllAccounts(!!el.checked); };
      el = document.getElementById("accounts-search");
      if (el) el.oninput = function () { App.filterAccounts(); };

      await App.loadProjects();
      await App.reloadAll();
      App.connectEvents();
      App.setStatus("Готово");
    } catch (e) {
      App.setStatus("Ошибка инициализации: " + e);
      console.error(e);
    }
  },

  connectEvents() {
    if (window.EventSource) {
      try {
        var es = new EventSource("/api/events");
        es.onmessage = function (ev) {
          try {
            var msg = JSON.parse(ev.data);
            if (msg.type === "js" && msg.code) {
              try { eval(msg.code); } catch (e) { console.error(e); }
            }
          } catch (e) {}
        };
      } catch (e) {}
    }
  },

  async loadProjects() {
    var data = await App.api("list_projects");
    var sel = document.getElementById("project-select");
    if (!data || !sel) return;
    var opts = '<option value="__all__">Все проекты</option>';
    opts += (data.projects || [])
      .map(function (p) {
        return (
          '<option value="' +
          esc(p.id) +
          '"' +
          (p.id === data.active_id ? " selected" : "") +
          ">" +
          esc(p.name) +
          "</option>"
        );
      })
      .join("");
    sel.innerHTML = opts;
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

  async createProject() {
    var name = prompt("Имя проекта:");
    if (!name || !name.trim()) return;
    await App.api("create_project", name.trim());
    await App.loadProjects();
    await App.reloadAll();
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
    if (cfg.theme) document.documentElement.setAttribute("data-theme", cfg.theme);
    var lf = document.getElementById("links-file");
    if (lf && cfg.links_file) lf.value = cfg.links_file;
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

  async startParse() {
    var links = (document.getElementById("links-file") || {}).value;
    if (links) await App.api("set_links_file", links);
    var res = await App.api("start_parse");
    if (res && res.error) alert(res.error);
  },

  onParseProgress(msg) {
    var log = document.getElementById("stats-log");
    if (log) {
      log.textContent += msg;
      log.scrollTop = log.scrollHeight;
    }
  },

  onParseDone(results) {
    App.renderStats(results || []);
    App.refreshHome();
    App.setStatus("Парсинг завершён");
  },

  renderStats(results) {
    /* force_ui_fix overrides this */
    var tbody = document.getElementById("stats-tbody");
    if (!tbody) return;
    App._channelsCache = Array.isArray(results) ? results.slice() : [];
    if (!results || !results.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty">Нет данных</td></tr>';
      return;
    }
    tbody.innerHTML = results.map(function (r) {
      return "<tr><td></td><td>" + esc(r.channel_name || "") + "</td><td>" + esc(r.subscribers || "0") +
        "</td><td>" + esc(r.total_views || "0") + "</td><td>" + esc(r.videos_count || "0") +
        "</td><td>" + esc(r.url || "") + "</td><td>" + esc(r.email || "—") + "</td><td></td><td></td></tr>";
    }).join("");
  },

  async applyStatsSort(mode) {
    const results = await App.api("sort_stats_results", mode);
    if (results) App.renderStats(results);
  },

  openUrl(url) { App.api("open_url", url); return false; },

  async toggleTheme() {
    var res = await App.api("toggle_theme");
    if (res && res.theme) document.documentElement.setAttribute("data-theme", res.theme);
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
    var amount = (document.getElementById("exp-amount") || {}).value;
    var desc = (document.getElementById("exp-desc") || {}).value;
    var cat = (document.getElementById("exp-cat") || {}).value;
    var date = (document.getElementById("exp-date") || {}).value;
    await App.api("add_expense", { amount: amount, description: desc, category: cat, date: date });
    App.loadExpenses();
  },
};

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&" + "amp;")
    .replace(/</g, "&" + "lt;")
    .replace(/>/g, "&" + "gt;")
    .replace(/"/g, "&" + "quot;");
}

document.addEventListener("DOMContentLoaded", function () {
  App.init();
});
