const App = {
  selectedScript: null,
  parsing: false,
  viewMode: "project",
  _es: null,
  _channelsCache: [],
  _accountsCache: [],
  UI_VER: "20260819o",

  async api(method) {
    var args = Array.prototype.slice.call(arguments, 1);
    try {
      var res = await fetch("/api/rpc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method: method, args: args }),
      });
      var data = await res.json();
      if (!res.ok || data.ok === false) {
        var err = (data && data.error) || res.statusText;
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

  connectEvents: function () {
    if (App._es) {
      try { App._es.close(); } catch (e) {}
    }
    try {
      var es = new EventSource("/api/events");
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
    } catch (e) {
      console.error("SSE", e);
    }
  },

  setStatus: function (t) {
    var el = document.getElementById("status-text");
    if (el) el.textContent = "UI " + App.UI_VER + " \u00b7 " + t;
  },

  navigate: function (page) {
    if (page === "settings") page = "home";
    document.querySelectorAll(".page").forEach(function (p) { p.classList.remove("active"); });
    document.querySelectorAll(".nav-item").forEach(function (n) { n.classList.remove("active"); });
    var section = document.getElementById("page-" + page);
    if (section) section.classList.add("active");
    var nav = document.querySelector('.nav-item[data-page="' + page + '"]');
    if (nav) nav.classList.add("active");
    if (page === "expenses") App.loadExpenses();
    if (page === "proxy" && App.loadProxies) App.loadProxies();
    if (page === "video") App.loadVideoScripts();
    if (page === "accounts") App.refreshAccounts();
    if (page === "stats") App.loadCachedStats();
  },

  init: async function () {
    App.setStatus("Старт…");
    try {
      App.connectEvents();
      App.bindAll();
      await App.loadProjects();
      await App.loadConfig();
      await App.loadCachedStats();
      await App.refreshHome();
      await App.refreshAccounts();
      await App.loadVideoScripts();
      await App.loadExpenses();
      if (App.loadProxies) await App.loadProxies();
      App.setStatus("Готово");
    } catch (e) {
      console.error("init error", e);
      App.setStatus("Ошибка: " + e);
    }
  },

  bindAll: function () {
    document.querySelectorAll(".nav-item").forEach(function (btn) {
      btn.onclick = function () {
        App.navigate(btn.getAttribute("data-page"));
      };
    });
    function on(id, fn) {
      var el = document.getElementById(id);
      if (el) el.onclick = fn;
    }
    function onChange(id, fn) {
      var el = document.getElementById(id);
      if (el) el.onchange = fn;
    }
    function onInput(id, fn) {
      var el = document.getElementById(id);
      if (el) el.oninput = fn;
    }
    on("btn-theme", function () { App.toggleTheme(); });
    on("btn-new-project", function () { App.newProject(); });
    onChange("project-select", function () {
      App.switchProject(document.getElementById("project-select").value);
    });
    onChange("stats-sort", function () {
      App.applyStatsSort(document.getElementById("stats-sort").value);
    });
    onChange("accounts-sort", function () {
      App.applyAccountsSort(document.getElementById("accounts-sort").value);
    });
    on("btn-ch-import", function () { App.importChannels(); });
    on("stats-parse-btn", function () { App.startParse(); });
    on("btn-pick-links", function () { App.pickLinksFile(); });
    on("btn-ch-select-all", function () { App.selectAllChannels(true); });
    on("btn-ch-select-none", function () { App.selectAllChannels(false); });
    on("btn-ch-delete", function () { App.deleteSelectedChannels(); });
    onChange("ch-check-all", function () {
      App.selectAllChannels(!!document.getElementById("ch-check-all").checked);
    });
    onInput("channels-search", function () { App.filterChannels(); });
    on("btn-acc-select-all", function () { App.selectAllAccounts(true); });
    on("btn-acc-select-none", function () { App.selectAllAccounts(false); });
    on("btn-acc-delete", function () { App.deleteSelectedAccounts(); });
    onChange("acc-check-all", function () {
      App.selectAllAccounts(!!document.getElementById("acc-check-all").checked);
    });
    onInput("accounts-search", function () { App.filterAccounts(); });
    on("btn-add-folder", function () { App.addAccountsFolder(); });
    on("btn-refresh-accounts", function () { App.refreshAccounts(); });
    on("btn-add-script", function () { App.addVideoScript(); });
    on("video-run-btn", function () { App.runVideoScript(); });
    on("video-stop-btn", function () { App.stopVideoScript(); });
    on("btn-add-expense", function () { App.addExpense(); });
    on("btn-add-proxy", function () {
      if (App.addProxyFromForm) App.addProxyFromForm();
    });
    on("btn-save-tg", function () { App.saveTelegram(); });
    on("tg-start", function () { App.startBot(); });
    on("tg-stop", function () { App.stopBot(); });
    on("btn-save-proxy-dates", function () { App.saveProxy(); });
    on("btn-save-server-dates", function () { App.saveServer(); });
  },

  loadProjects: async function () {
    var data = await App.api("list_projects");
    var sel = document.getElementById("project-select");
    if (!data || !sel) return;
    var opts = '<option value="__all__">Все проекты</option>';
    opts += (data.projects || []).map(function (p) {
      return '<option value="' + esc(p.id) + '"' +
        (p.id === data.active_id ? " selected" : "") + ">" + esc(p.name) + "</option>";
    }).join("");
    sel.innerHTML = opts;
    sel.onchange = function () { App.switchProject(sel.value); };
  },

  newProject: async function () {
    var name = prompt("Имя проекта:");
    if (!name || !name.trim()) return;
    await App.api("create_project", name.trim());
    await App.loadProjects();
    await App.reloadAll();
  },

  switchProject: async function (pid) {
    if (!pid) return;
    if (pid === "__all__") {
      if (App.showAllProjectsStats) await App.showAllProjectsStats();
      return;
    }
    App.viewMode = "project";
    App.setStatus("Смена проекта…");
    App.renderStats([]);
    var res = await App.api("switch_project", pid);
    if (res && res.error) { alert(res.error); return; }
    await App.loadCachedStats();
    await App.refreshHome();
    await App.refreshAccounts();
    await App.loadExpenses();
    if (App.loadProxies) await App.loadProxies();
    var sel = document.getElementById("project-select");
    if (sel) sel.value = pid;
    App.setStatus("Проект: " + ((res && res.project_name) || pid));
  },

  showAllProjectsStats: async function () {
    App.viewMode = "all";
    App.navigate("home");
    var dash = await App.api("get_all_projects_dashboard");
    if (!dash || dash.error) {
      alert("Сводка: " + ((dash && dash.error) || "ошибка"));
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

  reloadAll: async function () {
    await App.loadConfig();
    await App.loadCachedStats();
    await App.refreshAccounts();
    await App.refreshHome();
    await App.loadExpenses();
    await App.loadVideoScripts();
  },

  loadConfig: async function () {
    var cfg = await App.api("get_config");
    if (!cfg) return;
    if (cfg.theme || cfg.ui_theme) {
      document.documentElement.setAttribute("data-theme", cfg.ui_theme || cfg.theme);
    }
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

  loadCachedStats: async function () {
    var results = await App.api("get_cached_stats");
    App.renderStats(Array.isArray(results) ? results : []);
  },

  refreshHome: async function () {
    var data = await App.api("get_dashboard");
    if (!data) {
      var hp = document.getElementById("home-proxy");
      if (hp) hp.textContent = "Нет ответа API.";
      return;
    }
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

  toggleTheme: async function () {
    var res = await App.api("toggle_theme");
    if (res && res.theme) {
      document.documentElement.setAttribute("data-theme", res.theme);
      var st = document.getElementById("status-theme");
      if (st) st.textContent = "Тема: " + res.theme;
    }
  },

  startParse: async function () {
    var links = (document.getElementById("links-file") || {}).value;
    if (links) await App.api("set_links_file", links);
    var res = await App.api("start_parse");
    if (res && res.error) alert(res.error);
    else App.setStatus("Парсинг запущен");
  },

  onParseProgress: function (msg) {
    var log = document.getElementById("stats-log");
    if (log) {
      log.textContent += (typeof msg === "string" ? msg : (msg && msg.msg) || "") + "\n";
      log.scrollTop = log.scrollHeight;
    }
  },

  onParseDone: function (results) {
    App.renderStats(results || []);
    App.refreshHome();
    App.setStatus("Парсинг завершён");
  },

  renderStats: function (results) {
    App._channelsCache = Array.isArray(results) ? results.slice() : [];
    App._paintChannelsTable(App._channelsCache);
  },

  filterChannels: function () {
    App._paintChannelsTable(App._channelsCache || []);
  },

  _paintChannelsTable: function (results) {
    var tbody = document.getElementById("stats-tbody");
    if (!tbody) return;
    var qEl = document.getElementById("channels-search");
    var q = (qEl && qEl.value ? qEl.value : "").trim().toLowerCase();
    var list = results || [];
    if (q) {
      list = list.filter(function (r) {
        return String(r.channel_name || "").toLowerCase().indexOf(q) >= 0 ||
          String(r.url || "").toLowerCase().indexOf(q) >= 0 ||
          String(r.email || "").toLowerCase().indexOf(q) >= 0;
      });
    }
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty">' +
        (q ? "Ничего не найдено" : "Нет данных") + "</td></tr>";
      return;
    }
    tbody.innerHTML = list.map(function (r) {
      var name = String(r.channel_name || "");
      var err = r.error ? String(r.error) : "";
      var low = (err + " " + name).toLowerCase();
      var isBad = !!err || low.indexOf("404") >= 0 || name.trim().toLowerCase() === "youtube";
      var url = r.url || "";
      var cb = '<input type="checkbox" class="ch-check" data-url="' + esc(url) + '" />';
      if (isBad) {
        var label = err || (name.trim().toLowerCase() === "youtube" ? "Неактивный" : "404");
        return '<tr class="row-error channel-row"><td>' + cb + '</td><td>' + esc(name || url) +
          '</td><td>—</td><td>—</td><td>—</td><td>' + esc(url) + '</td><td>' + esc(r.email || "—") +
          '</td><td><span class="badge badge-err">❌ ' + esc(label) + '</span></td>' +
          '<td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="' + esc(url) + '">✕</button></td></tr>';
      }
      var views = r.total_views != null && r.total_views !== "" ? r.total_views : "0";
      var vids = r.videos_count != null && r.videos_count !== "" ? r.videos_count : "0";
      var subs = r.subscribers != null && r.subscribers !== "" ? r.subscribers : "0";
      return '<tr class="channel-row"><td>' + cb + '</td><td>' + esc(name) +
        '</td><td>' + esc(subs) + '</td><td>' + esc(views) + '</td><td>' + esc(vids) +
        '</td><td><a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(url) + '</a></td><td>' +
        esc(r.email || "—") + '</td><td><span class="badge badge-ok">✅</span></td>' +
        '<td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="' + esc(url) + '">✕</button></td></tr>';
    }).join("");

    tbody.querySelectorAll(".btn-del-ch").forEach(function (btn) {
      btn.onclick = function (e) {
        e.stopPropagation();
        App.deleteChannels([btn.getAttribute("data-url")]);
      };
    });
    tbody.querySelectorAll(".ch-check").forEach(function (cb) {
      cb.onclick = function (e) { e.stopPropagation(); };
      cb.onchange = function () {
        var tr = cb.closest("tr");
        if (tr) tr.classList.toggle("row-selected", cb.checked);
      };
    });
    tbody.querySelectorAll("tr.channel-row").forEach(function (tr) {
      tr.onclick = function (e) {
        if (e.target.tagName === "A" || e.target.tagName === "BUTTON" || e.target.tagName === "INPUT") return;
        var cb = tr.querySelector(".ch-check");
        if (!cb) return;
        cb.checked = !cb.checked;
        tr.classList.toggle("row-selected", cb.checked);
      };
    });
  },

  selectAllChannels: function (on) {
    var c = !!on;
    document.querySelectorAll(".ch-check").forEach(function (x) {
      x.checked = c;
      var tr = x.closest("tr");
      if (tr) tr.classList.toggle("row-selected", c);
    });
    var all = document.getElementById("ch-check-all");
    if (all) all.checked = c;
  },

  deleteSelectedChannels: async function () {
    var urls = [];
    document.querySelectorAll(".ch-check:checked").forEach(function (x) {
      urls.push(x.getAttribute("data-url"));
    });
    if (!urls.length) { alert("Выберите каналы"); return; }
    if (!confirm("Удалить выбранные (" + urls.length + ")?")) return;
    await App.deleteChannels(urls);
  },

  deleteChannels: async function (urls) {
    var res = await App.api("delete_channels", null, urls || []);
    if (res && res.error) { alert(res.error); return; }
    App.renderStats((res && res.stats) || []);
    App.refreshHome();
  },

  importChannels: async function () {
    var ta = document.getElementById("channels-import");
    var text = ta ? ta.value : "";
    if (!text || !text.trim()) { alert("Вставьте список каналов"); return; }
    var fmt = "url";
    document.querySelectorAll('input[name="ch-format"]').forEach(function (r) {
      if (r.checked) fmt = r.value;
    });
    var res = await App.api("import_channels", text, fmt);
    if (!res || res.error) { alert((res && res.error) || "Ошибка"); return; }
    if (ta) ta.value = "";
    alert("Добавлено: " + (res.added || 0) + ", всего: " + (res.total || 0));
    await App.loadCachedStats();
    App.refreshHome();
  },

  applyStatsSort: async function (mode) {
    var results = await App.api("sort_stats_results", mode);
    if (results) App.renderStats(results);
  },

  pickLinksFile: async function () {
    var p = prompt("Путь к файлу ссылок:");
    if (!p) return;
    var inp = document.getElementById("links-file");
    if (inp) inp.value = p;
    await App.api("set_links_file", p);
  },

  refreshAccounts: async function () {
    var data = await App.api("refresh_accounts");
    if (!data) return;
    if (data.error) { alert(data.error); return; }
    var foldersEl = document.getElementById("accounts-folders");
    if (foldersEl) {
      if (data.folders && data.folders.length) {
        foldersEl.innerHTML = data.folders.map(function (f, i) {
          return '<div class="script-item"><div class="script-path">' + esc(f) +
            '</div><button type="button" class="btn btn-ghost btn-sm" data-rm-folder="' + i + '">➖</button></div>';
        }).join("");
        foldersEl.querySelectorAll("[data-rm-folder]").forEach(function (btn) {
          btn.onclick = function () {
            var idx = parseInt(btn.getAttribute("data-rm-folder"), 10);
            App.removeFolder(data.folders[idx]);
          };
        });
      } else {
        foldersEl.innerHTML = '<div class="empty">Нет папок</div>';
      }
    }
    App._accountsCache = data.accounts || [];
    App._paintAccountsTable(App._accountsCache);
  },

  filterAccounts: function () {
    App._paintAccountsTable(App._accountsCache || []);
  },

  _paintAccountsTable: function (accounts) {
    var tbody = document.getElementById("accounts-tbody");
    if (!tbody) return;
    var qEl = document.getElementById("accounts-search");
    var q = (qEl && qEl.value ? qEl.value : "").trim().toLowerCase();
    var list = accounts || [];
    if (q) {
      list = list.filter(function (a) {
        return String(a.name || "").toLowerCase().indexOf(q) >= 0 ||
          String(a.folder_short || a.folder || "").toLowerCase().indexOf(q) >= 0;
      });
    }
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="empty">' +
        (q ? "Ничего не найдено" : "Нет данных") + "</td></tr>";
      return;
    }
    tbody.innerHTML = list.map(function (a) {
      var key = a.path || a.folder || a.name || "";
      return '<tr class="account-row"><td><input type="checkbox" class="acc-check" data-name="' +
        esc(a.name || "") + '" data-path="' + esc(key) + '" /></td><td>' + esc(a.name) +
        '</td><td>' + esc(a.folder_short || a.folder || "") + '</td><td>' + esc(a.materials_count) +
        '</td><td>' + esc(a.size) + '</td><td>' + esc(a.modified_date) +
        '</td><td>' + esc(a.quality_score) +
        '</td><td><button type="button" class="btn btn-ghost btn-sm btn-del-acc" data-name="' +
        esc(a.name || "") + '" data-path="' + esc(key) + '">✕</button></td></tr>';
    }).join("");
    tbody.querySelectorAll(".btn-del-acc").forEach(function (btn) {
      btn.onclick = function (e) {
        e.stopPropagation();
        App.deleteAccounts([btn.getAttribute("data-name")], [btn.getAttribute("data-path")]);
      };
    });
    tbody.querySelectorAll(".acc-check").forEach(function (cb) {
      cb.onclick = function (e) { e.stopPropagation(); };
      cb.onchange = function () {
        var tr = cb.closest("tr");
        if (tr) tr.classList.toggle("row-selected", cb.checked);
      };
    });
    tbody.querySelectorAll("tr.account-row").forEach(function (tr) {
      tr.onclick = function (e) {
        if (e.target.tagName === "BUTTON" || e.target.tagName === "INPUT") return;
        var cb = tr.querySelector(".acc-check");
        if (!cb) return;
        cb.checked = !cb.checked;
        tr.classList.toggle("row-selected", cb.checked);
      };
    });
  },

  selectAllAccounts: function (on) {
    var c = !!on;
    document.querySelectorAll(".acc-check").forEach(function (x) {
      x.checked = c;
      var tr = x.closest("tr");
      if (tr) tr.classList.toggle("row-selected", c);
    });
    var all = document.getElementById("acc-check-all");
    if (all) all.checked = c;
  },

  deleteSelectedAccounts: async function () {
    var names = [], paths = [];
    document.querySelectorAll(".acc-check:checked").forEach(function (x) {
      names.push(x.getAttribute("data-name"));
      paths.push(x.getAttribute("data-path"));
    });
    if (!names.length) { alert("Выберите аккаунты"); return; }
    if (!confirm("Удалить выбранные (" + names.length + ")?")) return;
    await App.deleteAccounts(names, paths);
  },

  deleteAccounts: async function (names, paths) {
    var res = await App.api("delete_accounts", names || [], paths || []);
    if (res && res.error) { alert(res.error); return; }
    App._accountsCache = (res && res.accounts) || [];
    App._paintAccountsTable(App._accountsCache);
  },

  applyAccountsSort: async function (mode) {
    var accounts = await App.api("sort_accounts_results", mode);
    if (!accounts) return;
    App._accountsCache = accounts;
    App._paintAccountsTable(accounts);
  },

  addAccountsFolder: async function () {
    var path = prompt("Полный путь к папке с аккаунтами:");
    if (!path || !path.trim()) return;
    var res = await App.api("add_accounts_folder", path.trim());
    if (res && res.error) alert(res.error);
    await App.refreshAccounts();
  },

  removeFolder: async function (path) {
    await App.api("remove_accounts_folder", path);
    await App.refreshAccounts();
  },

  loadVideoScripts: async function () {
    var scripts = await App.api("get_video_scripts");
    var el = document.getElementById("video-scripts");
    if (!el) return;
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

  addVideoScript: async function () {
    var path = prompt("Полный путь к .py скрипту:");
    if (!path || !path.trim()) return;
    var res = await App.api("add_video_script", path.trim());
    if (res && res.error) alert(res.error);
    await App.loadVideoScripts();
  },

  runVideoScript: async function () {
    if (App.selectedScript == null) { alert("Выберите скрипт"); return; }
    await App.api("run_video_script", App.selectedScript);
  },

  stopVideoScript: async function () { await App.api("stop_video_script"); },

  onVideoLog: function (line) {
    var log = document.getElementById("video-log");
    if (log) log.textContent += (typeof line === "string" ? line : (line && line.msg) || "") + "\n";
  },

  onVideoDone: function (ok) {
    App.setStatus(ok ? "Скрипт завершён" : "Скрипт остановлен");
  },

  saveProxy: async function () {
    await App.api("save_proxy_dates",
      (document.getElementById("proxy-purchase") || {}).value || "",
      (document.getElementById("proxy-expiry") || {}).value || "");
    var msg = document.getElementById("proxy-save-msg");
    if (msg) msg.textContent = "Сохранено";
  },

  saveServer: async function () {
    await App.api("save_server_dates",
      (document.getElementById("server-purchase") || {}).value || "",
      (document.getElementById("server-expiry") || {}).value || "");
    var msg = document.getElementById("server-save-msg");
    if (msg) msg.textContent = "Сохранено";
  },

  saveTelegram: async function () {
    await App.api("save_telegram",
      (document.getElementById("tg-token") || {}).value || "",
      (document.getElementById("tg-chat") || {}).value || "");
    App.setStatus("Telegram сохранён");
  },

  loadExpenses: async function () {
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

  addExpense: async function () {
    await App.api("add_expense", {
      amount: (document.getElementById("exp-amount") || {}).value,
      description: (document.getElementById("exp-desc") || {}).value,
      category: (document.getElementById("exp-cat") || {}).value,
      date: (document.getElementById("exp-date") || {}).value,
    });
    App.loadExpenses();
  },

  startBot: async function () { await App.api("start_bot"); },
  stopBot: async function () { await App.api("stop_bot"); },
  onBotLog: function (msg) {
    var log = document.getElementById("tg-log");
    if (log) log.textContent += (typeof msg === "string" ? msg : (msg && msg.msg) || "") + "\n";
  },
};

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "\u0026amp;")
    .replace(/</g, "\u0026lt;")
    .replace(/>/g, "\u0026gt;")
    .replace(/"/g, "\u0026quot;");
}

document.addEventListener("DOMContentLoaded", function () {
  App.init();
});
