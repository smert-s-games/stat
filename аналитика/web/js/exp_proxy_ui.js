/* exp_proxy_ui 20260910a — fix expenses + proxies */
(function () {
  function ready(fn) {
    var n = 0;
    var t = setInterval(function () {
      if (!window.App && typeof App !== "undefined") window.App = App;
      if (window.App && App.api) {
        clearInterval(t);
        fn();
      } else if (++n > 100) clearInterval(t);
    }, 50);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  ready(function () {
    App.loadExpenses = async function () {
      var data = await App.api("get_expenses");
      var tbody = document.getElementById("expenses-tbody");
      if (!tbody) return;
      if (data && data.error) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">' + esc(data.error) + "</td></tr>";
        return;
      }
      var items = (data && data.items) || [];
      if (!items.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">Нет расходов</td></tr>';
        var tot0 = document.getElementById("exp-total");
        if (tot0) tot0.textContent = "Итого: 0";
        return;
      }
      tbody.innerHTML = items
        .map(function (e) {
          return (
            "<tr><td>" +
            esc(e.date) +
            "</td><td>" +
            esc(e.category) +
            "</td><td>" +
            esc(e.description) +
            "</td><td>" +
            esc(e.amount) +
            '</td><td><button type="button" class="btn btn-ghost btn-sm" data-del-exp="' +
            esc(e.id) +
            '">✕</button></td></tr>'
          );
        })
        .join("");
      tbody.querySelectorAll("[data-del-exp]").forEach(function (btn) {
        btn.onclick = function () {
          App.deleteExpense(btn.getAttribute("data-del-exp"));
        };
      });
      var tot = document.getElementById("exp-total");
      if (tot) tot.textContent = "Итого: " + (data.total != null ? data.total : 0);
    };

    App.addExpense = async function () {
      var amount = (document.getElementById("exp-amount") || {}).value;
      var description = (document.getElementById("exp-desc") || {}).value || "";
      var category = (document.getElementById("exp-cat") || {}).value || "";
      var date = (document.getElementById("exp-date") || {}).value || "";
      if (amount === "" || amount == null) {
        alert("Укажите сумму");
        return;
      }
      var res = await App.api("add_expense", amount, description, category, date);
      if (res && res.error) {
        alert(res.error);
        return;
      }
      ["exp-amount", "exp-desc", "exp-cat"].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.value = "";
      });
      await App.loadExpenses();
      if (App.refreshHome) App.refreshHome();
    };

    App.deleteExpense = async function (id) {
      if (!id) return;
      if (!confirm("Удалить расход?")) return;
      var res = await App.api("delete_expense", id);
      if (res && res.error) {
        alert(res.error);
        return;
      }
      await App.loadExpenses();
      if (App.refreshHome) App.refreshHome();
    };

    App.loadProxies = async function () {
      var data = await App.api("get_proxies");
      var tbody = document.getElementById("proxies-tbody");
      if (!tbody) return;
      if (data && data.error) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty">' + esc(data.error) + "</td></tr>";
        return;
      }
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
            '</td><td><button type="button" class="btn btn-ghost btn-sm" data-del-proxy="' +
            esc(pr.id) +
            '">✕</button></td></tr>'
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
      var val = function (id) {
        return ((document.getElementById(id) || {}).value || "").trim();
      };
      var res = await App.api("add_proxy", {
        name: val("px-name"),
        host: val("px-host"),
        port: val("px-port"),
        type: val("px-type") || "http",
        login: val("px-login"),
        password: val("px-pass"),
        purchase_date: val("px-buy"),
        expiry_date: val("px-exp"),
        notes: val("px-notes"),
      });
      var msg = document.getElementById("proxy-save-msg");
      if (res && res.error) {
        if (msg) msg.textContent = res.error;
        alert(res.error);
        return;
      }
      if (msg) msg.textContent = "Сохранено";
      ["px-name", "px-host", "px-port", "px-type", "px-login", "px-pass", "px-buy", "px-exp", "px-notes"].forEach(
        function (id) {
          var e = document.getElementById(id);
          if (e) e.value = "";
        }
      );
      await App.loadProxies();
      if (App.refreshHome) App.refreshHome();
    };

    App.deleteProxy = async function (id) {
      if (!id) return;
      if (!confirm("Удалить прокси?")) return;
      await App.api("delete_proxy", id);
      await App.loadProxies();
      if (App.refreshHome) App.refreshHome();
    };

    function on(id, fn) {
      var el = document.getElementById(id);
      if (el) el.onclick = fn;
    }
    on("btn-add-expense", function () { App.addExpense(); });
    on("btn-add-proxy", function () { App.addProxyFromForm(); });

    var pe = document.getElementById("page-expenses");
    if (pe && pe.classList.contains("active")) App.loadExpenses();
    var pp = document.getElementById("page-proxy");
    if (pp && pp.classList.contains("active")) App.loadProxies();

    var origNav = App.navigate;
    if (origNav && !App._expProxyNavHooked) {
      App.navigate = function (page) {
        origNav.call(App, page);
        if (page === "expenses") App.loadExpenses();
        if (page === "proxy") App.loadProxies();
      };
      App._expProxyNavHooked = true;
    }
  });
})();
