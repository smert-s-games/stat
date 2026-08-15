/* global pywebview */
const App = {
  selectedScript: null,
  parsing: false,

  async api(method, ...args) {
    try {
      if (!window.pywebview || !window.pywebview.api) {
        console.warn("pywebview API not ready");
        return null;
      }
      return await window.pywebview.api[method](...args);
    } catch (e) {
      console.error(method, e);
      App.setStatus("Ошибка: " + e);
      return null;
    }
  },

  setStatus(text) {
    const el = document.getElementById("status-text");
    if (el) el.textContent = text;
  },

  navigate(page) {
    document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
    const section = document.getElementById("page-" + page);
    if (section) section.classList.add("active");
    const nav = document.querySelector(`.nav-item[data-page="${page}"]`);
    if (nav) nav.classList.add("active");
  },

  async init() {
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => App.navigate(btn.dataset.page));
    });
    document.getElementById("btn-parse").onclick = () => App.startParse();
    document.getElementById("btn-export").onclick = () => App.exportStats();
    document.getElementById("btn-theme").onclick = () => App.toggleTheme();

    await App.loadConfig();
    await App.refreshHome();
    await App.refreshAccounts();
    await App.loadVideoScripts();
  },

  async loadConfig() {
    const cfg = await App.api("get_config");
    if (!cfg) return;
    document.documentElement.setAttribute("data-theme", cfg.theme || "light");
    document.getElementById("status-theme").textContent =
      "Тема: " + (cfg.theme === "dark" ? "Тёмная" : "Светлая");
    document.getElementById("links-file").value = cfg.links_file || "";
    document.getElementById("proxy-purchase").value = (cfg.proxy && cfg.proxy.purchase_date) || "";
    document.getElementById("proxy-expiry").value = (cfg.proxy && cfg.proxy.expiry_date) || "";
    document.getElementById("server-purchase").value = (cfg.server && cfg.server.purchase_date) || "";
    document.getElementById("server-expiry").value = (cfg.server && cfg.server.expiry_date) || "";
    document.getElementById("tg-token").value = cfg.telegram_bot_token || "";
    document.getElementById("tg-chat").value = cfg.telegram_chat_id || "";
  },

  async refreshHome() {
    const data = await App.api("get_dashboard");
    if (!data) return;
    document.getElementById("kpi-channels").textContent = data.channels ?? "—";
    document.getElementById("kpi-views").textContent = data.views ?? "—";
    document.getElementById("kpi-subs").textContent = data.subs ?? "—";
    document.getElementById("kpi-accounts").textContent = data.accounts ?? "—";
    document.getElementById("home-proxy").innerHTML =
      data.proxy_html || "<span class='empty'>Нет данных</span>";
  },

  async toggleTheme() {
    const res = await App.api("toggle_theme");
    if (!res) return;
    document.documentElement.setAttribute("data-theme", res.theme);
    document.getElementById("status-theme").textContent =
      "Тема: " + (res.theme === "dark" ? "Тёмная" : "Светлая");
    App.setStatus("Тема: " + res.theme);
  },

  async startParse() {
    if (App.parsing) {
      alert("Парсинг уже выполняется");
      return;
    }
    App.parsing = true;
    const btn = document.getElementById("stats-parse-btn");
    if (btn) btn.disabled = true;
    document.getElementById("stats-log").textContent = "Запуск парсинга…\n";
    App.setStatus("Парсинг…");
    App.navigate("stats");
    const res = await App.api("start_parse");
    if (res && res.error) {
      document.getElementById("stats-log").textContent += "\n❌ " + res.error;
      App.setStatus("Ошибка парсинга");
      App.parsing = false;
      if (btn) btn.disabled = false;
    }
  },

  onParseProgress(msg) {
    const log = document.getElementById("stats-log");
    log.textContent += msg;
    log.scrollTop = log.scrollHeight;
  },

  onParseDone(results) {
    App.parsing = false;
    const btn = document.getElementById("stats-parse-btn");
    if (btn) btn.disabled = false;
    App.renderStats(results || []);
    App.refreshHome();
    App.setStatus("Парсинг завершён: " + (results ? results.length : 0));
  },

  renderStats(results) {
    const tbody = document.getElementById("stats-tbody");
    if (!results.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">Нет данных</td></tr>';
      return;
    }
    tbody.innerHTML = results
      .map((r) => {
        if (r.error) {
          return `<tr>
            <td>${esc(r.url || "")}</td><td>-</td><td>-</td><td>-</td>
            <td>${esc(r.url || "")}</td><td>-</td>
            <td><span class="badge badge-err">❌ ${esc(r.error)}</span></td>
          </tr>`;
        }
        return `<tr>
          <td>${esc(r.channel_name || "")}</td>
          <td>${esc(r.subscribers || "0")}</td>
          <td>${esc(r.total_views || "0")}</td>
          <td>${esc(r.videos_count || "0")}</td>
          <td><a href="#" onclick="return App.openUrl('${esc(r.url || "")}')">${esc(r.url || "")}</a></td>
          <td>${esc(r.email || "—")}</td>
          <td><span class="badge badge-ok">✅</span></td>
        </tr>`;
      })
      .join("");
  },

  openUrl(url) {
    App.api("open_url", url);
    return false;
  },

  async pickLinksFile() {
    const path = await App.api("pick_file", "Выберите файл ссылок", [["Text", "*.txt"]]);
    if (path) {
      document.getElementById("links-file").value = path;
      App.setStatus("Файл ссылок: " + path);
    }
  },

  async exportStats() {
    const res = await App.api("export_stats");
    if (res && res.ok) App.setStatus("Экспорт: " + res.path);
    else if (res && res.error) alert(res.error);
  },

  async refreshAccounts() {
    App.setStatus("Обновление аккаунтов…");
    const data = await App.api("refresh_accounts");
    if (!data) return;
    const foldersEl = document.getElementById("accounts-folders");
    if (data.folders && data.folders.length) {
      foldersEl.innerHTML = data.folders
        .map((f) => `<div class="script-item"><div class="script-path">${esc(f)}</div></div>`)
        .join("");
    } else {
      foldersEl.innerHTML = '<div class="empty">Нет папок</div>';
    }
    const tbody = document.getElementById("accounts-tbody");
    if (!data.accounts || !data.accounts.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty">Нет данных</td></tr>';
    } else {
      tbody.innerHTML = data.accounts
        .map(
          (a) => `<tr>
          <td>${esc(a.name)}</td>
          <td>${esc(a.folder_short || a.folder || "")}</td>
          <td>${esc(a.materials_count)}</td>
          <td>${esc(a.size)}</td>
          <td>${esc(a.modified_date)}</td>
          <td>${esc(a.quality_score)}</td>
        </tr>`
        )
        .join("");
    }
    App.refreshHome();
    App.setStatus("Аккаунты: " + (data.accounts ? data.accounts.length : 0));
  },

  async addAccountsFolder() {
    const path = await App.api("pick_folder", "Папка с аккаунтами");
    if (path) {
      await App.api("add_accounts_folder", path);
      App.refreshAccounts();
    }
  },

  async loadVideoScripts() {
    const scripts = await App.api("get_video_scripts");
    const el = document.getElementById("video-scripts");
    App.selectedScript = null;
    if (!scripts || !scripts.length) {
      el.innerHTML = '<div class="empty">Нет скриптов</div>';
      return;
    }
    el.innerHTML = scripts
      .map(
        (s, i) => `<div class="script-item" data-idx="${i}" onclick="App.selectScript(${i}, this)">
        <div>
          <div><strong>${esc(s.name)}</strong></div>
          <div class="script-path">${esc(s.path)}</div>
        </div>
        <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();App.removeScript(${i})">➖</button>
      </div>`
      )
      .join("");
  },

  selectScript(idx, el) {
    document.querySelectorAll(".script-item").forEach((x) => x.classList.remove("selected"));
    el.classList.add("selected");
    App.selectedScript = idx;
  },

  async addVideoScript() {
    const path = await App.api("pick_file", "Python скрипт", [["Python", "*.py"]]);
    if (path) {
      await App.api("add_video_script", path);
      App.loadVideoScripts();
    }
  },

  async removeScript(idx) {
    await App.api("remove_video_script", idx);
    App.loadVideoScripts();
  },

  async runVideoScript() {
    if (App.selectedScript === null) {
      alert("Выберите скрипт");
      return;
    }
    document.getElementById("video-run-btn").disabled = true;
    document.getElementById("video-stop-btn").disabled = false;
    document.getElementById("video-log").textContent = "Запуск…\n";
    await App.api("run_video_script", App.selectedScript);
  },

  async stopVideoScript() {
    await App.api("stop_video_script");
  },

  onVideoLog(line) {
    const log = document.getElementById("video-log");
    log.textContent += line + "\n";
    log.scrollTop = log.scrollHeight;
  },

  onVideoDone(ok) {
    document.getElementById("video-run-btn").disabled = false;
    document.getElementById("video-stop-btn").disabled = true;
    App.setStatus(ok ? "Скрипт завершён" : "Скрипт остановлен/ошибка");
  },

  async saveProxy() {
    await App.api("save_proxy", {
      purchase_date: document.getElementById("proxy-purchase").value,
      expiry_date: document.getElementById("proxy-expiry").value,
    });
    App.setStatus("Прокси сохранён");
    App.refreshHome();
  },

  async saveServer() {
    await App.api("save_server", {
      purchase_date: document.getElementById("server-purchase").value,
      expiry_date: document.getElementById("server-expiry").value,
    });
    App.setStatus("Сервер сохранён");
    App.refreshHome();
  },

  async saveTelegram() {
    await App.api("save_telegram", {
      token: document.getElementById("tg-token").value,
      chat_id: document.getElementById("tg-chat").value,
    });
    App.setStatus("Telegram настройки сохранены");
  },

  async startBot() {
    document.getElementById("tg-start").disabled = true;
    document.getElementById("tg-stop").disabled = false;
    await App.api("start_bot");
  },

  async stopBot() {
    await App.api("stop_bot");
    document.getElementById("tg-start").disabled = false;
    document.getElementById("tg-stop").disabled = true;
  },

  onBotLog(msg) {
    const log = document.getElementById("tg-log");
    log.textContent += msg + "\n";
    log.scrollTop = log.scrollHeight;
  },
};

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

window.addEventListener("pywebviewready", () => App.init());
setTimeout(() => {
  if (window.pywebview && window.pywebview.api) App.init();
}, 500);
