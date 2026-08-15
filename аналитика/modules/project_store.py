"""
Хранилище проектов и сессий.
Каждый проект: каналы (последний парсинг), папки аккаунтов, скрипты, расходы, прокси/сервер.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
PROJECTS_INDEX = DATA_DIR / "projects.json"


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _empty_project(name: str, pid: str | None = None) -> dict:
    return {
        "id": pid or str(uuid.uuid4())[:8],
        "name": name,
        "created_at": _now(),
        "links_file": "links.txt",
        "accounts_folders": [],
        "video_scripts": [],
        "proxy": {"purchase_date": "", "expiry_date": ""},
        "proxies": [],
        "server": {"purchase_date": "", "expiry_date": ""},
        "last_stats": [],
        "expenses": [],
        "stats_sort": "default",
        "accounts_sort": "materials_desc",
        "theme": "light",
    }


class ProjectStore:
    def __init__(self):
        _ensure_dir()
        self._index = self._load_index()
        self._migrate_from_config_if_needed()

    def _load_index(self) -> dict:
        if PROJECTS_INDEX.exists():
            try:
                with open(PROJECTS_INDEX, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "projects" in data and data["projects"]:
                    return data
            except Exception:
                pass
        p = _empty_project("Основной")
        data = {"active_id": p["id"], "projects": [p]}
        self._write_index(data)
        return data

    def _write_index(self, data: dict | None = None):
        _ensure_dir()
        data = data if data is not None else self._index
        with open(PROJECTS_INDEX, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _migrate_from_config_if_needed(self):
        cfg_path = BASE / "config.json"
        if not cfg_path.exists():
            return
        flag = DATA_DIR / ".migrated_config"
        if flag.exists():
            return
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            return
        active = self.get_active()
        if not active:
            return
        if active.get("last_stats") or active.get("expenses"):
            flag.write_text("1", encoding="utf-8")
            return
        active["links_file"] = cfg.get("links_file", active["links_file"])
        active["accounts_folders"] = cfg.get("accounts_folders") or []
        active["video_scripts"] = cfg.get("video_scripts") or []
        active["proxy"] = cfg.get("proxy") or active["proxy"]
        active["server"] = cfg.get("server") or active["server"]
        self._save_project(active)
        try:
            flag.write_text("1", encoding="utf-8")
        except Exception:
            pass

    def list_projects(self) -> list[dict]:
        return [
            {"id": p["id"], "name": p["name"], "created_at": p.get("created_at", "")}
            for p in self._index.get("projects", [])
        ]

    def get_active_id(self) -> str:
        return self._index.get("active_id") or (
            self._index["projects"][0]["id"] if self._index.get("projects") else ""
        )

    def get_active(self) -> dict | None:
        return self.get_project(self.get_active_id())

    def get_project(self, pid: str) -> dict | None:
        for p in self._index.get("projects", []):
            if p["id"] == pid:
                if "proxies" not in p:
                    p["proxies"] = []
                single = p.get("proxy") or {}
                if single.get("expiry_date") or single.get("purchase_date"):
                    if not p["proxies"]:
                        p["proxies"] = [{
                            "id": "legacy",
                            "name": "Основной",
                            "host": "",
                            "port": "",
                            "type": "",
                            "login": "",
                            "password": "",
                            "purchase_date": single.get("purchase_date", ""),
                            "expiry_date": single.get("expiry_date", ""),
                            "notes": "",
                        }]
                return p
        return None

    def _save_project(self, project: dict):
        projects = self._index.get("projects", [])
        for i, p in enumerate(projects):
            if p["id"] == project["id"]:
                projects[i] = project
                break
        else:
            projects.append(project)
        self._index["projects"] = projects
        self._write_index()

    def set_active(self, pid: str) -> dict:
        if not self.get_project(pid):
            return {"error": "проект не найден"}
        self._index["active_id"] = pid
        self._write_index()
        return {"ok": True, "id": pid}

    def create_project(self, name: str) -> dict:
        name = (name or "").strip() or "Новый проект"
        p = _empty_project(name)
        self._index.setdefault("projects", []).append(p)
        self._index["active_id"] = p["id"]
        self._write_index()
        return p

    def rename_project(self, pid: str, name: str) -> dict:
        p = self.get_project(pid)
        if not p:
            return {"error": "проект не найден"}
        p["name"] = (name or "").strip() or p["name"]
        self._save_project(p)
        return {"ok": True, "name": p["name"]}

    def delete_project(self, pid: str) -> dict:
        projects = self._index.get("projects", [])
        if len(projects) <= 1:
            return {"error": "нельзя удалить последний проект"}
        projects = [p for p in projects if p["id"] != pid]
        self._index["projects"] = projects
        if self._index.get("active_id") == pid:
            self._index["active_id"] = projects[0]["id"]
        self._write_index()
        return {"ok": True}

    def update_active(self, **fields) -> dict:
        p = self.get_active()
        if not p:
            return {"error": "нет активного проекта"}
        for k, v in fields.items():
            if k == "id":
                continue
            p[k] = v
        self._save_project(p)
        return p

    def add_expense(self, amount, description: str, category: str = "", date: str = "") -> dict:
        p = self.get_active()
        if not p:
            return {"error": "нет проекта"}
        try:
            amount = float(str(amount).replace(",", ".").replace(" ", ""))
        except ValueError:
            return {"error": "некорректная сумма"}
        exp = {
            "id": str(uuid.uuid4())[:8],
            "amount": amount,
            "description": (description or "").strip(),
            "category": (category or "").strip(),
            "date": date or datetime.now().strftime("%d.%m.%Y"),
            "created_at": _now(),
        }
        expenses = p.get("expenses") or []
        expenses.append(exp)
        p["expenses"] = expenses
        self._save_project(p)
        return exp

    def delete_expense(self, exp_id: str) -> dict:
        p = self.get_active()
        if not p:
            return {"error": "нет проекта"}
        expenses = [e for e in (p.get("expenses") or []) if e.get("id") != exp_id]
        p["expenses"] = expenses
        self._save_project(p)
        return {"ok": True}

    def expenses_summary(self) -> dict:
        p = self.get_active()
        expenses = (p or {}).get("expenses") or []
        total = sum(float(e.get("amount") or 0) for e in expenses)
        by_cat: dict[str, float] = {}
        for e in expenses:
            cat = e.get("category") or "Без категории"
            by_cat[cat] = by_cat.get(cat, 0) + float(e.get("amount") or 0)
        return {
            "total": total,
            "count": len(expenses),
            "by_category": by_cat,
            "items": expenses,
        }
