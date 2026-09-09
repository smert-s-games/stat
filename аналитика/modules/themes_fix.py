"""Cycle all UI themes instead of only light/dark."""
from __future__ import annotations

THEMES = [
    "light", "dark", "midnight", "ocean", "forest",
    "sunset", "purple", "rose", "slate", "sand",
]


def apply_themes_fix(WebAPI):
    WebAPI.THEMES = THEMES

    def toggle_theme(self):
        cur = self.config.get("theme") or self.config.get("ui_theme") or "light"
        try:
            i = THEMES.index(cur)
        except ValueError:
            i = 0
        nxt = THEMES[(i + 1) % len(THEMES)]
        self.config["theme"] = nxt
        self.config["ui_theme"] = nxt
        try:
            self._save_legacy_config()
        except Exception:
            pass
        return {"theme": nxt, "themes": list(THEMES)}

    WebAPI.toggle_theme = toggle_theme
    WebAPI._themes_fix = True
    print("themes_fix applied:", ", ".join(THEMES))
    return WebAPI
