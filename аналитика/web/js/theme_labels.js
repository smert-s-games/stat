/* Theme labels RU 20260909b */
(function () {
  var NAMES = {
    light: "Светлая", dark: "Тёмная", midnight: "Полночь", ocean: "Океан",
    forest: "Лес", sunset: "Закат", purple: "Фиолет", rose: "Роза",
    slate: "Сланец", sand: "Песок"
  };
  function label(t) { return NAMES[t] || t; }
  function apply(theme) {
    if (!theme) return;
    document.documentElement.setAttribute("data-theme", theme);
    var st = document.getElementById("status-theme");
    if (st) st.textContent = "Тема: " + label(theme);
  }
  var n = 0;
  var t = setInterval(function () {
    n++;
    if (!window.App) { if (n > 80) clearInterval(t); return; }
    clearInterval(t);
    var orig = App.toggleTheme;
    App.toggleTheme = async function () {
      var res = await orig.call(App);
      if (res && res.theme) apply(res.theme);
      return res;
    };
    var cur = document.documentElement.getAttribute("data-theme");
    if (cur) apply(cur);
  }, 100);
})();
