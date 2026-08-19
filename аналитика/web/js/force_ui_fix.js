/* UI 20260819h */
(function () {
  "use strict";
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g,"&").replace(/</g,"<").replace(/>/g,">").replace(/"/g,""");
  }
  window.esc = window.esc || esc;

  function bindNav() {
    if (!window.App) return;
    App.navigate = function (page) {
      document.querySelectorAll(".page").forEach(function (p) { p.classList.remove("active"); });
      document.querySelectorAll(".nav-item").forEach(function (n) { n.classList.remove("active"); });
      var section = document.getElementById("page-" + page);
      if (section) section.classList.add("active");
      var nav = document.querySelector('.nav-item[data-page="' + page + '"]');
      if (nav) nav.classList.add("active");
      if (page === "expenses" && App.loadExpenses) App.loadExpenses();
      if (page === "proxy" && App.loadProxies) App.loadProxies();
      if (page === "settings" && App.renderThemePills) App.renderThemePills();
    };
    document.querySelectorAll(".nav-item").forEach(function (btn) {
      btn.onclick = function () { App.navigate(btn.getAttribute("data-page")); };
    });
    var el;
    el = document.getElementById("btn-theme");
    if (el) el.onclick = function () { if (App.toggleTheme) App.toggleTheme(); };
    el = document.getElementById("btn-new-project");
    if (el) el.onclick = function () { if (App.newProject) App.newProject(); else if (App.createProject) App.createProject(); };
    el = document.getElementById("project-select");
    if (el) el.onchange = function () { if (App.switchProject) App.switchProject(el.value); };
  }

  function bindMgmt() {
    if (!window.App) return;
    function paintCh(results) {
      var tbody = document.getElementById("stats-tbody");
      if (!tbody) return;
      var qEl = document.getElementById("channels-search");
      var q = (qEl && qEl.value ? qEl.value : "").trim().toLowerCase();
      var list = results || [];
      if (q) list = list.filter(function (r) {
        return String(r.channel_name||"").toLowerCase().indexOf(q)>=0 || String(r.url||"").toLowerCase().indexOf(q)>=0 || String(r.email||"").toLowerCase().indexOf(q)>=0;
      });
      if (!list.length) { tbody.innerHTML = '<tr><td colspan="9" class="empty">'+(q?"Ничего не найдено":"Нет данных")+"</td></tr>"; return; }
      tbody.innerHTML = list.map(function (r) {
        var name = String(r.channel_name||"");
        var err = r.error ? String(r.error) : "";
        var low = (err+" "+name).toLowerCase();
        var isBad = !!err || low.indexOf("404")>=0 || name.trim().toLowerCase()==="youtube";
        var url = r.url||"";
        var cb = '<input type="checkbox" class="ch-check" data-url="'+esc(url)+'" />';
        if (isBad) {
          var label = err || (name.trim().toLowerCase()==="youtube"?"Неактивный канал":"404 Not Found");
          return '<tr class="row-error"><td>'+cb+'</td><td>'+esc(name||url)+'</td><td>—</td><td>—</td><td>—</td><td>'+esc(url)+'</td><td>'+esc(r.email||"—")+'</td><td><span class="badge badge-err">❌ '+esc(label)+'</span></td><td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="'+esc(url)+'">✕</button></td></tr>';
        }
        var views = (r.total_views_num!=null && r.total_views_num!=="") ? r.total_views : (r.total_views||"0");
        return '<tr><td>'+cb+'</td><td>'+esc(r.channel_name||"")+'</td><td>'+esc(r.subscribers||"0")+'</td><td>'+esc(views)+'</td><td>'+esc(r.videos_count||"0")+'</td><td><a href="'+esc(url)+'" target="_blank" rel="noopener">'+esc(url)+'</a></td><td>'+esc(r.email||"—")+'</td><td><span class="badge badge-ok">✅</span></td><td><button type="button" class="btn btn-ghost btn-sm btn-del-ch" data-url="'+esc(url)+'">✕</button></td></tr>';
      }).join("");
      tbody.querySelectorAll(".btn-del-ch").forEach(function (btn) {
        btn.onclick = function () { App.deleteChannels([btn.getAttribute("data-url")]); };
      });
    }
    App.renderStats = function (results) {
      App._channelsCache = Array.isArray(results) ? results.slice() : [];
      paintCh(App._channelsCache);
    };
    App._paintChannels = paintCh;
    App.filterChannels = function () { paintCh(App._channelsCache||[]); };
    App.selectAllChannels = function (on) {
      var c = !!on;
      document.querySelectorAll(".ch-check").forEach(function (x) { x.checked = c; });
      var all = document.getElementById("ch-check-all"); if (all) all.checked = c;
    };
    App.deleteSelectedChannels = async function () {
      var urls = [];
      document.querySelectorAll(".ch-check:checked").forEach(function (x) { urls.push(x.getAttribute("data-url")); });
      if (!urls.length) { alert("Выберите каналы"); return; }
      if (!confirm("Удалить выбранные ("+urls.length+")?")) return;
      await App.deleteChannels(urls);
    };
    App.deleteChannels = async function (urls) {
      var res = await App.api("delete_channels", null, urls||[]);
      if (res && res.error) { alert(res.error); return; }
      App.renderStats((res && res.stats)||[]);
      if (App.refreshHome) App.refreshHome();
    };
    App.importChannels = async function () {
      var ta = document.getElementById("channels-import");
      var text = ta ? ta.value : "";
      if (!text || !text.trim()) { alert("Вставьте список каналов"); return; }
      var fmt = "url_email";
      document.querySelectorAll('input[name="ch-format"]').forEach(function (r) { if (r.checked) fmt = r.value; });
      var res = await App.api("import_channels", text, fmt);
      if (!res || res.error) { alert((res && res.error)||"Ошибка"); return; }
      if (ta) ta.value = "";
      alert("Добавлено: "+(res.added||0)+", всего: "+(res.total||0));
      var cached = await App.api("get_cached_stats");
      if (Array.isArray(cached) && cached.length) App.renderStats(cached);
      else if (res.channels) App.renderStats(res.channels.map(function (c) {
        return {url:c.url, channel_name:c.name||c.url, email:c.email||"", subscribers:"—", total_views:"—", videos_count:"—"};
      }));
      if (App.refreshHome) App.refreshHome();
    };

    function paintAcc(accounts) {
      var tbody = document.getElementById("accounts-tbody");
      if (!tbody) return;
      var qEl = document.getElementById("accounts-search");
      var q = (qEl && qEl.value ? qEl.value : "").trim().toLowerCase();
      var list = accounts || [];
      if (q) list = list.filter(function (a) {
        return String(a.name||"").toLowerCase().indexOf(q)>=0 || String(a.folder_short||a.folder||"").toLowerCase().indexOf(q)>=0;
      });
      if (!list.length) { tbody.innerHTML = '<tr><td colspan="8" class="empty">'+(q?"Ничего не найдено":"Нет данных")+"</td></tr>"; return; }
      tbody.innerHTML = list.map(function (a) {
        var key = a.path || a.folder || a.name || "";
        return '<tr><td><input type="checkbox" class="acc-check" data-name="'+esc(a.name||"")+'" data-path="'+esc(key)+'" /></td><td>'+esc(a.name)+'</td><td>'+esc(a.folder_short||a.folder||"")+'</td><td>'+esc(a.materials_count)+'</td><td>'+esc(a.size)+'</td><td>'+esc(a.modified_date)+'</td><td>'+esc(a.quality_score)+'</td><td><button type="button" class="btn btn-ghost btn-sm btn-del-acc" data-name="'+esc(a.name||"")+'" data-path="'+esc(key)+'">✕</button></td></tr>';
      }).join("");
      tbody.querySelectorAll(".btn-del-acc").forEach(function (btn) {
        btn.onclick = function () { App.deleteAccounts([btn.getAttribute("data-name")],[btn.getAttribute("data-path")]); };
      });
    }
    App._paintAccounts = paintAcc;
    App.filterAccounts = function () { paintAcc(App._accountsCache||[]); };
    App.selectAllAccounts = function (on) {
      var c = !!on;
      document.querySelectorAll(".acc-check").forEach(function (x) { x.checked = c; });
      var all = document.getElementById("acc-check-all"); if (all) all.checked = c;
    };
    App.deleteSelectedAccounts = async function () {
      var names=[], paths=[];
      document.querySelectorAll(".acc-check:checked").forEach(function (x) {
        names.push(x.getAttribute("data-name")); paths.push(x.getAttribute("data-path"));
      });
      if (!names.length) { alert("Выберите аккаунты"); return; }
      if (!confirm("Удалить выбранные ("+names.length+")?")) return;
      await App.deleteAccounts(names, paths);
    };
    App.deleteAccounts = async function (names, paths) {
      var res = await App.api("delete_accounts", names||[], paths||[]);
      if (res && res.error) { alert(res.error); return; }
      App._accountsCache = (res && res.accounts)||[];
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
          foldersEl.innerHTML = data.folders.map(function (f,i) {
            return '<div class="script-item"><div class="script-path">'+esc(f)+'</div><button type="button" class="btn btn-ghost btn-sm" data-folder-idx="'+i+'">➖</button></div>';
          }).join("");
          foldersEl.querySelectorAll("[data-folder-idx]").forEach(function (btn) {
            btn.onclick = function () {
              var idx = parseInt(btn.getAttribute("data-folder-idx"),10);
              if (App.removeFolder) App.removeFolder(data.folders[idx]);
            };
          });
        } else foldersEl.innerHTML = '<div class="empty">Нет папок</div>';
      }
      App._accountsCache = data.accounts || [];
      paintAcc(App._accountsCache);
      if (App.refreshHome) App.refreshHome();
    };

    App.pickLinksFile = App.pickLinksFile || async function () {
      var p = prompt("Путь к файлу ссылок:"); if (!p) return;
      var inp = document.getElementById("links-file"); if (inp) inp.value = p;
      await App.api("set_links_file", p);
    };
    App.saveProxy = App.saveProxy || async function () {
      await App.api("save_proxy_dates", (document.getElementById("proxy-purchase")||{}).value||"", (document.getElementById("proxy-expiry")||{}).value||"");
      var m = document.getElementById("proxy-save-msg"); if (m) m.textContent = "Сохранено";
    };
    App.saveServer = App.saveServer || async function () {
      await App.api("save_server_dates", (document.getElementById("server-purchase")||{}).value||"", (document.getElementById("server-expiry")||{}).value||"");
      var m = document.getElementById("server-save-msg"); if (m) m.textContent = "Сохранено";
    };
    App.addProxyFromForm = App.addProxyFromForm || async function () {
      await App.api("add_proxy", {
        name:(document.getElementById("px-name")||{}).value||"",
        host:(document.getElementById("px-host")||{}).value||"",
        port:(document.getElementById("px-port")||{}).value||"",
        type:(document.getElementById("px-type")||{}).value||"http",
        login:(document.getElementById("px-login")||{}).value||"",
        password:(document.getElementById("px-pass")||{}).value||"",
        purchase_date:(document.getElementById("px-buy")||{}).value||"",
        expiry_date:(document.getElementById("px-exp")||{}).value||"",
        notes:(document.getElementById("px-notes")||{}).value||""
      });
      if (App.loadProxies) App.loadProxies();
    };
    App.saveTelegram = App.saveTelegram || async function () {
      await App.api("save_telegram", (document.getElementById("tg-token")||{}).value||"", (document.getElementById("tg-chat")||{}).value||"");
    };
    App.startBot = App.startBot || async function () { await App.api("start_bot"); };
    App.stopBot = App.stopBot || async function () { await App.api("stop_bot"); };
    App.runVideoScript = App.runVideoScript || async function () {
      if (App.selectedScript == null) { alert("Выберите скрипт"); return; }
      await App.api("run_video_script", App.selectedScript);
    };
    App.stopVideoScript = App.stopVideoScript || async function () { await App.api("stop_video_script"); };
    App.addVideoScript = App.addVideoScript || async function () {
      var p = prompt("Путь к .py:"); if (!p) return;
      await App.api("add_video_script", p.trim());
      if (App.loadVideoScripts) App.loadVideoScripts();
    };
    App.addExpense = App.addExpense || async function () {
      await App.api("add_expense", {
        amount:(document.getElementById("exp-amount")||{}).value,
        description:(document.getElementById("exp-desc")||{}).value,
        category:(document.getElementById("exp-cat")||{}).value,
        date:(document.getElementById("exp-date")||{}).value
      });
      if (App.loadExpenses) App.loadExpenses();
    };
    App.addAccountsFolder = App.addAccountsFolder || async function () {
      var path = prompt("Путь к папке аккаунтов:"); if (!path||!path.trim()) return;
      await App.api("add_accounts_folder", path.trim());
      App.refreshAccounts();
    };
    App.startParse = App.startParse || async function () {
      var links = (document.getElementById("links-file")||{}).value;
      if (links) await App.api("set_links_file", links);
      var res = await App.api("start_parse");
      if (res && res.error) alert(res.error);
    };

    [["btn-ch-select-all",function(){App.selectAllChannels(true);}],
     ["btn-ch-select-none",function(){App.selectAllChannels(false);}],
     ["btn-ch-delete",function(){App.deleteSelectedChannels();}],
     ["btn-ch-import",function(){App.importChannels();}],
     ["btn-acc-select-all",function(){App.selectAllAccounts(true);}],
     ["btn-acc-select-none",function(){App.selectAllAccounts(false);}],
     ["btn-acc-delete",function(){App.deleteSelectedAccounts();}]
    ].forEach(function (pair) {
      var e = document.getElementById(pair[0]); if (e) e.onclick = pair[1];
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

  function boot() {
    if (!window.App || typeof App.api !== "function") { setTimeout(boot, 80); return; }
    bindNav();
    bindMgmt();
    var st = document.getElementById("status-text");
    if (st) st.textContent = "UI 20260819h · Готово";
    document.title = "YT Analytics · 20260819h";
    setTimeout(function () {
      if (App._channelsCache && App._channelsCache.length) {
        var tb = document.getElementById("stats-tbody");
        if (tb && !tb.querySelector(".ch-check")) App.renderStats(App._channelsCache);
      }
      if (App._accountsCache && App._accountsCache.length && App._paintAccounts) {
        var ab = document.getElementById("accounts-tbody");
        if (ab && !ab.querySelector(".acc-check")) App._paintAccounts(App._accountsCache);
      }
    }, 600);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
