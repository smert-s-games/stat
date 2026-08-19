/* inline channel management - load after app.js */
(function () {
  function boot() {
    if (!window.App || typeof App.api !== "function") {
      setTimeout(boot, 50);
      return;
    }
    function paint(results) {
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
      function e(s) {
        return String(s == null ? "" : s)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;");
      }
      tbody.innerHTML = list
        .map(function (r) {
          var name = String(r.channel_name || "");
          var err = r.error ? String(r.error) : "";
          var low = (err + " " + name).toLowerCase();
          var isBad =
            !!err || low.indexOf("404") >= 0 || name.trim().toLowerCase() === "youtube";
          var url = r.url || "";
          var cb =
            '<input type="checkbox" class="ch-check" data-url="' + e(url) + '" />';
          if (isBad) {
            var label =
              err ||
              (name.trim().toLowerCase() === "youtube"
                ? "Неактивный канал"
                : "404 Not Found");
            return (
              '<tr class="row-error"><td>' +
              cb +
              "</td><td>" +
              e(name || url) +
              "</td><td>—</td><td>—</td><td>—</td><td>" +
              e(url) +
              "</td><td>" +
              e(r.email || "—") +
              '</td><td><span class="badge badge-err">❌ ' +
              e(label) +
              "</span></td><td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="" +
              e(url) +
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
            e(r.channel_name || "") +
            "</td><td>" +
            e(r.subscribers || "0") +
            "</td><td>" +
            e(views) +
            "</td><td>" +
            e(r.videos_count || "0") +
            '</td><td><a href="#" class="ch-link" data-url="' +
            e(url) +
            '">' +
            e(url) +
            "</a></td><td>" +
            e(r.email || "—") +
            '</td><td><span class="badge badge-ok">✅</span></td><td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="' +
            e(url) +
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
    App.renderStats = function (results) {
      paint(results);
    };
    App._paintChannels = paint;
    App.filterChannels = function () {
      paint(App._channelsCache || []);
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
    App.importChannels = async function () {
      var ta = document.getElementById("channels-import");
      var text = ta ? ta.value : "";
      if (!text || !text.trim()) {
        alert("Вставьте список каналов");
        return;
      }
      var fmt = "url";
      document.querySelectorAll('input[name="ch-format"]').forEach(function (r) {
        if (r.checked) fmt = r.value;
      });
      if (fmt === "url" && /https?:\/\/.+:[^\s]+@/.test(text)) fmt = "url_email";
      var res = await App.api("import_channels", text, fmt);
      if (!res || res.error) {
        alert((res && res.error) || "Ошибка");
        return;
      }
      if (ta) ta.value = "";
      var cached = await App.api("get_cached_stats");
      if (Array.isArray(cached) && cached.length) App.renderStats(cached);
      else if (res.channels) {
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
    function bind() {
      var b;
      b = document.getElementById("btn-ch-select-all");
      if (b) b.onclick = function () {
        App.selectAllChannels(true);
      };
      b = document.getElementById("btn-ch-select-none");
      if (b) b.onclick = function () {
        App.selectAllChannels(false);
      };
      b = document.getElementById("btn-ch-delete");
      if (b) b.onclick = function () {
        App.deleteSelectedChannels();
      };
      b = document.getElementById("btn-ch-import");
      if (b) b.onclick = function () {
        App.importChannels();
      };
      b = document.getElementById("ch-check-all");
      if (b)
        b.onchange = function () {
          App.selectAllChannels(!!b.checked);
        };
      b = document.getElementById("channels-search");
      if (b)
        b.oninput = function () {
          App.filterChannels();
        };
    }
    bind();
    setTimeout(bind, 300);
    setTimeout(function () {
      if (App._channelsCache && App._channelsCache.length) paint(App._channelsCache);
      else if (typeof App.loadCachedStats === "function") {
        App.loadCachedStats();
      }
    }, 700);
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
