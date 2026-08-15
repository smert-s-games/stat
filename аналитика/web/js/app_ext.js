/* Extensions: multi-proxy, themes, 404, project isolation, all-projects */
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

  function isErrorRow(r) {
    if (!r) return true;
    var err = String(r.error == null ? "" : r.error);
    var st = String(r.status == null ? "" : r.status);
    var name = String(r.channel_name == null ? "" : r.channel_name).trim();
    var nameLow = name.toLowerCase();
    var blob = (err + " " + st + " " + nameLow).toLowerCase();
    if (blob.indexOf("404") >= 0) return true;
    if (blob.indexOf("not found") >= 0) return true;
    if (nameLow === "youtube" || nameLow === "www.youtube.com") return true;
    if (err !== "" && err !== "undefined" && err !== "null") return true;
    return false;
  }

  App.renderStats = function (results) {
    var tbody = document.getElementById("stats-tbody");
    if (!tbody) return;
    if (!results || !results.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">Нет данных</td></tr>';
      return;
    }
    tbody.innerHTML = results
      .map(function (r) {
        var err = String(r.error == null ? "" : r.error);
        var name = String(r.channel_name == null ? "" : r.channel_name);
        if (isErrorRow(r)) {
          var label = "Ошибка";
          var low = (err + " " + name).toLowerCase();
          if (name.trim().toLowerCase() === "youtube" || name.trim().toLowerCase() === "www.youtube.com") {
            label = "Неактивный канал";
          } else if (low.indexOf("404") >= 0 || low.indexOf("not found") >= 0) {
            label = "404 Not Found";
          } else if (err) {
            label = err;
          }
          return (
            '<tr class="row-error"><td>' +
            esc(name || r.url || "") +
            "</td><td>—</td><td>—</td><td>—</td><td>" +
            esc(r.url || "") +
            "</td><td>" +
            esc(r.email || r.project_name || "—") +
            '</td><td><span class="badge badge-err">❌ ' +
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

  App.showAllProjectsStats = async function () {
    App.viewMode = "all";
    var sel = document.getElementById("project-select");
    if (sel) sel.value = "__all__";
    var dash = await App.api("get_all_projects_dashboard");
    if (!dash || dash.error) {
      alert("Не удалось загрузить сводку: " + ((dash && dash.error) || "нет ответа"));
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
    if (hp) hp.innerHTML = dash.proxy_html || "<span class='empty'>Нет данных</span>";
    var data = await App.api("get_all_projects_stats");
    if (data && data.stats) {
      App.renderStats(data.stats);
      var log = document.getElementById("stats-log");
      if (log)
        log.textContent =
          "Все проекты: " + data.stats.length + " каналов из " + (data.projects_count || "?") + " проектов.\n";
    }
    App.navigate("home");
    App.setStatus("Все проекты: " + (dash.channels || 0) + " каналов");
  };

  App.loadProjects = async function () {
    var data = await App.api("list_projects");
    var sel = document.getElementById("project-select");
    if (!data || !sel) return;
    var prev = sel.value;
    var opts = '<option value="__all__">Все проекты</option>';
    opts += (data.projects || [])
      .map(function (p) {
        return (
          '<option value="' +
          esc(p.id) +
          '"' +
          (p.id === data.active_id ? " selected" : "") +
          ">" +
          esc(p.name) +
          "</option>"
        );
      })
      .join("");
    sel.innerHTML = opts;
    if (prev === "__all__") sel.value = "__all__";
  };

  App.switchProject = async function (pid) {
    if (!pid) return;
    if (pid === "__all__") {
      await App.showAllProjectsStats();
      return;
    }
    App.viewMode = "project";
    App.renderStats([]);
    var log = document.getElementById("stats-log");
    if (log) log.textContent = "Загрузка проекта…\n";
    await App.api("switch_project", pid);
    await App.reloadAll();
  };

  App.loadCachedStats = async function () {
    var results = await App.api("get_cached_stats");
    var list = Array.isArray(results) ? results : [];
    App.renderStats(list);
    var log = document.getElementById("stats-log");
    if (log) {
      if (list.length) log.textContent = "Сессия проекта: " + list.length + " каналов.\n";
      else log.textContent = "В этом проекте нет сохранённой статистики.\n";
    }
  };

  var _init = App.init;
  App.init = async function () {
    await _init.call(App);
    try {
      await App.loadProxies();
      App.renderThemePills();
      var btn = document.getElementById("btn-all-projects");
      if (btn) btn.style.display = "none";
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

  var _reloadAll = App.reloadAll;
  App.reloadAll = async function () {
    App.renderStats([]);
    await _reloadAll.call(App);
    var results = await App.api("get_cached_stats");
    App.renderStats(Array.isArray(results) ? results : []);
  };
})();
