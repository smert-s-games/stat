/* UI 20260819j — project switch + channel selection */
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
    tbody.innerHTML = list.map(function (r, idx) {
      var name = String(r.channel_name || "");
      var err = r.error ? String(r.error) : "";
      var low = (err + " " + name).toLowerCase();
      var isBad = !!err || low.indexOf("404") >= 0 || name.trim().toLowerCase() === "youtube";
      var url = r.url || "";
      var cb = '<input type="checkbox" class="ch-check" data-url="' + esc(url) + '" data-idx="' + idx + '" />';
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
        if (e.target && (e.target.tagName === "A" || e.target.tagName === "BUTTON" || e.target.tagName === "INPUT")) return;
        var cb = tr.querySelector(".ch-check");
        if (!cb) return;
        cb.checked = !cb.checked;
        tr.classList.toggle("row-selected", cb.checked);
      };
    });
  }

  function paintAcc(accounts) {
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
        if (e.target && (e.target.tagName === "BUTTON" || e.target.tagName === "INPUT")) return;
        var cb = tr.querySelector(".acc-check");
        if (!cb) return;
        cb.checked = !cb.checked;
        tr.classList.toggle("row-selected", cb.checked);
      };
    });
  }

  function install() {
    if (!window.App || typeof App.api !== "function") return false;

    App.renderStats = function (results) {
      App._channelsCache = Array.isArray(results) ? results.slice() : [];
      paintCh(App._channelsCache);
    };
    App._paintChannels = paintCh;
    App.filterChannels = function () { paintCh(App._channelsCache || []); };

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
      document.querySelectorAll(".ch-check:checked").forEach(function (x) {
        urls.push(x.getAttribute("data-url"));
      });
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
      document.querySelectorAll('input[name="ch-format"]').forEach(function (r) {
        if (r.checked) fmt = r.value;
      });
      var res = await App.api("import_channels", text, fmt);
      if (!res || res.error) { alert((res && res.error) || "Ошибка"); return; }
      if (ta) ta.value = "";
      alert("Добавлено: " + (res.added || 0) + ", всего: " + (res.total || 0));
      var cached = await App.api("get_cached_stats");
      if (Array.isArray(cached) && cached.length) App.renderStats(cached);
      else if (res.channels) {
        App.renderStats(res.channels.map(function (c) {
          return {
            url: c.url,
            channel_name: c.name || c.url,
            email: c.email || "",
            subscribers: "—",
            total_views: "—",
            videos_count: "—",
          };
        }));
      }
      if (App.refreshHome) App.refreshHome();
    };

    App._paintAccounts = paintAcc;
    App.filterAccounts = function () { paintAcc(App._accountsCache || []); };
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
    App.deleteSelectedAccounts = async function () {
      var names = [], paths = [];
      document.querySelectorAll(".acc-check:checked").forEach(function (x) {
        names.push(x.getAttribute("data-name"));
        paths.push(x.getAttribute("data-path"));
      });
      if (!names.length) { alert("Выберите аккаунты"); return; }
      if (!confirm("Удалить выбранные (" + names.length + ")?")) return;
      await App.deleteAccounts(names, paths);
    };
    App.deleteAccounts = async function (names, paths) {
      var res = await App.api("delete_accounts", names || [], paths || []);
      if (res && res.error) { alert(res.error); return; }
      App._accountsCache = (res && res.accounts) || [];
      paintAcc(App._accountsCache);
      if (App.refreshHome) App.refreshHome();
    };

    App.refreshAccounts = async function () {
      var data = await App.api("refresh_accounts");
      if (!data) return;
      if (data.error) { alert(data.error); return; }
      var foldersEl = document.getElementById("accounts-folders");
      if (foldersEl) {
        if (data.folders && data.folders.length) {
          foldersEl.innerHTML = data.folders.map(function (f, i) {
            return '<div class="script-item"><div class="script-path">' + esc(f) +
              '</div><button type="button" class="btn btn-ghost btn-sm" data-folder-idx="' + i + '">➖</button></div>';
          }).join("");
          foldersEl.querySelectorAll("[data-folder-idx]").forEach(function (btn) {
            btn.onclick = function () {
              var idx = parseInt(btn.getAttribute("data-folder-idx"), 10);
              if (App.removeFolder) App.removeFolder(data.folders[idx]);
            };
          });
        } else {
          foldersEl.innerHTML = '<div class="empty">Нет папок</div>';
        }
      }
      App._accountsCache = data.accounts || [];
      paintAcc(App._accountsCache);
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
      var log = document.getElementById("stats-log");
      if (log) log.textContent = "Загрузка проекта…\n";

      var res = await App.api("switch_project", pid);
      if (!res || res.error) {
        alert((res && res.error) || "Не удалось сменить проект");
        App.setStatus("Ошибка смены проекта");
        return;
      }

      var stats = await App.api("get_cached_stats");
      App.renderStats(Array.isArray(stats) ? stats : []);
      if (log) {
        var n = Array.isArray(stats) ? stats.length : 0;
        log.textContent = n ? ("Проект: " + (res.project_name || "") + " — " + n + " каналов.\n") : "В проекте нет статистики.\n";
      }
      if (App.refreshHome) await App.refreshHome();
      if (App.refreshAccounts) await App.refreshAccounts();
      if (App.loadExpenses) await App.loadExpenses();
      if (App.loadConfig) await App.loadConfig();

      var sel = document.getElementById("project-select");
      if (sel) sel.value = pid;

      App.setStatus("Проект: " + (res.project_name || pid));
    };

    App.loadProjects = async function () {
      var data = await App.api("list_projects");
      var sel = document.getElementById("project-select");
      if (!data || !sel) return;
      var cur = sel.value;
      var opts = '<option value="__all__">Все проекты</option>';
      (data.projects || []).forEach(function (p) {
        var selAttr = (p.id === data.active_id) ? " selected" : "";
        opts += '<option value="' + esc(p.id) + '"' + selAttr + ">" + esc(p.name) + "</option>";
      });
      sel.innerHTML = opts;
      if (cur && cur !== "__all__") {
        var found = false;
        for (var i = 0; i < sel.options.length; i++) {
          if (sel.options[i].value === cur) { found = true; break; }
        }
        if (found) sel.value = cur;
      }
      sel.onchange = function () { App.switchProject(sel.value); };
    };

    function bind() {
      var pairs = [
        ["btn-ch-select-all", function () { App.selectAllChannels(true); }],
        ["btn-ch-select-none", function () { App.selectAllChannels(false); }],
        ["btn-ch-delete", function () { App.deleteSelectedChannels(); }],
        ["btn-ch-import", function () { App.importChannels(); }],
        ["btn-acc-select-all", function () { App.selectAllAccounts(true); }],
        ["btn-acc-select-none", function () { App.selectAllAccounts(false); }],
        ["btn-acc-delete", function () { App.deleteSelectedAccounts(); }],
      ];
      pairs.forEach(function (pair) {
        var e = document.getElementById(pair[0]);
        if (e) e.onclick = pair[1];
      });
      var chAll = document.getElementById("ch-check-all");
      if (chAll) chAll.onchange = function () { App.selectAllChannels(!!chAll.checked); };
      var accAll = document.getElementById("acc-check-all");
      if (accAll) accAll.onchange = function () { App.selectAllAccounts(!!accAll.checked); };
      var cs = document.getElementById("channels-search");
      if (cs) cs.oninput = function () { App.filterChannels(); };
      var as = document.getElementById("accounts-search");
      if (as) as.oninput = function () { App.filterAccounts(); };
      var sel = document.getElementById("project-select");
      if (sel) sel.onchange = function () { App.switchProject(sel.value); };
    }
    bind();

    document.title = "YT Analytics · 20260819j";
    return true;
  }

  function boot() {
    if (!install()) {
      setTimeout(boot, 80);
      return;
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
