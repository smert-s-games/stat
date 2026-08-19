/* inline channel/account management v20260819f */
(function () {
  var VER = "20260819f";

  function boot() {
    if (!window.App || typeof App.api !== "function") {
      setTimeout(boot, 50);
      return;
    }

    try {
      var st = document.getElementById("status-text");
      if (st) st.textContent = "UI " + VER;
      var logo = document.querySelector(".logo");
      if (logo && logo.textContent.indexOf(VER) < 0) {
        logo.title = "build " + VER;
      }
      document.title = "YT Analytics · " + VER;
    } catch (e) {}

    function esc(s) {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function paintChannels(results) {
      App._channelsCache = Array.isArray(results) ? results.slice() : [];
      var tbody = document.getElementById("stats-tbody");
      if (!tbody) return;
      var qEl = document.getElementById("channels-search");
      var q = (qEl && qEl.value ? qEl.value : "").trim().toLowerCase();
      var list = App._channelsCache;
      if (q) {
        list = list.filter(function (r) {
          return (
            String(r.channel_name || "").toLowerCase().indexOf(q) >= 0 ||
            String(r.url || "").toLowerCase().indexOf(q) >= 0 ||
            String(r.email || "").toLowerCase().indexOf(q) >= 0
          );
        });
      }
      if (!list.length) {
        tbody.innerHTML =
          '<tr><td colspan="9" class="empty">' +
          (q ? "Ничего не найдено" : "Нет данных") +
          "</td></tr>";
        return;
      }
      tbody.innerHTML = list
        .map(function (r) {
          var name = String(r.channel_name || "");
          var err = r.error ? String(r.error) : "";
          var low = (err + " " + name).toLowerCase();
          var isBad =
            !!err || low.indexOf("404") >= 0 || name.trim().toLowerCase() === "youtube";
          var url = r.url || "";
          var cb = '<input type="checkbox" class="ch-check" data-url="' + esc(url) + '" />';
          if (isBad) {
            var label =
              err ||
              (name.trim().toLowerCase() === "youtube" ? "Неактивный канал" : "404 Not Found");
            return (
              '<tr class="row-error"><td>' +
              cb +
              "</td><td>" +
              esc(name || url) +
              "</td><td>—</td><td>—</td><td>—</td><td>" +
              esc(url) +
              "</td><td>" +
              esc(r.email || "—") +
              '</td><td><span class="badge badge-err">❌ ' +
              esc(label) +
              '</span></td><td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="' +
              esc(url) +
              '">✕</button></td></tr>'
            );
          }
          var views =
            r.total_views_num != null && r.total_views_num !== ""
              ? r.total_views
              : r.total_views || "0";
          return (
            "<tr><td>" +
            cb +
            "</td><td>" +
            esc(r.channel_name || "") +
            "</td><td>" +
            esc(r.subscribers || "0") +
            "</td><td>" +
            esc(views) +
            "</td><td>" +
            esc(r.videos_count || "0") +
            '</td><td><a href="#" class="ch-link" data-url="' +
            esc(url) +
            '">' +
            esc(url) +
            "</a></td><td>" +
            esc(r.email || "—") +
            '</td><td><span class="badge badge-ok">✅</span></td><td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="' +
            esc(url) +
            '">✕</button></td></tr>'
          );
        })
        .join("");
      tbody.querySelectorAll("a.ch-link").forEach(function (a) {
        a.onclick = function (ev) {
          ev.preventDefault();
          App.openUrl(a.getAttribute("data-url"));
        };
      });
      tbody.querySelectorAll(".btn-del-ch").forEach(function (btn) {
        btn.onclick = function () {
          App.deleteChannels([btn.getAttribute("data-url")]);
        };
      });
    }

    function paintAccounts(accounts) {
      App._accountsCache = Array.isArray(accounts) ? accounts.slice() : [];
      var tbody = document.getElementById("accounts-tbody");
      if (!tbody) return;
      var qEl = document.getElementById("accounts-search");
      var q = (qEl && qEl.value ? qEl.value : "").trim().toLowerCase();
      var list = App._accountsCache;
      if (q) {
        list = list.filter(function (a) {
          return (
            String(a.name || "").toLowerCase().indexOf(q) >= 0 ||
            String(a.folder_short || a.folder || "").toLowerCase().indexOf(q) >= 0
          );
        });
      }
      if (!list.length) {
        tbody.innerHTML =
          '<tr><td colspan="8" class="empty">' +
          (q ? "Ничего не найдено" : "Нет данных") +
          "</td></tr>";
        return;
      }
      tbody.innerHTML = list
        .map(function (a) {
          var key = a.path || a.folder || a.name || "";
          return (
            '<tr><td><input type="checkbox" class="acc-check" data-name="' +
            esc(a.name || "") +
            '" data-path="' +
            esc(key) +
            '" /></td><td>' +
            esc(a.name) +
            "</td><td>" +
            esc(a.folder_short || a.folder || "") +
            "</td><td>" +
            esc(a.materials_count) +
            "</td><td>" +
            esc(a.size) +
            "</td><td>" +
            esc(a.modified_date) +
            "</td><td>" +
            esc(a.quality_score) +
            '</td><td><button type="button" class="btn btn-ghost btn-sm btn-del-acc" data-name="' +
            esc(a.name || "") +
            '" data-path="' +
            esc(key) +
            '">✕</button></td></tr>'
          );
        })
        .join("");
      tbody.querySelectorAll(".btn-del-acc").forEach(function (btn) {
        btn.onclick = function () {
          App.deleteAccounts(
            [btn.getAttribute("data-name")],
            [btn.getAttribute("data-path")]
          );
        };
      });
    }

    App.renderStats = function (results) {
      paintChannels(results);
    };
    App._paintChannels = paintChannels;
    App.filterChannels = function () {
      paintChannels(App._channelsCache || []);
    };
    App.selectAllChannels = function (on) {
      var c = !!on;
      document.querySelectorAll(".ch-check").forEach(function (x) {
        x.checked = c;
      });
      var all = document.getElementById("ch-check-all");
      if (all) all.checked = c;
    };
    App.deleteSelectedChannels = async function () {
      var urls = [];
      document.querySelectorAll(".ch-check:checked").forEach(function (x) {
        urls.push(x.getAttribute("data-url"));
      });
      if (!urls.length) {
        alert("Выберите каналы");
        return;
      }
      if (!confirm("Удалить выбранные каналы (" + urls.length + ")?")) return;
      await App.deleteChannels(urls);
    };
    App.deleteChannels = async function (urls) {
      var res = await App.api("delete_channels", null, urls || []);
      if (res && res.error) {
        alert(res.error);
        return;
      }
      App.renderStats((res && res.stats) || []);
      if (App.refreshHome) App.refreshHome();
    };

    App._paintAccounts = paintAccounts;
    App.filterAccounts = function () {
      paintAccounts(App._accountsCache || []);
    };
    App.selectAllAccounts = function (on) {
      var c = !!on;
      document.querySelectorAll(".acc-check").forEach(function (x) {
        x.checked = c;
      });
      var all = document.getElementById("acc-check-all");
      if (all) all.checked = c;
    };
    App.deleteSelectedAccounts = async function () {
      var names = [],
        paths = [];
      document.querySelectorAll(".acc-check:checked").forEach(function (x) {
        names.push(x.getAttribute("data-name"));
        paths.push(x.getAttribute("data-path"));
      });
      if (!names.length) {
        alert("Выберите аккаунты");
        return;
      }
      if (!confirm("Удалить выбранные аккаунты (" + names.length + ")?")) return;
      await App.deleteAccounts(names, paths);
    };
    App.deleteAccounts = async function (names, paths) {
      var res = await App.api("delete_accounts", names || [], paths || []);
      if (res && res.error) {
        alert(res.error);
        return;
      }
      App._accountsCache = (res && res.accounts) || [];
      paintAccounts(App._accountsCache);
      if (App.refreshHome) App.refreshHome();
    };

    var _ra = App.refreshAccounts;
    if (typeof _ra === "function") {
      App.refreshAccounts = async function () {
        var data = await App.api("refresh_accounts");
        if (!data) return;
        if (data.error) {
          alert(data.error);
          return;
        }
        var foldersEl = document.getElementById("accounts-folders");
        if (foldersEl) {
          if (data.folders && data.folders.length) {
            foldersEl.innerHTML = data.folders
              .map(function (f, i) {
                return (
                  '<div class="script-item"><div class="script-path">' +
                  esc(f) +
                  '</div><button type="button" class="btn btn-ghost btn-sm" data-folder-idx="' +
                  i +
                  '">➖</button></div>'
                );
              })
              .join("");
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
        paintAccounts(data.accounts || []);
        if (App.refreshHome) App.refreshHome();
      };
    }

    App.importChannels = async function () {
      var ta = document.getElementById("channels-import");
      var text = ta ? ta.value : "";
      if (!text || !text.trim()) {
        alert("Вставьте список каналов");
        return;
      }
      var fmt = "url_email";
      document.querySelectorAll('input[name="ch-format"]').forEach(function (r) {
        if (r.checked) fmt = r.value;
      });
      try {
        var res = await App.api("import_channels", text, fmt);
        if (!res || res.error) {
          alert((res && res.error) || "Ошибка импорта");
          return;
        }
        if (ta) ta.value = "";
        var msg =
          "Добавлено: " +
          (res.added || 0) +
          ", обновлено: " +
          (res.updated || 0) +
          ", всего: " +
          (res.total || 0);
        alert(msg);
        if (App.setStatus) App.setStatus(msg);
        var cached = await App.api("get_cached_stats");
        if (Array.isArray(cached) && cached.length) {
          App.renderStats(cached);
        } else if (res.channels && res.channels.length) {
          App.renderStats(
            res.channels.map(function (c) {
              return {
                url: c.url,
                channel_name: c.name || c.url,
                email: c.email || "",
                subscribers: "—",
                total_views: "—",
                videos_count: "—",
              };
            })
          );
        }
        if (App.refreshHome) App.refreshHome();
      } catch (err) {
        alert("Ошибка: " + err);
      }
    };

    function bind() {
      var b;
      b = document.getElementById("btn-ch-select-all");
      if (b) b.onclick = function () { App.selectAllChannels(true); };
      b = document.getElementById("btn-ch-select-none");
      if (b) b.onclick = function () { App.selectAllChannels(false); };
      b = document.getElementById("btn-ch-delete");
      if (b) b.onclick = function () { App.deleteSelectedChannels(); };
      b = document.getElementById("btn-ch-import");
      if (b) b.onclick = function () { App.importChannels(); };
      b = document.getElementById("ch-check-all");
      if (b) b.onchange = function () { App.selectAllChannels(!!b.checked); };
      b = document.getElementById("channels-search");
      if (b) b.oninput = function () { App.filterChannels(); };

      b = document.getElementById("btn-acc-select-all");
      if (b) b.onclick = function () { App.selectAllAccounts(true); };
      b = document.getElementById("btn-acc-select-none");
      if (b) b.onclick = function () { App.selectAllAccounts(false); };
      b = document.getElementById("btn-acc-delete");
      if (b) b.onclick = function () { App.deleteSelectedAccounts(); };
      b = document.getElementById("acc-check-all");
      if (b) b.onchange = function () { App.selectAllAccounts(!!b.checked); };
      b = document.getElementById("accounts-search");
      if (b) b.oninput = function () { App.filterAccounts(); };
    }
    bind();
    setTimeout(bind, 200);
    setTimeout(bind, 800);
    setTimeout(function () {
      if (App._channelsCache && App._channelsCache.length) {
        paintChannels(App._channelsCache);
      } else if (typeof App.loadCachedStats === "function") {
        App.loadCachedStats();
      }
      if (App._accountsCache && App._accountsCache.length) {
        paintAccounts(App._accountsCache);
      }
    }, 900);
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
