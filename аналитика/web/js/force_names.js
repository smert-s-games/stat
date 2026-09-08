/* force channel names UI 20260819r */
(function () {
  function fixName(name, url) {
    var n = String(name || "").trim().toLowerCase();
    var bad = !n || n === "неизвестно" || n === "подписаться" || n === "subscribe" ||
      n === "поиск" || n === "search" || n === "youtube" ||
      (n.indexOf("подпис") === 0 && n.length < 20);
    if (!bad) return name;
    var m = String(url || "").match(/youtube\.com\/@([^/?&#]+)/i);
    if (m) return "@" + m[1];
    m = String(url || "").match(/youtube\.com\/(?:channel\/|c\/|user\/)([^/?&#]+)/i);
    if (m) return m[1];
    return name || url || "—";
  }
  function patch() {
    if (!window.App) return false;
    App.UI_VER = "20260819r";
    App.fixChannelName = fixName;
    var orig = App._paintChannelsTable;
    if (orig && !App._paintPatchedR) {
      App._paintChannelsTable = function (results) {
        var list = (results || []).map(function (r) {
          if (!r || typeof r !== "object") return r;
          var x = Object.assign({}, r);
          x.channel_name = fixName(x.channel_name, x.url);
          return x;
        });
        return orig.call(App, list);
      };
      App._paintPatchedR = true;
    }
    var st = document.getElementById("status-text");
    if (st && st.textContent.indexOf("20260819r") < 0) {
      st.textContent = "UI 20260819r · " + (st.textContent.replace(/^UI\s+\S+\s*·\s*/, "") || "Готово");
    }
    if (App._channelsCache && App._channelsCache.length && App._paintChannelsTable) {
      App._paintChannelsTable(App._channelsCache);
    }
    return true;
  }
  var n = 0;
  var t = setInterval(function () {
    if (patch() || ++n > 50) clearInterval(t);
  }, 100);
  document.addEventListener("DOMContentLoaded", patch);
})();
