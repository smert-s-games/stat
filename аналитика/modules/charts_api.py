"""Charts API: per-project history (parse snapshots + filtered DB)."""
from __future__ import annotations
import re
from collections import defaultdict
from datetime import datetime, timedelta


def _num(v):
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().lower().replace("\xa0", " ").replace(" ", "")
    mult = 1
    if "млрд" in s or s.endswith("b"):
        mult = 1_000_000_000
        s = re.sub(r"[млрdb]", "", s)
    elif "млн" in s or s.endswith("m"):
        mult = 1_000_000
        s = re.sub(r"[млнm]", "", s)
    elif "тыс" in s or s.endswith("k"):
        mult = 1000
        s = re.sub(r"[тысk.]", "", s)
    s = s.replace(",", ".")
    s = re.sub(r"[^0-9.]", "", s)
    try:
        return int(float(s) * mult) if s else 0
    except Exception:
        return 0


def _day_key(ts: str) -> str:
    ts = (ts or "").strip()
    if not ts:
        return datetime.now().strftime("%Y-%m-%d")
    return ts[:10]


def _norm_url(u: str) -> str:
    return (u or "").strip().rstrip("/").lower()


def apply_charts_api(WebAPI):
    if getattr(WebAPI, "_charts_api_v2", False):
        return WebAPI

    def _project_channel_urls(self, p=None) -> set:
        p = p if p is not None else (self._proj() or {})
        urls = set()
        for c in p.get("channels") or []:
            if isinstance(c, dict) and c.get("url"):
                urls.add(_norm_url(c["url"]))
        for r in p.get("last_stats") or []:
            if isinstance(r, dict) and r.get("url") and not r.get("error"):
                urls.add(_norm_url(r["url"]))
        for snap in p.get("parse_history") or []:
            for ch in snap.get("channels") or []:
                if ch.get("url"):
                    urls.add(_norm_url(ch["url"]))
        return urls

    def _append_parse_snapshot(self, results):
        try:
            p = self._proj() or {}
            hist = list(p.get("parse_history") or [])
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            channels = []
            tot_subs = tot_views = tot_vids = 0
            for r in results or []:
                if not isinstance(r, dict) or r.get("error"):
                    continue
                subs = _num(r.get("subscribers_num") or r.get("subscribers"))
                views = _num(r.get("total_views_num") or r.get("total_views"))
                vids = _num(r.get("videos_count_num") or r.get("videos_count"))
                tot_subs += subs
                tot_views += views
                tot_vids += vids
                channels.append({
                    "url": r.get("url") or "",
                    "name": r.get("channel_name") or "",
                    "subscribers": subs,
                    "views": views,
                    "videos": vids,
                })
            hist.append({
                "ts": ts,
                "project_id": p.get("id") or "",
                "project_name": p.get("name") or "",
                "subscribers": tot_subs,
                "views": tot_views,
                "videos": tot_vids,
                "channels_count": len(channels),
                "channels": channels,
            })
            hist = hist[-40:]
            self.store.update_active(parse_history=hist)
        except Exception as e:
            print("parse snapshot:", e)

    def _metric_from_snap_channel(c, metric):
        if metric == "views":
            return int(c.get("views") or 0)
        if metric == "videos":
            return int(c.get("videos") or 0)
        return int(c.get("subscribers") or 0)

    def _metric_from_snap(snap, metric):
        if metric == "views":
            return int(snap.get("views") or 0)
        if metric == "videos":
            return int(snap.get("videos") or 0)
        return int(snap.get("subscribers") or 0)

    def _history_from_snapshots(self, days, metric, mode, channel_url, projects):
        cutoff = datetime.now() - timedelta(days=days)
        points = []
        for p in projects:
            for snap in p.get("parse_history") or []:
                ts = snap.get("ts") or ""
                try:
                    dt = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if dt < cutoff:
                    continue
                points.append((dt, ts, p.get("name") or p.get("id") or "", snap))
        points.sort(key=lambda x: x[0])
        if not points:
            return [], [], "none"

        if mode == "channel" and channel_url:
            key = _norm_url(channel_url)
            labels, data, name = [], [], channel_url
            for _dt, ts, _pn, snap in points:
                labels.append(_day_key(ts) + " " + ts[11:16])
                found = 0
                for c in snap.get("channels") or []:
                    if _norm_url(c.get("url") or "") == key:
                        found = _metric_from_snap_channel(c, metric)
                        name = c.get("name") or name
                        break
                data.append(found)
            return labels, [{"name": name, "data": data}], "snapshot_channel"

        if mode == "top5":
            last_snap = points[-1][3]
            ranking = []
            for c in last_snap.get("channels") or []:
                ranking.append((_norm_url(c.get("url") or ""), c.get("name") or c.get("url") or "", _metric_from_snap_channel(c, metric)))
            ranking = sorted(ranking, key=lambda x: -x[2])[:5]
            labels = [_day_key(ts) + " " + ts[11:16] for _dt, ts, _pn, _s in points]
            series = []
            for url, name, _ in ranking:
                data = []
                for _dt, ts, _pn, snap in points:
                    val = 0
                    for c in snap.get("channels") or []:
                        if _norm_url(c.get("url") or "") == url:
                            val = _metric_from_snap_channel(c, metric)
                            break
                    data.append(val)
                series.append({"name": name, "data": data})
            return labels, series, "snapshot_top5" if series else "none"

        if len(projects) > 1:
            bucket = defaultdict(int)
            order = []
            for _dt, ts, _pn, snap in points:
                key = _day_key(ts) + " " + ts[11:16]
                if key not in bucket:
                    order.append(key)
                bucket[key] += _metric_from_snap(snap, metric)
            labels = order
            data = [bucket[k] for k in labels]
            return labels, [{"name": "Все проекты", "data": data}], "snapshot_all_projects"

        labels = [_day_key(ts) + " " + ts[11:16] for _dt, ts, _pn, _s in points]
        data = [_metric_from_snap(snap, metric) for _dt, ts, _pn, snap in points]
        pname = projects[0].get("name") or "Проект"
        return labels, [{"name": pname, "data": data}], "snapshot_project"

    def _history_from_db(self, days, metric, mode, channel_url, allow_urls: set):
        labels, series, source = [], [], "none"
        try:
            if mode == "channel" and channel_url:
                if allow_urls and _norm_url(channel_url) not in allow_urls:
                    return [], [], "none"
                rows = self.database.get_channel_history(channel_url, days) or []
                rows = list(reversed(rows))
                by_day = {}
                name = channel_url
                for rec in rows:
                    if len(rec) < 7:
                        continue
                    name = rec[2] or name
                    d = _day_key(str(rec[6]))
                    val = rec[4] if metric == "views" else (rec[3] if metric == "subscribers" else rec[5])
                    by_day[d] = int(val or 0)
                labels = sorted(by_day.keys())
                data = [by_day[d] for d in labels]
                series = [{"name": name or channel_url, "data": data}]
                source = "db_channel" if labels else "none"
            else:
                rows = self.database.get_all_channels_history(days) or []
                day_totals = defaultdict(lambda: defaultdict(int))
                day_channel = defaultdict(lambda: defaultdict(int))
                names = {}
                for rec in rows:
                    if len(rec) < 7:
                        continue
                    url, name = rec[1], rec[2] or rec[1]
                    nu = _norm_url(url)
                    if allow_urls and nu not in allow_urls:
                        continue
                    names[url] = name
                    d = _day_key(str(rec[6]))
                    val = rec[4] if metric == "views" else (rec[3] if metric == "subscribers" else rec[5])
                    val = int(val or 0)
                    day_totals[d][metric] += val
                    day_channel[d][url] = val
                labels = sorted(day_totals.keys())
                if mode == "top5" and labels:
                    last = labels[-1]
                    ranking = sorted(day_channel[last].items(), key=lambda x: -x[1])[:5]
                    for url, _ in ranking:
                        data = [day_channel[d].get(url, 0) for d in labels]
                        series.append({"name": names.get(url, url), "data": data})
                    source = "db_top5" if series else "none"
                else:
                    data = [day_totals[d].get(metric, 0) for d in labels]
                    series = [{"name": "Каналы проекта", "data": data}]
                    source = "db_project" if labels else "none"
        except Exception as e:
            print("charts db:", e)
        return labels, series, source

    def get_chart_channels(self):
        p = self._proj() or {}
        seen = {}
        for r in p.get("last_stats") or []:
            if isinstance(r, dict) and r.get("url") and not r.get("error"):
                seen[r["url"]] = r.get("channel_name") or r["url"]
        for c in p.get("channels") or []:
            if isinstance(c, dict) and c.get("url"):
                u = c["url"]
                if u not in seen:
                    seen[u] = c.get("name") or u
        for snap in p.get("parse_history") or []:
            for c in snap.get("channels") or []:
                u = c.get("url") or ""
                if u and u not in seen:
                    seen[u] = c.get("name") or u
        items = [{"url": u, "name": n} for u, n in sorted(seen.items(), key=lambda x: (x[1] or "").lower())]
        return {
            "channels": items,
            "project_id": p.get("id") or "",
            "project_name": p.get("name") or "",
        }

    def get_charts_data(self, days=30, metric="views", mode="total", channel_url="", project_id=""):
        try:
            days = int(days or 30)
        except Exception:
            days = 30
        days = max(1, min(days, 365))
        metric = (metric or "views").strip().lower()
        if metric not in ("views", "subscribers", "videos"):
            metric = "views"
        mode = (mode or "total").strip().lower()
        channel_url = (channel_url or "").strip()
        project_id = (project_id or "").strip()

        projects = []
        active = self._proj() or {}
        all_mode = project_id == "__all__"
        if project_id == "__all__":
            try:
                projects = list(self.store._index.get("projects") or [])
            except Exception:
                projects = [active] if active else []
            all_mode = True
        elif project_id and project_id != (active.get("id") or ""):
            try:
                p = self.store.get_project(project_id)
                projects = [p] if p else [active]
            except Exception:
                projects = [active]
        else:
            projects = [active] if active else []

        projects = [p for p in projects if isinstance(p, dict)]

        labels, series, source = _history_from_snapshots(self, days, metric, mode, channel_url, projects)

        if source == "none" or not labels:
            allow = set()
            for p in projects:
                allow |= self._project_channel_urls(p)
            labels, series, source = self._history_from_db(days, metric, mode, channel_url, allow)

        delta = 0
        growth_pct = None
        if series and series[0].get("data"):
            d0 = series[0]["data"][0]
            d1 = series[0]["data"][-1]
            delta = d1 - d0
            if d0:
                growth_pct = round((delta / d0) * 100, 1)

        pname = "Все проекты" if all_mode or len(projects) > 1 else (projects[0].get("name") if projects else "")
        return {
            "labels": labels,
            "series": series,
            "metric": metric,
            "mode": mode,
            "days": days,
            "source": source,
            "delta": delta,
            "growth_pct": growth_pct,
            "points": len(labels),
            "project_id": projects[0].get("id") if len(projects) == 1 else "__all__",
            "project_name": pname,
        }

    WebAPI._project_channel_urls = _project_channel_urls
    WebAPI._append_parse_snapshot = _append_parse_snapshot
    WebAPI._history_from_db = _history_from_db
    WebAPI.get_charts_data = get_charts_data
    WebAPI.get_chart_channels = get_chart_channels
    WebAPI._charts_api = True
    WebAPI._charts_api_v2 = True
    print("charts_api v2 applied (per-project)")
    return WebAPI
