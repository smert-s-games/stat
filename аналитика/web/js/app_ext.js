/* Extensions: multi-proxy, themes, stronger 404 badges */
(function () {
  if (!window.App) return;

  App.THEMES = [
    { id: "light", label: "Светлая" },
    { id: "dark", label: "Тёмная" },
    { id: "midnight", label: "Полночь" },
    { id: "ocean", label: "Океан" },
    { id: "forest", label: "Лес" },
    { id: "sunset", label: "Закат" },
    { id: "purple", label: "Фиолет" },
  ];

  var _renderStats = App.renderStats;
  App.renderStats = function (results) {
    var tbody = document.getElementById("stats-tbody");
    if (!tbody) return _renderStats && _renderStats.call(App, results);
    if (!results || !results.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">Нет данных</td></tr>';
      return;
    }
    tbody.innerHTML = results
      .map(function (r) {
        var errText = r.error ? String(r.error) : "";
        var isErr = !!(errText || r.status === "❌");
        if (isErr) {
          var label = errText || "404 Not Found";
          return (
            '<tr class="row-error"><td>' +
            esc(r.channel_name || r.url || "") +
            "</td><td>—</td><td>—</td><td>—</td><td>" +
            esc(r.url || "") +
            '</td><td>—</td><td><span class="badge badge-err">❌ ' +
            esc(label) +
            "</span></td></tr>"
          );
        }
        return (
          "<tr><td>" +
          esc(r.channel_name || "") +
          "</td><td>" +
          esc(r.subscribers || "0") +
          "</td><td>" +
          esc(r.total_views || "0") +
          "</td><td>" +
          esc(r.videos_count || "0") +
          '</td><td><a href="#" data-url="' +
          esc(r.url || "") +
          '">' +
          esc(r.url || "") +
          "</a></td><td>" +
          esc(r.email || "—") +
          '</td><td><span class="badge badge-ok">✅</span></td></tr>'
        );
      })
      .join("");
    tbody.querySelectorAll("a[data-url]").forEach(function (a) {
      a.onclick = function (e) {
        e.preventDefault();
        App.openUrl(a.getAttribute("data-url"));
      };
    });
  };

  App.renderThemePills = function () {
    var box = document.getElementById("theme-pills");
    if (!box) return;
    var cur = document.documentElement.getAttribute("data-theme") || "light";
    box.innerHTML = App.THEMES.map(function (t) {
      return (
        '<button type="button" class="theme-pill' +
        (t.id === cur ? " active" : "") +
        '" data-theme-id="' +
        t.id +
        '">' +
        t.label +
        "</button>"
      );
    }).join("");
    box.querySelectorAll("[data-theme-id]").forEach(function (btn) {
      btn.onclick = function () {
        App.setTheme(btn.getAttribute("data-theme-id"));
      };
    });
  };

  App.setTheme = async function (theme) {
    var res = await App.api("set_theme", theme);
    if (!res) return;
    document.documentElement.setAttribute("data-theme", res.theme);
    var st = document.getElementById("status-theme");
    if (st) st.textContent = "Тема: " + res.theme;
    App.renderThemePills();
  };

  App.loadProxies = async function () {
    var data = await App.api("get_proxies");
    var tbody = document.getElementById("proxies-tbody");
    if (!tbody) return;
    var list = (data && data.proxies) || [];
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty">Нет прокси</td></tr>';
      return;
    }
    tbody.innerHTML = list
      .map(function (pr) {
        return (
          "<tr><td>" +
          esc(pr.name) +
          "</td><td>" +
          esc(pr.host) +
          "</td><td>" +
          esc(pr.port) +
          "</td><td>" +
          esc(pr.type) +
          "</td><td>" +
          esc(pr.login) +
          "</td><td>" +
          esc(pr.purchase_date) +
          "</td><td>" +
          esc(pr.expiry_date) +
          "</td><td>" +
          esc(pr.notes) +
          '</td><td><button class="btn btn-ghost btn-sm" data-del-proxy="' +
          esc(pr.id) +
          '">X</button></td></tr>'
        );
      })
      .join("");
    tbody.querySelectorAll("[data-del-proxy]").forEach(function (btn) {
      btn.onclick = function () {
        App.deleteProxy(btn.getAttribute("data-del-proxy"));
      };
    });
  };

  App.addProxyFromForm = async function () {
    var g = function (id) {
      return ((document.getElementById(id) || {}).value || "").trim();
    };
    var res = await App.api("add_proxy", {
      name: g("px-name"),
      host: g("px-host"),
      port: g("px-port"),
      type: g("px-type") || "http",
      login: g("px-login"),
      password: g("px-pass"),
      purchase_date: g("px-buy"),
      expiry_date: g("px-exp"),
      notes: g("px-notes"),
    });
    var msg = document.getElementById("proxy-save-msg");
    if (res && res.ok) {
      if (msg) msg.textContent = "Сохранено";
      ["px-name", "px-host", "px-port", "px-login", "px-pass", "px-buy", "px-exp", "px-notes"].forEach(
        function (id) {
          var e = document.getElementById(id);
          if (e) e.value = "";
        }
      );
      await App.loadProxies();
      App.refreshHome();
    } else if (msg) msg.textContent = "Ошибка";
  };

  App.addProxy = function () {
    App.navigate("proxy");
    var n = document.getElementById("px-name");
    if (n) n.focus();
  };

  App.deleteProxy = async function (id) {
    if (!confirm("Удалить прокси?")) return;
    await App.api("delete_proxy", id);
    await App.loadProxies();
    App.refreshHome();
  };

  var _init = App.init;
  App.init = async function () {
    await _init.call(App);
    try {
      await App.loadProxies();
      App.renderThemePills();
      var cfg = await App.api("get_config");
      if (cfg && (cfg.ui_theme || cfg.theme)) {
        document.documentElement.setAttribute("data-theme", cfg.ui_theme || cfg.theme);
        App.renderThemePills();
      }
    } catch (e) {
      console.error("app_ext init", e);
    }
  };

  App.toggleTheme = async function () {
    var res = await App.api("toggle_theme");
    if (!res) return;
    document.documentElement.setAttribute("data-theme", res.theme);
    var st = document.getElementById("status-theme");
    if (st) st.textContent = "Тема: " + res.theme;
    App.renderThemePills();
  };
})();
