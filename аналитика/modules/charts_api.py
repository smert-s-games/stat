"""Charts API: history series from DB + project parse snapshots."""
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


def apply_charts_api(WebAPI):
    if getattr(WebAPI, "_charts_api", False):
        return WebAPI

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

    def get_chart_channels(self):
        p = self._proj() or {}
        seen = {}
        for r in p.get("last_stats") or []:
            if isinstance(r, dict) and r.get("url") and not r.get("error"):
                seen[r["url"]] = r.get("channel_name") or r["url"]
        for snap in p.get("parse_history") or []:
            for c in snap.get("channels") or []:
                u = c.get("url") or ""
                if u and u not in seen:
                    seen[u] = c.get("name") or u
        try:
            rows = self.database.get_all_channels_history(90)
            for rec in rows or []:
                u = rec[1] if len(rec) > 1 else ""
                n = rec[2] if len(rec) > 2 else u
                if u and u not in seen:
                    seen[u] = n or u
        except Exception:
            pass
        items = [{"url": u, "name": n} for u, n in sorted(seen.items(), key=lambda x: (x[1] or "").lower())]
        return {"channels": items}

    def get_charts_data(self, days=30, metric="views", mode="total", channel_url=""):
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

        labels = []
        series = []
        source = "none"
        delta = 0
        growth_pct = None

        try:
            if mode == "channel" and channel_url:
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
                    series = [{"name": "Все каналы", "data": data}]
                    source = "db_total" if labels else "none"
        except Exception as e:
            print("charts db:", e)

        if source == "none" or not labels:
            p = self._proj() or {}
            hist = list(p.get("parse_history") or [])
            cutoff = datetime.now() - timedelta(days=days)
            points = []
            for snap in hist:
                ts = snap.get("ts") or ""
                try:
                    dt = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if dt < cutoff:
                    continue
                points.append(snap)
            if mode == "channel" and channel_url:
                labels = []
                data = []
                name = channel_url
                for snap in points:
                    labels.append(_day_key(snap.get("ts") or "") + " " + (snap.get("ts") or "")[11:16])
                    found = 0
                    for c in snap.get("channels") or []:
                        if (c.get("url") or "").rstrip("/") == channel_url.rstrip("/"):
                            if metric == "views":
                                found = int(c.get("views") or 0)
                            elif metric == "videos":
                                found = int(c.get("videos") or 0)
                            else:
                                found = int(c.get("subscribers") or 0)
                            name = c.get("name") or name
                            break
                    data.append(found)
                series = [{"name": name, "data": data}]
                source = "snapshot_channel" if labels else "none"
            else:
                labels = []
                data = []
                for snap in points:
                    labels.append(_day_key(snap.get("ts") or "") + " " + (snap.get("ts") or "")[11:16])
                    if metric == "views":
                        data.append(int(snap.get("views") or 0))
                    elif metric == "videos":
                        data.append(int(snap.get("videos") or 0))
                    else:
                        data.append(int(snap.get("subscribers") or 0))
                series = [{"name": "Все каналы", "data": data}]
                source = "snapshot_total" if labels else "none"

        if series and series[0]["data"]:
            d0 = series[0]["data"][0]
            d1 = series[0]["data"][-1]
            delta = d1 - d0
            if d0:
                growth_pct = round((delta / d0) * 100, 1)

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
        }

    WebAPI._append_parse_snapshot = _append_parse_snapshot
    WebAPI.get_charts_data = get_charts_data
    WebAPI.get_chart_channels = get_chart_channels
    WebAPI._charts_api = True
    print("charts_api applied")
    return WebAPI
