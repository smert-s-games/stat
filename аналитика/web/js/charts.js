/* Stats charts UI 20260910b — per-project */
(function () {
  var charts = { views: null, subscribers: null, videos: null };
  var lastBundle = null;
  var COLORS = [
    "#6366f1", "#22c55e", "#f59e0b", "#ec4899", "#06b6d4",
    "#a855f7", "#ef4444", "#14b8a6"
  ];
  var METRICS = ["views", "subscribers", "videos"];

  function $(id) { return document.getElementById(id); }

  function ensureChartJs(cb) {
    if (window.Chart) { cb(); return; }
    var s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js";
    s.onload = function () { cb(); };
    s.onerror = function () {
      var box = $("charts-status");
      if (box) box.textContent = "Не удалось загрузить Chart.js (нужен интернет для CDN)";
    };
    document.head.appendChild(s);
  }

  function fmtNum(n) {
    n = Number(n) || 0;
    if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + " млрд";
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + " млн";
    if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + " тыс";
    return String(n);
  }

  function cssVar(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  }

  async function loadChannelOptions() {
    if (!window.App && typeof App !== "undefined") window.App = App;
    if (!window.App || !App.api) return;
    var res = await App.api("get_chart_channels");
    var sel = $("chart-channel");
    if (!sel || !res) return;
    var cur = sel.value;
    var opts = '<option value="">— канал —</option>';
    (res.channels || []).forEach(function (c) {
      opts += '<option value="' + (c.url || "").replace(/"/g, "&quot;") + '">' +
        (c.name || c.url || "").replace(/</g, "&lt;") + "</option>";
    });
    sel.innerHTML = opts;
    if (cur) sel.value = cur;
  }

  function destroyAll() {
    METRICS.forEach(function (m) {
      if (charts[m]) {
        try { charts[m].destroy(); } catch (e) {}
        charts[m] = null;
      }
    });
  }

  function setDelta(id, data) {
    var el = $(id);
    if (!el) return;
    var d = (data && data.delta) || 0;
    var sign = d > 0 ? "+" : "";
    var pct = data && data.growth_pct != null ? " (" + sign + data.growth_pct + "%)" : "";
    el.textContent = "Δ " + sign + fmtNum(d) + pct;
    el.style.color = d > 0 ? cssVar("--success", "#22c55e") : (d < 0 ? cssVar("--danger", "#ef4444") : cssVar("--muted", "#9ca3af"));
  }

  function renderOne(metric, data, ctype) {
    var canvas = $("chart-" + metric);
    if (!canvas || !window.Chart) return;
    if (charts[metric]) {
      try { charts[metric].destroy(); } catch (e) {}
      charts[metric] = null;
    }
    if (!data || !data.labels || !data.labels.length) return;

    var tick = cssVar("--chart-tick", "#94a3b8");
    var grid = cssVar("--chart-grid", "rgba(148,163,184,0.15)");
    var text = cssVar("--text", "#e2e8f0");

    var datasets = (data.series || []).map(function (s, i) {
      var c = COLORS[i % COLORS.length];
      return {
        label: s.name || ("Серия " + (i + 1)),
        data: s.data || [],
        borderColor: c,
        backgroundColor: ctype === "bar" ? c + "99" : c + "33",
        fill: ctype === "line",
        tension: 0.25,
        pointRadius: 2,
        pointHoverRadius: 4,
        borderWidth: 2,
      };
    });

    charts[metric] = new Chart(canvas.getContext("2d"), {
      type: ctype === "bar" ? "bar" : "line",
      data: { labels: data.labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: datasets.length > 1, labels: { color: text, boxWidth: 10, font: { size: 10 } } },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return (ctx.dataset.label || "") + ": " + fmtNum(ctx.parsed.y);
              }
            }
          }
        },
        scales: {
          x: {
            ticks: { maxRotation: 40, color: tick, font: { size: 10 } },
            grid: { color: grid }
          },
          y: {
            ticks: { color: tick, callback: function (v) { return fmtNum(v); }, font: { size: 10 } },
            grid: { color: grid }
          }
        }
      }
    });
  }

  async function refreshCharts() {
    if (!window.App && typeof App !== "undefined") window.App = App;
    if (!window.App || !App.api) return;
    var days = ($("chart-days") || {}).value || 30;
    var mode = ($("chart-mode") || {}).value || "total";
    var ctype = ($("chart-type") || {}).value || "line";
    var channel = ($("chart-channel") || {}).value || "";
    var status = $("charts-status");
    if (status) status.textContent = "Загрузка…";

    if (mode === "channel" && !channel) {
      if (status) status.textContent = "Выберите канал";
      destroyAll();
      return;
    }

    var pid = (document.getElementById("project-select") || {}).value || "";
    if (App.viewMode === "all") pid = "__all__";

    var results = {};
    var sources = [];
    var totalPoints = 0;
    for (var i = 0; i < METRICS.length; i++) {
      var metric = METRICS[i];
      var data = await App.api("get_charts_data", Number(days), metric, mode, channel, pid);
      results[metric] = data;
      if (data && data.labels && data.labels.length) {
        totalPoints = Math.max(totalPoints, data.labels.length);
        if (data.source) sources.push(data.source);
      }
      setDelta("delta-" + metric, data);
    }
    lastBundle = results;

    var any = METRICS.some(function (m) {
      return results[m] && results[m].labels && results[m].labels.length;
    });
    if (!any) {
      if (status) status.textContent = "Нет точек истории для этого проекта. Сделайте парсинг.";
      destroyAll();
      return;
    }

    if (status) {
      var pn = "";
      try {
        var first = results[METRICS[0]];
        if (first && first.project_name) pn = " · " + first.project_name;
      } catch (e) {}
      status.textContent = totalPoints + " точек · " + (sources[0] || "—") + pn;
    }

    ensureChartJs(function () {
      METRICS.forEach(function (m) { renderOne(m, results[m], ctype); });
    });
  }

  function exportCsv() {
    if (!lastBundle) {
      alert("Нет данных для экспорта");
      return;
    }
    var lines = ["metric,date,series,value"];
    METRICS.forEach(function (m) {
      var data = lastBundle[m];
      if (!data || !data.labels) return;
      (data.series || []).forEach(function (s) {
        for (var i = 0; i < data.labels.length; i++) {
          lines.push([
            m,
            '"' + String(data.labels[i]).replace(/"/g, '""') + '"',
            '"' + String(s.name || "").replace(/"/g, '""') + '"',
            s.data[i] != null ? s.data[i] : ""
          ].join(","));
        }
      });
    });
    var blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "stats_charts.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function bind() {
    ["chart-days", "chart-mode", "chart-type", "chart-channel"].forEach(function (id) {
      var el = $(id);
      if (!el || el._chartBound) return;
      el._chartBound = true;
      el.addEventListener("change", function () {
        if (id === "chart-mode") {
          var ch = $("chart-channel-wrap");
          if (ch) ch.style.display = el.value === "channel" ? "inline-flex" : "none";
        }
        refreshCharts();
      });
    });
    var btn = $("chart-refresh");
    if (btn && !btn._chartBound) {
      btn._chartBound = true;
      btn.addEventListener("click", function () { loadChannelOptions(); refreshCharts(); });
    }
    var exp = $("chart-export");
    if (exp && !exp._chartBound) {
      exp._chartBound = true;
      exp.addEventListener("click", exportCsv);
    }
  }

  function initCharts() {
    bind();
    loadChannelOptions().then(refreshCharts);
  }

  var tries = 0;
  var t = setInterval(function () {
    tries++;
    if (!window.App && typeof App !== "undefined") window.App = App;
    if (window.App) {
      clearInterval(t);
      var origNav = App.navigate;
      App.navigate = function (page) {
        origNav.call(App, page);
        if (page === "stats") {
          setTimeout(function () { loadChannelOptions(); refreshCharts(); }, 200);
        }
      };
      var origParseDone = App.onParseDone;
      App.onParseDone = function (results) {
        if (origParseDone) origParseDone.call(App, results);
        setTimeout(refreshCharts, 400);
      };
      var origTheme = App.toggleTheme;
      App.toggleTheme = async function () {
        var res = await origTheme.call(App);
        setTimeout(refreshCharts, 150);
        return res;
      };
      if (document.getElementById("page-stats") &&
          document.getElementById("page-stats").classList.contains("active")) {
        initCharts();
      } else {
        bind();
      }
      App.refreshCharts = refreshCharts;
      if (!App._chartsProjectHook && App.switchProject) {
        var _sp = App.switchProject;
        App.switchProject = async function (pid) {
          var r = await _sp.call(App, pid);
          setTimeout(function () { loadChannelOptions(); refreshCharts(); }, 300);
          return r;
        };
        App._chartsProjectHook = true;
      }
      if (!App._chartsAllHook && App.showAllProjectsStats) {
        var _all = App.showAllProjectsStats;
        App.showAllProjectsStats = async function () {
          var r = await _all.call(App);
          setTimeout(function () { loadChannelOptions(); refreshCharts(); }, 300);
          return r;
        };
        App._chartsAllHook = true;
      }
    } else if (tries > 80) clearInterval(t);
  }, 100);

  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(initCharts, 300);
  });
})();
