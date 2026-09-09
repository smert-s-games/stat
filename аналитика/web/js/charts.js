/* Stats charts UI 20260909a */
(function () {
  var chartInst = null;
  var COLORS = [
    "#6366f1", "#22c55e", "#f59e0b", "#ec4899", "#06b6d4",
    "#a855f7", "#ef4444", "#14b8a6"
  ];

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

  function metricLabel(m) {
    if (m === "subscribers") return "Подписчики";
    if (m === "videos") return "Видео";
    return "Просмотры";
  }

  function fmtNum(n) {
    n = Number(n) || 0;
    if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + " млрд";
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + " млн";
    if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + " тыс";
    return String(n);
  }

  async function loadChannelOptions() {
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

  function destroyChart() {
    if (chartInst) {
      try { chartInst.destroy(); } catch (e) {}
      chartInst = null;
    }
  }

  async function refreshCharts() {
    if (!window.App || !App.api) return;
    var days = ($("chart-days") || {}).value || 30;
    var metric = ($("chart-metric") || {}).value || "views";
    var mode = ($("chart-mode") || {}).value || "total";
    var ctype = ($("chart-type") || {}).value || "line";
    var channel = ($("chart-channel") || {}).value || "";
    var status = $("charts-status");
    if (status) status.textContent = "Загрузка…";

    if (mode === "channel" && !channel) {
      if (status) status.textContent = "Выберите канал";
      destroyChart();
      return;
    }

    var data = await App.api("get_charts_data", Number(days), metric, mode, channel);
    if (!data || data.error) {
      if (status) status.textContent = "Ошибка: " + ((data && data.error) || "нет данных");
      destroyChart();
      return;
    }

    var deltaEl = $("chart-delta");
    if (deltaEl) {
      var d = data.delta || 0;
      var sign = d > 0 ? "+" : "";
      var pct = data.growth_pct != null ? " (" + sign + data.growth_pct + "%)" : "";
      deltaEl.textContent = "Δ " + sign + fmtNum(d) + pct;
      deltaEl.style.color = d > 0 ? "var(--success, #22c55e)" : (d < 0 ? "var(--danger, #ef4444)" : "var(--muted)");
    }

    if (!data.labels || !data.labels.length) {
      if (status) status.textContent = "Нет точек истории. Сделайте несколько парсингов — график заполнится.";
      destroyChart();
      return;
    }

    if (status) {
      status.textContent = data.points + " точек · источник: " + (data.source || "—") + " · " + metricLabel(metric);
    }

    ensureChartJs(function () {
      var canvas = $("stats-chart");
      if (!canvas || !window.Chart) return;
      destroyChart();
      var datasets = (data.series || []).map(function (s, i) {
        var c = COLORS[i % COLORS.length];
        return {
          label: s.name || ("Серия " + (i + 1)),
          data: s.data || [],
          borderColor: c,
          backgroundColor: ctype === "bar" ? c + "99" : c + "33",
          fill: ctype === "line",
          tension: 0.25,
          pointRadius: 3,
          pointHoverRadius: 5,
          borderWidth: 2,
        };
      });
      var ctx = canvas.getContext("2d");
      chartInst = new Chart(ctx, {
        type: ctype === "bar" ? "bar" : "line",
        data: { labels: data.labels, datasets: datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { display: datasets.length > 1, labels: { color: getComputedStyle(document.documentElement).getPropertyValue("--text") || "#e2e8f0" } },
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
              ticks: { maxRotation: 45, color: "#94a3b8", font: { size: 11 } },
              grid: { color: "rgba(148,163,184,0.15)" }
            },
            y: {
              ticks: {
                color: "#94a3b8",
                callback: function (v) { return fmtNum(v); }
              },
              grid: { color: "rgba(148,163,184,0.15)" }
            }
          }
        }
      });
    });
  }

  function exportCsv() {
    if (!chartInst) {
      alert("Нет данных для экспорта");
      return;
    }
    var labels = chartInst.data.labels || [];
    var sets = chartInst.data.datasets || [];
    var lines = ["date," + sets.map(function (s) { return '"' + (s.label || "").replace(/"/g, '""') + '"'; }).join(",")];
    for (var i = 0; i < labels.length; i++) {
      var row = ['"' + labels[i] + '"'];
      sets.forEach(function (s) { row.push(s.data[i] != null ? s.data[i] : ""); });
      lines.push(row.join(","));
    }
    var blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "stats_chart.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function bind() {
    ["chart-days", "chart-metric", "chart-mode", "chart-type", "chart-channel"].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      el.addEventListener("change", function () {
        if (id === "chart-mode") {
          var ch = $("chart-channel-wrap");
          if (ch) ch.style.display = el.value === "channel" ? "inline-flex" : "none";
        }
        refreshCharts();
      });
    });
    var btn = $("chart-refresh");
    if (btn) btn.addEventListener("click", function () { loadChannelOptions(); refreshCharts(); });
    var exp = $("chart-export");
    if (exp) exp.addEventListener("click", exportCsv);
  }

  function initCharts() {
    bind();
    loadChannelOptions().then(refreshCharts);
  }

  var tries = 0;
  var t = setInterval(function () {
    tries++;
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
      if (document.getElementById("page-stats") &&
          document.getElementById("page-stats").classList.contains("active")) {
        initCharts();
      } else {
        bind();
      }
      App.refreshCharts = refreshCharts;
    } else if (tries > 80) clearInterval(t);
  }, 100);

  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(initCharts, 300);
  });
})();
