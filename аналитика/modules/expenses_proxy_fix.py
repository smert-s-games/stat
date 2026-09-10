"""Make expenses accept object payload; ensure proxy CRUD is present."""
from __future__ import annotations
import uuid


def apply_expenses_proxy_fix(WebAPI):
    _orig_add = getattr(WebAPI, "add_expense", None)

    def add_expense(self, amount=None, description="", category="", date=""):
        # Frontend may send a single dict as first arg
        if isinstance(amount, dict):
            data = amount
            amount = data.get("amount")
            description = data.get("description", description)
            category = data.get("category", category)
            date = data.get("date", date)
        if _orig_add:
            return _orig_add(self, amount, description or "", category or "", date or "")
        return self.store.add_expense(amount, description or "", category or "", date or "")

    # Ensure proxy methods exist even if runtime_patches failed partially
    if not getattr(WebAPI, "get_proxies", None):
        def get_proxies(self):
            p = self._proj() or {}
            return {"proxies": list(p.get("proxies") or [])}
        WebAPI.get_proxies = get_proxies

    if not getattr(WebAPI, "add_proxy", None):
        def add_proxy(self, data=None, **kwargs):
            if data is None:
                data = kwargs
            if not isinstance(data, dict):
                data = {}
            proxies = list((self._proj() or {}).get("proxies") or [])
            item = {
                "id": str(uuid.uuid4())[:8],
                "name": str(data.get("name") or ("Proxy %d" % (len(proxies) + 1))).strip(),
                "host": str(data.get("host") or "").strip(),
                "port": str(data.get("port") or "").strip(),
                "type": str(data.get("type") or "http").strip(),
                "login": str(data.get("login") or "").strip(),
                "password": str(data.get("password") or "").strip(),
                "purchase_date": str(data.get("purchase_date") or "").strip(),
                "expiry_date": str(data.get("expiry_date") or "").strip(),
                "notes": str(data.get("notes") or "").strip(),
            }
            proxies.append(item)
            self.store.update_active(proxies=proxies)
            return {"ok": True, "proxy": item, "proxies": proxies}
        WebAPI.add_proxy = add_proxy

    if not getattr(WebAPI, "delete_proxy", None):
        def delete_proxy(self, proxy_id: str):
            proxies = [p for p in ((self._proj() or {}).get("proxies") or []) if p.get("id") != proxy_id]
            self.store.update_active(proxies=proxies)
            return {"ok": True, "proxies": proxies}
        WebAPI.delete_proxy = delete_proxy

    WebAPI.add_expense = add_expense
    WebAPI._expenses_proxy_fix = True
    print("expenses_proxy_fix applied")
    return WebAPI
