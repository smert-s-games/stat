"""Thin entry: re-export WebAPI and BASE for web_server."""
from modules.web_backend import WebAPI, BASE, sort_stats, sort_accounts  # noqa: F401

try:
    from modules.runtime_patches import apply_webapi_patches
    apply_webapi_patches(WebAPI)
except Exception as e:
    print("runtime_patches:", e)

__all__ = ["WebAPI", "BASE", "sort_stats", "sort_accounts"]
