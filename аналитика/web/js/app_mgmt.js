/* Channel/account management extensions */
(function () {
  if (!window.App) return;

  App._channelsCache = App._channelsCache || [];
  App._accountsCache = App._accountsCache || [];

  App.renderStats = function (results) {
    App._channelsCache = Array.isArray(results) ? results.slice() : [];
    App._paintChannels(App._channelsCache);
  };

  App._paintChannels = function (results) {
    var tbody = document.getElementById("stats-tbody");
    if (!tbody) return;
    var q = ((document.getElementById("channels-search") || {}).value || "").trim().toLowerCase();
    var list = results || [];
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
        '<tr><td colspan="9" class="empty">' + (q ? "Ничего не найдено" : "Нет данных") + "</td></tr>";
      return;
    }
    tbody.innerHTML = list
      .map(function (r) {
        var name = String(r.channel_name || "");
        var err = r.error ? String(r.error) : "";
        var low = (err + " " + name).toLowerCase();
        var isBad = !!err || low.indexOf("404") >= 0 || name.trim().toLowerCase() === "youtube";
        var url = r.url || "";
        if (isBad) {
          var label =
            err || (name.trim().toLowerCase() === "youtube" ? "Неактивный канал" : "404 Not Found");
          return (
            '<tr class="row-error"><td><input type="checkbox" class="ch-check" data-url="' +
            esc(url) +
            '" /></td><td>' +
            esc(name || url) +
            "</td><td>—</td><td>—</td><td>—</td><td>" +
            esc(url) +
            "</td><td>" +
            esc(r.email || "—") +
            '</td><td><span class="badge badge-err">❌ ' +
            esc(label) +
            '</span></td><td><button class="btn btn-ghost btn-sm btn-icon" data-del-ch="' +
            esc(url) +
            '">✕</button></td></tr>'
          );
        }
        var views =
          r.total_views_num != null && r.total_views_num !== "" ? r.total_views : r.total_views || "0";
        return (
          '<tr><td><input type="checkbox" class="ch-check" data-url="' +
          esc(url) +
          '" /></td><td>' +
          esc(r.channel_name || "") +
          "</td><td>" +
          esc(r.subscribers || "0") +
          "</td><td>" +
          esc(views) +
          "</td><td>" +
          esc(r.videos_count || "0") +
          '</td><td><a href="#" data-url="' +
          esc(url) +
          '">' +
          esc(url) +
          "</a></td><td>" +
          esc(r.email || "—") +
          '</td><td><span class="badge badge-ok">✅</span></td><td><button class="btn btn-ghost btn-sm btn-icon" data-del-ch="' +
          esc(url) +
          '">✕</button></td></tr>'
        );
      })
      .join("");
    tbody.querySelectorAll("a[data-url]").forEach(function (a) {
      a.onclick = function (e) {
        e.preventDefault();
        App.openUrl(a.getAttribute("data-url"));
      };
    });
    tbody.querySelectorAll("[data-del-ch]").forEach(function (btn) {
      btn.onclick = function () {
        App.deleteChannels([btn.getAttribute("data-del-ch")]);
      };
    });
  };

  App.filterChannels = function () {
    App._paintChannels(App._channelsCache);
  };

  App.selectAllChannels = function (on) {
    var checked = !!on;
    document.querySelectorAll(".ch-check").forEach(function (c) {
      c.checked = checked;
    });
    var all = document.getElementById("ch-check-all");
    if (all) all.checked = checked;
  };

  App.deleteSelectedChannels = async function () {
    var urls = [];
    document.querySelectorAll(".ch-check:checked").forEach(function (c) {
      urls.push(c.getAttribute("data-url"));
    });
    if (!urls.length) {
      alert("Выберите каналы");
      return;
    }
    if (!confirm("Удалить выбранные каналы (" + urls.length + ")?")) return;
    await App.deleteChannels(urls);
  };

  App.deleteChannels = async function (urls) {
    var res = await App.api("delete_channels", null, urls);
    if (res && res.error) {
      alert(res.error);
      return;
    }
    App.renderStats((res && res.stats) || []);
    App.refreshHome();
    App.setStatus("Удалено каналов: " + ((res && res.removed) || 0));
  };

  App.importChannels = async function () {
    var ta = document.getElementById("channels-import");
    var text = ta ? ta.value : "";
    if (!text.trim()) {
      alert("Вставьте список каналов");
      return;
    }
    var fmt = "url";
    document.querySelectorAll('input[name="ch-format"]').forEach(function (r) {
      if (r.checked) fmt = r.value;
    });
    var res = await App.api("import_channels", text, fmt);
    if (!res || res.error) {
      alert((res && res.error) || "Ошибка импорта");
      return;
    }
    if (ta) ta.value = "";
    App.setStatus("Добавлено: " + (res.added || 0) + " · всего: " + (res.total || 0));
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
  };

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
              '</div><button class="btn btn-ghost btn-sm" data-folder-idx="' +
              i +
              '">➖</button></div>'
            );
          })
          .join("");
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
    App._accountsCache = data.accounts || [];
    App._paintAccounts(App._accountsCache);
    App.refreshHome();
  };

  App._paintAccounts = function (accounts) {
    var tbody = document.getElementById("accounts-tbody");
    if (!tbody) return;
    var q = ((document.getElementById("accounts-search") || {}).value || "").trim().toLowerCase();
    var list = accounts || [];
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
        '<tr><td colspan="8" class="empty">' + (q ? "Ничего не найдено" : "Нет данных") + "</td></tr>";
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
          '</td><td><button class="btn btn-ghost btn-sm btn-icon" data-del-acc="' +
          esc(a.name || "") +
          '" data-del-path="' +
          esc(key) +
          '">✕</button></td></tr>'
        );
      })
      .join("");
    tbody.querySelectorAll("[data-del-acc]").forEach(function (btn) {
      btn.onclick = function () {
        App.deleteAccounts([btn.getAttribute("data-del-acc")], [btn.getAttribute("data-del-path")]);
      };
    });
  };

  App.filterAccounts = function () {
    App._paintAccounts(App._accountsCache);
  };

  App.selectAllAccounts = function (on) {
    var checked = !!on;
    document.querySelectorAll(".acc-check").forEach(function (c) {
      c.checked = checked;
    });
    var all = document.getElementById("acc-check-all");
    if (all) all.checked = checked;
  };

  App.deleteSelectedAccounts = async function () {
    var names = [],
      paths = [];
    document.querySelectorAll(".acc-check:checked").forEach(function (c) {
      names.push(c.getAttribute("data-name"));
      paths.push(c.getAttribute("data-path"));
    });
    if (!names.length) {
      alert("Выберите аккаунты");
      return;
    }
    if (!confirm("Удалить выбранные аккаунты (" + names.length + ") из списка?")) return;
    await App.deleteAccounts(names, paths);
  };

  App.deleteAccounts = async function (names, paths) {
    var res = await App.api("delete_accounts", names || [], paths || []);
    if (res && res.error) {
      alert(res.error);
      return;
    }
    App._accountsCache = (res && res.accounts) || [];
    App._paintAccounts(App._accountsCache);
    App.refreshHome();
    App.setStatus("Удалено аккаунтов: " + ((res && res.removed) || 0));
  };

  App.applyAccountsSort = async function (mode) {
    var accounts = await App.api("sort_accounts_results", mode);
    if (!accounts) return;
    App._accountsCache = accounts;
    App._paintAccounts(accounts);
  };
})();
