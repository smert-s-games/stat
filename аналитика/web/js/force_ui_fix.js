/* force_ui_fix v20260819g — overrides broken painters every second until ok */
(function () {
  var VER = "20260819g";
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
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
      document.querySelectorAll(".ch-check").forEach(function (x) { x.checked = c; });
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
      var res = await App.api("delete_channels", null, urls);
      if (res && res.error) { alert(res.error); return; }
      App.renderStats((res && res.stats) || []);
    };
    App.deleteChannels = async function (urls) {
      var res = await App.api("delete_channels", null, urls || []);
      if (res && res.error) { alert(res.error); return; }
      App.renderStats((res && res.stats) || []);
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
          return { url: c.url, channel_name: c.name || c.url, email: c.email || "",
            subscribers: "—", total_views: "—", videos_count: "—" };
        }));
      }
    };

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
          return '<tr class="row-error"><td>' + cb + '</td><td>' + esc(name || url) +
            '</td><td>—</td><td>—</td><td>—</td><td>' + esc(url) + '</td><td>' + esc(r.email || "—") +
            '</td><td><span class="badge badge-err">❌ ' + esc(label) + '</span></td>' +
            '<td><button type="button" class="btn btn-ghost btn-sm" data-url="' + esc(url) + '" onclick="App.deleteChannels([this.getAttribute(\'data-url\')])">✕</button></td></tr>';
        }
        var views = (r.total_views_num != null && r.total_views_num !== "") ? r.total_views : (r.total_views || "0");
        return '<tr><td>' + cb + '</td><td>' + esc(r.channel_name || "") + '</td><td>' + esc(r.subscribers || "0") +
          '</td><td>' + esc(views) + '</td><td>' + esc(r.videos_count || "0") +
          '</td><td><a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(url) + '</a></td><td>' +
          esc(r.email || "—") + '</td><td><span class="badge badge-ok">✅</span></td>' +
          '<td><button type="button" class="btn btn-ghost btn-sm" data-url="' + esc(url) + '" onclick="App.deleteChannels([this.getAttribute(\'data-url\')])">✕</button></td></tr>';
      }).join("");
    }

    App.refreshAccounts = async function () {
      var data = await App.api("refresh_accounts");
      if (!data) return;
      if (data.error) { alert(data.error); return; }
      var foldersEl = document.getElementById("accounts-folders");
      if (foldersEl) {
        if (data.folders && data.folders.length) {
          foldersEl.innerHTML = data.folders.map(function (f, i) {
            return '<div class="script-item"><div class="script-path">' + esc(f) +
              '</div><button type="button" class="btn btn-ghost btn-sm" onclick="App.removeFolder(App._lastFolders[' + i + '])">➖</button></div>';
          }).join("");
          App._lastFolders = data.folders;
        } else foldersEl.innerHTML = '<div class="empty">Нет папок</div>';
      }
      App._accountsCache = data.accounts || [];
      paintAcc(App._accountsCache);
      if (App.refreshHome) App.refreshHome();
    };

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
        return '<tr><td><input type="checkbox" class="acc-check" data-name="' + esc(a.name || "") +
          '" data-path="' + esc(key) + '" /></td><td>' + esc(a.name) + '</td><td>' +
          esc(a.folder_short || a.folder || "") + '</td><td>' + esc(a.materials_count) +
          '</td><td>' + esc(a.size) + '</td><td>' + esc(a.modified_date) +
          '</td><td>' + esc(a.quality_score) +
          '</td><td><button type="button" class="btn btn-ghost btn-sm" onclick="App.deleteAccounts([\\' +
          esc(a.name || "").replace(/'/g, "\\'") + '\\'],[\\'' + esc(key).replace(/'/g, "\\'") + '\\'])">✕</button></td></tr>';
      }).join("");
    }
    App._paintAccounts = paintAcc;
    App.filterAccounts = function () { paintAcc(App._accountsCache || []); };
    App.selectAllAccounts = function (on) {
      var c = !!on;
      document.querySelectorAll(".acc-check").forEach(function (x) { x.checked = c; });
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
      var res = await App.api("delete_accounts", names, paths);
      if (res && res.error) { alert(res.error); return; }
      App._accountsCache = (res && res.accounts) || [];
      paintAcc(App._accountsCache);
    };
    App.deleteAccounts = async function (names, paths) {
      var res = await App.api("delete_accounts", names || [], paths || []);
      if (res && res.error) { alert(res.error); return; }
      App._accountsCache = (res && res.accounts) || [];
      paintAcc(App._accountsCache);
    };

    function bind() {
      var map = [
        ["btn-ch-select-all", function () { App.selectAllChannels(true); }],
        ["btn-ch-select-none", function () { App.selectAllChannels(false); }],
        ["btn-ch-delete", function () { App.deleteSelectedChannels(); }],
        ["btn-ch-import", function () { App.importChannels(); }],
        ["btn-acc-select-all", function () { App.selectAllAccounts(true); }],
        ["btn-acc-select-none", function () { App.selectAllAccounts(false); }],
        ["btn-acc-delete", function () { App.deleteSelectedAccounts(); }],
      ];
      map.forEach(function (pair) {
        var el = document.getElementById(pair[0]);
        if (el) el.onclick = pair[1];
      });
      var chAll = document.getElementById("ch-check-all");
      if (chAll) chAll.onchange = function () { App.selectAllChannels(!!chAll.checked); };
      var accAll = document.getElementById("acc-check-all");
      if (accAll) accAll.onchange = function () { App.selectAllAccounts(!!accAll.checked); };
      var cs = document.getElementById("channels-search");
      if (cs) cs.oninput = function () { App.filterChannels(); };
      var as = document.getElementById("accounts-search");
      if (as) as.oninput = function () { App.filterAccounts(); };
    }
    bind();

    var st = document.getElementById("status-text");
    if (st) st.textContent = "UI " + VER;
    document.title = "YT Analytics · " + VER;
    return true;
  }

  function loop() {
    install();
    var tb = document.getElementById("stats-tbody");
    if (tb && App._channelsCache && App._channelsCache.length) {
      if (!tb.querySelector(".ch-check")) App.renderStats(App._channelsCache);
    }
    var ab = document.getElementById("accounts-tbody");
    if (ab && App._accountsCache && App._accountsCache.length) {
      if (!ab.querySelector(".acc-check")) App._paintAccounts(App._accountsCache);
    }
  }
  setInterval(loop, 1000);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      setTimeout(loop, 100);
      setTimeout(loop, 500);
      setTimeout(loop, 1500);
    });
  } else {
    setTimeout(loop, 100);
    setTimeout(loop, 500);
  }
})();
