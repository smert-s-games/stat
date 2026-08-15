const App = {
  selectedScript: null,
  parsing: false,
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
    if (el) el.textContent = t;
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
      var hp = document.getElementById("home-proxy");
      if (hp) hp.textContent = "Ошибка: " + e;
    }
  },

  async loadProjects() {
    const data = await App.api("list_projects");
    const sel = document.getElementById("project-select");
    if (!data || !sel) return;
    sel.innerHTML = (data.projects || []).map(function (p) {
      return '<option value="' + esc(p.id) + '"' + (p.id === data.active_id ? ' selected' : '') + '>' + esc(p.name) + '</option>';
    }).join("");
  },

  async newProject() {
    const name = prompt("Название проекта:");
    if (!name || !name.trim()) return;
    await App.api("create_project", name.trim());
    await App.reloadAll();
  },

  async switchProject(pid) {
    if (!pid) return;
    await App.api("switch_project", pid);
    await App.reloadAll();
  },

  async reloadAll() {
    await App.loadProjects();
    await App.loadConfig();
    await App.loadCachedStats();
    await App.refreshHome();
    await App.refreshAccounts();
    await App.loadVideoScripts();
    await App.loadExpenses();
    App.setStatus("Проект переключён");
  },

  async loadConfig() {
    const cfg = await App.api("get_config");
    if (!cfg) return;
    document.documentElement.setAttribute("data-theme", cfg.theme || "light");
    var st = document.getElementById("status-theme");
    if (st) st.textContent = "Тема: " + (cfg.theme === "dark" ? "Тёмная" : "Светлая");
    var set = function (id, val) { var e = document.getElementById(id); if (e) e.value = val || ""; };
    set("links-file", cfg.links_file);
    set("proxy-purchase", cfg.proxy && cfg.proxy.purchase_date);
    set("proxy-expiry", cfg.proxy && cfg.proxy.expiry_date);
    set("server-purchase", cfg.server && cfg.server.purchase_date);
    set("server-expiry", cfg.server && cfg.server.expiry_date);
    set("tg-token", cfg.telegram_bot_token);
    set("tg-chat", cfg.telegram_chat_id);
    if (cfg.stats_sort) set("stats-sort", cfg.stats_sort);
    if (cfg.accounts_sort) set("accounts-sort", cfg.accounts_sort);
    var pn = document.getElementById("home-project-name");
    if (pn) pn.textContent = cfg.project_name ? "· " + cfg.project_name : "";
  },

  async loadCachedStats() {
    const results = await App.api("get_cached_stats");
    if (results && results.length) {
      App.renderStats(results);
      var log = document.getElementById("stats-log");
      if (log) log.textContent = "Сохранённая сессия: " + results.length + " каналов.\n";
    }
  },

  async refreshHome() {
    const data = await App.api("get_dashboard");
    if (!data) {
      var hp = document.getElementById("home-proxy");
      if (hp) hp.textContent = "Нет связи с API. Перезапустите python run_web.py";
      return;
    }
    var setT = function (id, val) { var e = document.getElementById(id); if (e) e.textContent = val != null ? val : "—"; };
    setT("kpi-channels", data.channels);
    setT("kpi-views", data.views);
    setT("kpi-subs", data.subs);
    setT("kpi-accounts", data.accounts);
    var hp = document.getElementById("home-proxy");
    if (hp) hp.innerHTML = data.proxy_html || "<span class='empty'>Нет данных</span>";
  },

  async toggleTheme() {
    const res = await App.api("toggle_theme");
    if (!res) return;
    document.documentElement.setAttribute("data-theme", res.theme);
    var st = document.getElementById("status-theme");
    if (st) st.textContent = "Тема: " + (res.theme === "dark" ? "Тёмная" : "Светлая");
  },

  async startParse() {
    if (App.parsing) { alert("Парсинг уже выполняется"); return; }
    var linksEl = document.getElementById("links-file");
    var links = linksEl ? linksEl.value.trim() : "";
    if (links) await App.api("set_links_file", links);
    App.parsing = true;
    var btn = document.getElementById("stats-parse-btn");
    if (btn) btn.disabled = true;
    var log = document.getElementById("stats-log");
    if (log) log.textContent = "Запуск парсинга…\n";
    App.setStatus("Парсинг…");
    App.navigate("stats");
    const res = await App.api("start_parse");
    if (res && res.error) {
      if (log) log.textContent += "\n❌ " + res.error;
      App.setStatus("Ошибка");
      App.parsing = false;
      if (btn) btn.disabled = false;
    }
  },

  onParseProgress(msg) {
    var log = document.getElementById("stats-log");
    if (!log) return;
    log.textContent += msg;
    log.scrollTop = log.scrollHeight;
  },

  onParseDone(results) {
    App.parsing = false;
    var btn = document.getElementById("stats-parse-btn");
    if (btn) btn.disabled = false;
    App.renderStats(results || []);
    App.refreshHome();
    App.setStatus("Парсинг завершён: " + (results ? results.length : 0) + " (сохранено)");
  },

  renderStats(results) {
    var tbody = document.getElementById("stats-tbody");
    if (!tbody) return;
    if (!results || !results.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">Нет данных</td></tr>';
      return;
    }
    tbody.innerHTML = results.map(function (r) {
      if (r.error) {
        return "<tr><td>" + esc(r.channel_name || r.url || "") + "</td><td>—</td><td>—</td><td>—</td><td>" + esc(r.url || "") + "</td><td>—</td><td><span class=\"badge badge-err\">❌ " + esc(String(r.error)) + "</span></td></tr>";
      }
      return "<tr><td>" + esc(r.channel_name || "") + "</td><td>" + esc(r.subscribers || "0") + "</td><td>" + esc(r.total_views || "0") + "</td><td>" + esc(r.videos_count || "0") + "</td><td><a href=\"#\" data-url=\"" + esc(r.url || "") + "\">" + esc(r.url || "") + "</a></td><td>" + esc(r.email || "—") + "</td><td><span class=\"badge badge-ok\">✅</span></td></tr>";
    }).join("");
    tbody.querySelectorAll("a[data-url]").forEach(function (a) {
      a.onclick = function (e) { e.preventDefault(); App.openUrl(a.getAttribute("data-url")); };
    });
  },

  async applyStatsSort(mode) {
    const results = await App.api("sort_stats_results", mode);
    if (results) App.renderStats(results);
  },

  openUrl(url) { App.api("open_url", url); return false; },

  async pickLinksFile() {
    var cur = document.getElementById("links-file");
    var path = prompt("Полный путь к links.txt:", cur ? cur.value : "");
    if (path === null || !path.trim()) return;
    if (cur) cur.value = path.trim();
    await App.api("set_links_file", path.trim());
  },

  async exportStats() {
    const res = await App.api("export_stats");
    if (res && res.ok) App.setStatus("Экспорт: " + res.path);
    else if (res && res.error) alert(res.error);
  },

  async refreshAccounts() {
    const data = await App.api("refresh_accounts");
    if (!data) return;
    if (data.error) { alert(data.error); return; }
    var foldersEl = document.getElementById("accounts-folders");
    if (foldersEl) {
      if (data.folders && data.folders.length) {
        foldersEl.innerHTML = data.folders.map(function (f, i) {
          return '<div class="script-item"><div class="script-path">' + esc(f) + '</div><button class="btn btn-ghost btn-sm" data-folder-idx="' + i + '">➖</button></div>';
        }).join("");
        foldersEl.querySelectorAll("[data-folder-idx]").forEach(function (btn) {
          btn.onclick = function () {
            var idx = parseInt(btn.getAttribute("data-folder-idx"), 10);
            App.removeFolder(data.folders[idx]);
          };
        });
      } else {
        foldersEl.innerHTML = '<div class="empty">Нет папок</div>';
      }
    }
    var tbody = document.getElementById("accounts-tbody");
    if (tbody) {
      if (!data.accounts || !data.accounts.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">Нет данных</td></tr>';
      } else {
        tbody.innerHTML = data.accounts.map(function (a) {
          return "<tr><td>" + esc(a.name) + "</td><td>" + esc(a.folder_short || a.folder || "") + "</td><td>" + esc(a.materials_count) + "</td><td>" + esc(a.size) + "</td><td>" + esc(a.modified_date) + "</td><td>" + esc(a.quality_score) + "</td></tr>";
        }).join("");
      }
    }
    App.refreshHome();
  },

  async applyAccountsSort(mode) {
    const accounts = await App.api("sort_accounts_results", mode);
    if (!accounts) return;
    var tbody = document.getElementById("accounts-tbody");
    if (!tbody) return;
    tbody.innerHTML = accounts.map(function (a) {
      return "<tr><td>" + esc(a.name) + "</td><td>" + esc(a.folder_short || a.folder || "") + "</td><td>" + esc(a.materials_count) + "</td><td>" + esc(a.size) + "</td><td>" + esc(a.modified_date) + "</td><td>" + esc(a.quality_score) + "</td></tr>";
    }).join("") || '<tr><td colspan="6" class="empty">Нет данных</td></tr>';
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
    App.selectedScript = null;
    if (!scripts || !scripts.length) {
      el.innerHTML = '<div class="empty">Нет скриптов</div>';
      return;
    }
    el.innerHTML = scripts.map(function (s, i) {
      return '<div class="script-item" data-idx="' + i + '"><div><strong>' + esc(s.name) + '</strong><div class="script-path">' + esc(s.path) + '</div></div><button class="btn btn-ghost btn-sm" data-remove="' + i + '">➖</button></div>';
    }).join("");
    el.querySelectorAll(".script-item").forEach(function (item) {
      item.onclick = function () { App.selectScript(parseInt(item.getAttribute("data-idx"), 10), item); };
    });
    el.querySelectorAll("[data-remove]").forEach(function (btn) {
      btn.onclick = function (e) { e.stopPropagation(); App.removeScript(parseInt(btn.getAttribute("data-remove"), 10)); };
    });
  },

  selectScript(idx, el) {
    document.querySelectorAll("#video-scripts .script-item").forEach(function (x) { x.classList.remove("selected"); });
    el.classList.add("selected");
    App.selectedScript = idx;
  },

  async addVideoScript() {
    var path = prompt("Путь к .py:");
    if (!path || !path.trim()) return;
    await App.api("add_video_script", path.trim());
    App.loadVideoScripts();
  },

  async removeScript(idx) {
    await App.api("remove_video_script", idx);
    App.loadVideoScripts();
  },

  async runVideoScript() {
    if (App.selectedScript === null) { alert("Выберите скрипт"); return; }
    document.getElementById("video-run-btn").disabled = true;
    document.getElementById("video-stop-btn").disabled = false;
    document.getElementById("video-log").textContent = "Запуск…\n";
    await App.api("run_video_script", App.selectedScript);
  },

  async stopVideoScript() { await App.api("stop_video_script"); },

  onVideoLog(line) {
    var log = document.getElementById("video-log");
    if (!log) return;
    log.textContent += line + "\n";
    log.scrollTop = log.scrollHeight;
  },

  onVideoDone(ok) {
    var run = document.getElementById("video-run-btn");
    var stop = document.getElementById("video-stop-btn");
    if (run) run.disabled = false;
    if (stop) stop.disabled = true;
    App.setStatus(ok ? "Скрипт завершён" : "Остановлен");
  },

  async saveProxy() {
    const res = await App.api("save_proxy", {
      purchase_date: ((document.getElementById("proxy-purchase") || {}).value || "").trim(),
      expiry_date: ((document.getElementById("proxy-expiry") || {}).value || "").trim(),
    });
    var msg = document.getElementById("proxy-save-msg");
    if (res && res.ok) {
      if (msg) msg.textContent = "OK сохранено";
      App.setStatus("Прокси сохранён");
      App.refreshHome();
    } else if (msg) msg.textContent = "Ошибка";
  },

  async saveServer() {
    const res = await App.api("save_server", {
      purchase_date: ((document.getElementById("server-purchase") || {}).value || "").trim(),
      expiry_date: ((document.getElementById("server-expiry") || {}).value || "").trim(),
    });
    var msg = document.getElementById("server-save-msg");
    if (res && res.ok) {
      if (msg) msg.textContent = "OK сохранено";
      App.setStatus("Сервер сохранён");
      App.refreshHome();
    } else if (msg) msg.textContent = "Ошибка";
  },

  async saveTelegram() {
    await App.api("save_telegram", {
      token: (document.getElementById("tg-token") || {}).value || "",
      chat_id: (document.getElementById("tg-chat") || {}).value || "",
    });
    App.setStatus("Telegram сохранён");
  },

  async loadExpenses() {
    const data = await App.api("get_expenses");
    if (!data) return;
    var tot = document.getElementById("exp-total");
    if (tot) tot.textContent = "Итого: " + (data.total || 0).toFixed(2) + " · " + (data.count || 0);
    var tbody = document.getElementById("expenses-tbody");
    if (!tbody) return;
    var items = data.items || [];
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty">Нет расходов</td></tr>';
      return;
    }
    tbody.innerHTML = items.slice().reverse().map(function (e) {
      return "<tr><td>" + esc(e.date) + "</td><td>" + esc(e.category || "—") + "</td><td>" + esc(e.description || "") + "</td><td>" + Number(e.amount).toFixed(2) + "</td><td><button class=\"btn btn-ghost btn-sm\" data-exp=\"" + esc(e.id) + "\">X</button></td></tr>";
    }).join("");
    tbody.querySelectorAll("[data-exp]").forEach(function (btn) {
      btn.onclick = function () { App.deleteExpense(btn.getAttribute("data-exp")); };
    });
  },

  async addExpense() {
    const res = await App.api(
      "add_expense",
      (document.getElementById("exp-amount") || {}).value || "",
      (document.getElementById("exp-desc") || {}).value || "",
      (document.getElementById("exp-cat") || {}).value || "",
      (document.getElementById("exp-date") || {}).value || ""
    );
    if (res && res.error) { alert(res.error); return; }
    var amt = document.getElementById("exp-amount");
    var desc = document.getElementById("exp-desc");
    if (amt) amt.value = "";
    if (desc) desc.value = "";
    App.loadExpenses();
    App.refreshHome();
  },

  async deleteExpense(id) {
    await App.api("delete_expense", id);
    App.loadExpenses();
    App.refreshHome();
  },

  async startBot() {
    document.getElementById("tg-start").disabled = true;
    document.getElementById("tg-stop").disabled = false;
    await App.api("start_bot");
  },

  async stopBot() {
    await App.api("stop_bot");
    document.getElementById("tg-start").disabled = false;
    document.getElementById("tg-stop").disabled = true;
  },

  onBotLog(msg) {
    var log = document.getElementById("tg-log");
    if (!log) return;
    log.textContent += msg + "\n";
    log.scrollTop = log.scrollHeight;
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
