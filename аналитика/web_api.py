"""Thin entry: re-export WebAPI and BASE for web_server."""
from modules.web_backend import WebAPI, BASE, sort_stats, sort_accounts  # noqa: F401

try:
    from modules.runtime_patches import apply_webapi_patches
    apply_webapi_patches(WebAPI)
except Exception as e:
    print("runtime_patches:", e)

try:
    from modules.import_fix import apply_import_fix
    apply_import_fix(WebAPI)
except Exception as e:
    print("import_fix:", e)

try:
    from modules.channels_fix import apply_channels_fix
    apply_channels_fix(WebAPI)
except Exception as e:
    print("channels_fix:", e)

try:
    from modules.stats_parser import StatsParser
    from modules.parser_fix import apply_parser_fix
    apply_parser_fix(StatsParser)
except Exception as e:
    print("parser_fix:", e)

try:
    from modules.email_stats_fix import apply_email_stats_fix
    apply_email_stats_fix(WebAPI)
except Exception as e:
    print("email_stats_fix:", e)

try:
    from modules.display_fix import apply_display_fix
    apply_display_fix(WebAPI)
except Exception as e:
    print("display_fix:", e)

try:
    from modules.charts_api import apply_charts_api
    apply_charts_api(WebAPI)
except Exception as e:
    print("charts_api:", e)

try:
    from modules.themes_fix import apply_themes_fix
    apply_themes_fix(WebAPI)
except Exception as e:
    print("themes_fix:", e)

try:
    from modules.expenses_proxy_fix import apply_expenses_proxy_fix
    apply_expenses_proxy_fix(WebAPI)
except Exception as e:
    print("expenses_proxy_fix:", e)

__all__ = ["WebAPI", "BASE", "sort_stats", "sort_accounts"]
