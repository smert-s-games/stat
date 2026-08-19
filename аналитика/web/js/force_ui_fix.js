/* UI 20260819m */
(function () {
  "use strict";
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "\u0026amp;")
      .replace(/</g, "\u0026lt;")
      .replace(/>/g, "\u0026gt;")
      .replace(/"/g, "\u0026quot;");
  }
  window.esc = window.esc || esc;

  function paintCh(results) {
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
        return '<tr class="row-error channel-row" data-url="' + esc(url) + '"><td>' + cb + '</td><td>' + esc(name || url) +
          '</td><td>—</td><td>—</td><td>—</td><td>' + esc(url) + '</td><td>' + esc(r.email || "—") +
          '</td><td><span class="badge badge-err">❌ ' + esc(label) + '</span></td>' +
          '<td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="' + esc(url) + '">✕</button></td></tr>';
      }
      var views = (r.total_views_num != null && r.total_views_num !== "") ? r.total_views : (r.total_views || "0");
      return '<tr class="channel-row" data-url="' + esc(url) + '"><td>' + cb + '</td><td>' + esc(r.channel_name || "") +
        '</td><td>' + esc(r.subscribers || "0") + '</td><td>' + esc(views) + '</td><td>' + esc(r.videos_count || "0") +
        '</td><td><a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(url) + '</a></td><td>' +
        esc(r.email || "—") + '</td><td><span class="badge badge-ok">✅</span></td>' +
        '<td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="' + esc(url) + '">✕</button></td></tr>';
    }).join("");
    tbody.querySelectorAll(".btn-del-ch").forEach(function (btn) {
      btn.onclick = function (e) { e.stopPropagation(); App.deleteChannels([btn.getAttribute("data-url")]); };
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
        if (e.target && (e.target.tagName === "A" || e.target.tagName === "BUTTON" || e.target.tagName === "INPUT")) return;
        var cb = tr.querySelector(".ch-check");
        if (!cb) return;
        cb.checked = !cb.checked;
        tr.classList.toggle("row-selected", cb.checked);
      };
    });
  }

  function install() {
    if (!window.App) return false;
    App.setStatus = function (t) {
      var el = document.getElementById("status-text");
      if (el) el.textContent = "UI 20260819m \u00b7 " + t;
    };
    if (typeof App.api !== "function") return false;

    App.renderStats = function (results) {
      App._channelsCache = Array.isArray(results) ? results.slice() : [];
      paintCh(App._channelsCache);
    };
    App._paintChannels = paintCh;
    App.filterChannels = function () { paintCh(App._channelsCache || []); };
    App.onParseDone = function (results) {
      App.renderStats(Array.isArray(results) ? results : []);
      if (App.refreshHome) App.refreshHome();
      App.setStatus("Парсинг завершён");
    };

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
    App.deleteSelectedChannels = async function () {
      var urls = [];
      document.querySelectorAll(".ch-check:checked").forEach(function (x) { urls.push(x.getAttribute("data-url")); });
      if (!urls.length) { alert("Выберите каналы"); return; }
      if (!confirm("Удалить выбранные (" + urls.length + ")?")) return;
      await App.deleteChannels(urls);
    };
    App.deleteChannels = async function (urls) {
      var res = await App.api("delete_channels", null, urls || []);
      if (res && res.error) { alert(res.error); return; }
      App.renderStats((res && res.stats) || []);
      if (App.refreshHome) App.refreshHome();
    };
    App.importChannels = async function () {
      var ta = document.getElementById("channels-import");
      var text = ta ? ta.value : "";
      if (!text || !text.trim()) { alert("Вставьте список каналов"); return; }
      var fmt = "url_email";
      document.querySelectorAll('input[name="ch-format"]').forEach(function (r) { if (r.checked) fmt = r.value; });
      var res = await App.api("import_channels", text, fmt);
      if (!res || res.error) { alert((res && res.error) || "Ошибка"); return; }
      if (ta) ta.value = "";
      alert("Добавлено: " + (res.added || 0) + ", всего: " + (res.total || 0));
      var cached = await App.api("get_cached_stats");
      if (Array.isArray(cached)) App.renderStats(cached);
      if (App.refreshHome) App.refreshHome();
    };

    App.switchProject = async function (pid) {
      if (!pid) return;
      if (pid === "__all__") {
        if (App.showAllProjectsStats) await App.showAllProjectsStats();
        return;
      }
      App.viewMode = "project";
      App.setStatus("Смена проекта…");
      App.renderStats([]);
      var res = await App.api("switch_project", pid);
      if (!res || res.error) {
        alert((res && res.error) || "Не удалось сменить проект");
        return;
      }
      var stats = await App.api("get_cached_stats");
      App.renderStats(Array.isArray(stats) ? stats : []);
      if (App.refreshHome) await App.refreshHome();
      if (App.refreshAccounts) await App.refreshAccounts();
      if (App.loadExpenses) await App.loadExpenses();
      var sel = document.getElementById("project-select");
      if (sel) sel.value = pid;
      App.setStatus("Проект: " + (res.project_name || pid));
    };

    [["btn-ch-select-all", function () { App.selectAllChannels(true); }],
     ["btn-ch-select-none", function () { App.selectAllChannels(false); }],
     ["btn-ch-delete", function () { App.deleteSelectedChannels(); }],
     ["btn-ch-import", function () { App.importChannels(); }]
    ].forEach(function (pair) {
      var e = document.getElementById(pair[0]);
      if (e) e.onclick = pair[1];
    });
    var chAll = document.getElementById("ch-check-all");
    if (chAll) chAll.onchange = function () { App.selectAllChannels(!!chAll.checked); };
    var cs = document.getElementById("channels-search");
    if (cs) cs.oninput = function () { App.filterChannels(); };
    var sel = document.getElementById("project-select");
    if (sel) sel.onchange = function () { App.switchProject(sel.value); };

    document.title = "YT Analytics \u00b7 20260819m";
    App.setStatus("Готово");
    if (App._channelsCache && App._channelsCache.length) {
      paintCh(App._channelsCache);
    } else if (typeof App.loadCachedStats === "function") {
      App.loadCachedStats();
    }
    return true;
  }

  function boot() {
    if (!install()) { setTimeout(boot, 80); return; }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
