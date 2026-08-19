/* UI 20260819n — event delegation, all buttons work */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "\u0026amp;")
      .replace(/</g, "\u0026lt;")
      .replace(/>/g, "\u0026gt;")
      .replace(/"/g, "\u0026quot;");
  }
  window.esc = esc;

  function setStatus(t) {
    var el = document.getElementById("status-text");
    if (el) el.textContent = "UI 20260819n \u00b7 " + t;
  }

  function paintCh(results) {
    var tbody = document.getElementById("stats-tbody");
    if (!tbody) return;
    var qEl = document.getElementById("channels-search");
    var q = (qEl && qEl.value ? qEl.value : "").trim().toLowerCase();
    var list = Array.isArray(results) ? results.slice() : [];
    if (q) {
      list = list.filter(function (r) {
        return String(r.channel_name || "").toLowerCase().indexOf(q) >= 0 ||
          String(r.url || "").toLowerCase().indexOf(q) >= 0 ||
          String(r.email || "").toLowerCase().indexOf(q) >= 0;
      });
    }
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty">' + (q ? "Ничего не найдено" : "Нет данных") + "</td></tr>";
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
        var label = err || (name.trim().toLowerCase() === "youtube" ? "Неактивный канал" : "404 Not Found");
        return '<tr class="row-error channel-row"><td>' + cb + '</td><td>' + esc(name || url) +
          '</td><td>—</td><td>—</td><td>—</td><td>' + esc(url) + '</td><td>' + esc(r.email || "—") +
          '</td><td><span class="badge badge-err">❌ ' + esc(label) + '</span></td>' +
          '<td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="' + esc(url) + '">✕</button></td></tr>';
      }
      var views = r.total_views || "0";
      return '<tr class="channel-row"><td>' + cb + '</td><td>' + esc(name) +
        '</td><td>' + esc(r.subscribers || "0") + '</td><td>' + esc(views) + '</td><td>' + esc(r.videos_count || "0") +
        '</td><td><a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(url) + '</a></td><td>' +
        esc(r.email || "—") + '</td><td><span class="badge badge-ok">✅</span></td>' +
        '<td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="' + esc(url) + '">✕</button></td></tr>';
    }).join("");
  }

  function paintAcc(accounts) {
    var tbody = document.getElementById("accounts-tbody");
    if (!tbody) return;
    var list = Array.isArray(accounts) ? accounts : [];
    var qEl = document.getElementById("accounts-search");
    var q = (qEl && qEl.value ? qEl.value : "").trim().toLowerCase();
    if (q) {
      list = list.filter(function (a) {
        return String(a.name || "").toLowerCase().indexOf(q) >= 0 ||
          String(a.folder_short || a.folder || "").toLowerCase().indexOf(q) >= 0;
      });
    }
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="empty">' + (q ? "Ничего не найдено" : "Нет данных") + "</td></tr>";
      return;
    }
    tbody.innerHTML = list.map(function (a) {
      var key = a.path || a.folder || a.name || "";
      return '<tr class="account-row"><td><input type="checkbox" class="acc-check" data-name="' + esc(a.name || "") +
        '" data-path="' + esc(key) + '" /></td><td>' + esc(a.name) + '</td><td>' +
        esc(a.folder_short || a.folder || "") + '</td><td>' + esc(a.materials_count) +
        '</td><td>' + esc(a.size) + '</td><td>' + esc(a.modified_date) +
        '</td><td>' + esc(a.quality_score) +
        '</td><td><button type="button" class="btn btn-ghost btn-sm btn-del-acc" data-name="' +
        esc(a.name || "") + '" data-path="' + esc(key) + '">✕</button></td></tr>';
    }).join("");
  }

  function safeCall(name, fn) {
    return async function () {
      try {
        setStatus(name + "\u2026");
        await fn.apply(null, arguments);
      } catch (e) {
        console.error(name, e);
        alert(name + ": " + (e && e.message ? e.message : e));
        setStatus("Ошибка: " + name);
      }
    };
  }

  function installMethods() {
    if (!window.App) return false;

    App.setStatus = setStatus;
    App._paintChannels = paintCh;
    App._paintAccounts = paintAcc;

    App.renderStats = function (results) {
      App._channelsCache = Array.isArray(results) ? results.slice() : [];
      paintCh(App._channelsCache);
    };

    App.filterChannels = function () { paintCh(App._channelsCache || []); };
    App.filterAccounts = function () { paintAcc(App._accountsCache || []); };

    App.selectAllChannels = function (on) {
      var c = !!on;
      document.querySelectorAll(".ch-check").forEach(function (x) {
        x.checked = c;
        var tr = x.closest("tr");
        if (tr) tr.classList.toggle("row-selected", c);
      });
      var all = document.getElementById("ch-check-all");
      if (all) all.checked = c;
    };

    App.selectAllAccounts = function (on) {
      var c = !!on;
      document.querySelectorAll(".acc-check").forEach(function (x) {
        x.checked = c;
        var tr = x.closest("tr");
        if (tr) tr.classList.toggle("row-selected", c);
      });
      var all = document.getElementById("acc-check-all");
      if (all) all.checked = c;
    };

    App.deleteChannels = safeCall("Удаление каналов", async function (urls) {
      var res = await App.api("delete_channels", null, urls || []);
      if (res && res.error) { alert(res.error); return; }
      App.renderStats((res && res.stats) || []);
      if (App.refreshHome) await App.refreshHome();
      setStatus("Удалено");
    });

    App.deleteSelectedChannels = safeCall("Удаление", async function () {
      var urls = [];
      document.querySelectorAll(".ch-check:checked").forEach(function (x) {
        urls.push(x.getAttribute("data-url"));
      });
      if (!urls.length) { alert("Выберите каналы"); return; }
      if (!confirm("Удалить выбранные (" + urls.length + ")?")) return;
      await App.deleteChannels(urls);
    });

    App.deleteAccounts = safeCall("Удаление аккаунтов", async function (names, paths) {
      var res = await App.api("delete_accounts", names || [], paths || []);
      if (res && res.error) { alert(res.error); return; }
      App._accountsCache = (res && res.accounts) || [];
      paintAcc(App._accountsCache);
      if (App.refreshHome) await App.refreshHome();
    });

    App.deleteSelectedAccounts = safeCall("Удаление", async function () {
      var names = [], paths = [];
      document.querySelectorAll(".acc-check:checked").forEach(function (x) {
        names.push(x.getAttribute("data-name"));
        paths.push(x.getAttribute("data-path"));
      });
      if (!names.length) { alert("Выберите аккаунты"); return; }
      if (!confirm("Удалить выбранные (" + names.length + ")?")) return;
      await App.deleteAccounts(names, paths);
    });

    App.importChannels = safeCall("Импорт", async function () {
      var ta = document.getElementById("channels-import");
      var text = ta ? ta.value : "";
      if (!text || !text.trim()) { alert("Вставьте список каналов"); return; }
      var fmt = "url";
      document.querySelectorAll('input[name="ch-format"]').forEach(function (r) {
        if (r.checked) fmt = r.value;
      });
      var res = await App.api("import_channels", text, fmt);
      if (!res || res.error) { alert((res && res.error) || "Ошибка импорта"); return; }
      if (ta) ta.value = "";
      alert("Добавлено: " + (res.added || 0) + ", всего: " + (res.total || 0));
      var cached = await App.api("get_cached_stats");
      if (Array.isArray(cached)) App.renderStats(cached);
      if (App.refreshHome) await App.refreshHome();
      setStatus("Импорт готов");
    });

    App.startParse = safeCall("Парсинг", async function () {
      var links = (document.getElementById("links-file") || {}).value;
      if (links) await App.api("set_links_file", links);
      var res = await App.api("start_parse");
      if (res && res.error) { alert(res.error); return; }
      setStatus("Парсинг запущен");
      var log = document.getElementById("stats-log");
      if (log) log.textContent = "Парсинг запущен\u2026\n";
    });

    App.switchProject = safeCall("Смена проекта", async function (pid) {
      if (!pid) return;
      if (pid === "__all__") {
        if (App.showAllProjectsStats) await App.showAllProjectsStats();
        return;
      }
      App.viewMode = "project";
      App.renderStats([]);
      var res = await App.api("switch_project", pid);
      if (!res || res.error) { alert((res && res.error) || "Ошибка смены проекта"); return; }
      var stats = await App.api("get_cached_stats");
      App.renderStats(Array.isArray(stats) ? stats : []);
      if (App.refreshHome) await App.refreshHome();
      if (App.refreshAccounts) await App.refreshAccounts();
      if (App.loadExpenses) await App.loadExpenses();
      var sel = document.getElementById("project-select");
      if (sel) sel.value = pid;
      setStatus("Проект: " + (res.project_name || pid));
    });

    App.newProject = safeCall("Новый проект", async function () {
      var name = prompt("Имя проекта:");
      if (!name || !name.trim()) return;
      await App.api("create_project", name.trim());
      if (App.loadProjects) await App.loadProjects();
      if (App.reloadAll) await App.reloadAll();
      setStatus("Проект создан");
    });

    App.toggleTheme = safeCall("Тема", async function () {
      var res = await App.api("toggle_theme");
      if (res && res.theme) {
        document.documentElement.setAttribute("data-theme", res.theme);
        var st = document.getElementById("status-theme");
        if (st) st.textContent = "Тема: " + res.theme;
        if (App.renderThemePills) App.renderThemePills();
      }
      setStatus("Тема: " + ((res && res.theme) || "?"));
    });

    App.onParseDone = function (results) {
      App.renderStats(Array.isArray(results) ? results : []);
      if (App.refreshHome) App.refreshHome();
      setStatus("Парсинг завершён");
    };

    document.title = "YT Analytics \u00b7 20260819n";
    return typeof App.api === "function";
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !window.App) return;
    var el = t;
    while (el && el !== document.body) {
      var id = el.id;
      if (id === "btn-theme") { e.preventDefault(); App.toggleTheme(); return; }
      if (id === "btn-new-project") { e.preventDefault(); App.newProject(); return; }
      if (id === "btn-ch-import") { e.preventDefault(); App.importChannels(); return; }
      if (id === "stats-parse-btn") { e.preventDefault(); App.startParse(); return; }
      if (id === "btn-ch-select-all") { e.preventDefault(); App.selectAllChannels(true); return; }
      if (id === "btn-ch-select-none") { e.preventDefault(); App.selectAllChannels(false); return; }
      if (id === "btn-ch-delete") { e.preventDefault(); App.deleteSelectedChannels(); return; }
      if (id === "btn-acc-select-all") { e.preventDefault(); App.selectAllAccounts(true); return; }
      if (id === "btn-acc-select-none") { e.preventDefault(); App.selectAllAccounts(false); return; }
      if (id === "btn-acc-delete") { e.preventDefault(); App.deleteSelectedAccounts(); return; }
      if (id === "video-run-btn") { e.preventDefault(); if (App.runVideoScript) App.runVideoScript(); return; }
      if (id === "video-stop-btn") { e.preventDefault(); if (App.stopVideoScript) App.stopVideoScript(); return; }
      if (el.classList && el.classList.contains("btn-del-ch")) {
        e.preventDefault(); e.stopPropagation();
        App.deleteChannels([el.getAttribute("data-url")]); return;
      }
      if (el.classList && el.classList.contains("btn-del-acc")) {
        e.preventDefault(); e.stopPropagation();
        App.deleteAccounts([el.getAttribute("data-name")], [el.getAttribute("data-path")]); return;
      }
      if (el.classList && el.classList.contains("channel-row")) {
        if (t.tagName === "A" || t.tagName === "INPUT" || t.tagName === "BUTTON") return;
        var cb = el.querySelector(".ch-check");
        if (cb) { cb.checked = !cb.checked; el.classList.toggle("row-selected", cb.checked); }
        return;
      }
      if (el.classList && el.classList.contains("account-row")) {
        if (t.tagName === "INPUT" || t.tagName === "BUTTON") return;
        var cb2 = el.querySelector(".acc-check");
        if (cb2) { cb2.checked = !cb2.checked; el.classList.toggle("row-selected", cb2.checked); }
        return;
      }
      el = el.parentElement;
    }
  }, true);

  document.addEventListener("change", function (e) {
    var t = e.target;
    if (!t || !window.App) return;
    if (t.id === "project-select") { App.switchProject(t.value); return; }
    if (t.id === "ch-check-all") { App.selectAllChannels(!!t.checked); return; }
    if (t.id === "acc-check-all") { App.selectAllAccounts(!!t.checked); return; }
    if (t.id === "stats-sort" && App.applyStatsSort) { App.applyStatsSort(t.value); return; }
    if (t.id === "accounts-sort" && App.applyAccountsSort) { App.applyAccountsSort(t.value); return; }
    if (t.classList && t.classList.contains("ch-check")) {
      var tr = t.closest("tr");
      if (tr) tr.classList.toggle("row-selected", t.checked);
    }
    if (t.classList && t.classList.contains("acc-check")) {
      var tr2 = t.closest("tr");
      if (tr2) tr2.classList.toggle("row-selected", t.checked);
    }
  }, true);

  document.addEventListener("input", function (e) {
    var t = e.target;
    if (!t || !window.App) return;
    if (t.id === "channels-search") App.filterChannels();
    if (t.id === "accounts-search") App.filterAccounts();
  }, true);

  function boot() {
    if (!installMethods()) { setTimeout(boot, 50); return; }
    setStatus("Готово");
    if (App._channelsCache && App._channelsCache.length) paintCh(App._channelsCache);
    else if (typeof App.loadCachedStats === "function") {
      App.loadCachedStats().catch(function (e) { console.error(e); });
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
