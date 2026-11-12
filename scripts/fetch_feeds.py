#!/usr/bin/env python3
"""Pull free, no-key open-source feeds into data/feeds/latest.json.

Standard library only. Every source is optional: a failure is recorded in
"errors" and the run continues, so one dead feed never blocks the briefing.

Usage:  python scripts/fetch_feeds.py
"""
import json
import math
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HOME = (37.6138, -122.4869)          # Pacifica, CA 94044
UA = "MorningWatch/1.0 (personal briefing page)"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "feeds" / "latest.json"
TIMEOUT = 25


def get(url, accept="*/*"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def get_json(url):
    return json.loads(get(url, "application/geo+json, application/json"))


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(h)))


def strip(s, n=400):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


def rss(url, limit=15):
    """Parse RSS 2.0 or Atom into [{title, link, date, summary}]."""
    root = ET.fromstring(get(url, "application/rss+xml, application/atom+xml, application/xml"))
    out = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//a:entry", ns)
    for it in items[:limit]:
        def t(*tags):
            for tag in tags:
                el = it.find(tag)
                if el is None:
                    el = it.find("a:" + tag, ns)
                if el is not None:
                    return el
            return None
        title = t("title")
        link = t("link")
        href = (link.get("href") if link is not None and link.get("href") else (link.text if link is not None else "")) or ""
        date = t("pubDate", "updated", "published")
        desc = t("description", "summary", "content")
        entry = {
            "title": strip(title.text if title is not None else "", 200),
            "link": href.strip(),
            "date": (date.text or "").strip() if date is not None else "",
            "summary": strip(desc.text if desc is not None else "", 300),
        }
        # GeoRSS point (GDACS etc.)
        for el in it.iter():
            if el.tag.endswith("point") and el.text:
                try:
                    la, lo = map(float, el.text.split()[:2])
                    entry["lat"], entry["lon"] = la, lo
                except ValueError:
                    pass
            if el.tag.endswith("alertlevel") and el.text:
                entry["alertlevel"] = el.text
        out.append(entry)
    return out


# ---------------------------------------------------------------- sources

def quakes_local():
    d = get_json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson")
    out = []
    for f in d["features"]:
        lo, la = f["geometry"]["coordinates"][:2]
        dist = km(HOME, (la, lo))
        if dist <= 350:
            p = f["properties"]
            out.append({"mag": p["mag"], "place": p["place"], "km_from_home": dist, "lat": la, "lon": lo,
                        "time": datetime.fromtimestamp(p["time"] / 1000, timezone.utc).isoformat(),
                        "tsunami": p.get("tsunami"), "url": p["url"]})
    return sorted(out, key=lambda q: -q["mag"])[:15]


def quakes_world():
    d = get_json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson")
    out = []
    for f in d["features"]:
        p = f["properties"]
        if (p["mag"] or 0) >= 5.5:
            lo, la = f["geometry"]["coordinates"][:2]
            out.append({"mag": p["mag"], "place": p["place"], "lat": la, "lon": lo, "alert": p.get("alert"),
                        "time": datetime.fromtimestamp(p["time"] / 1000, timezone.utc).isoformat(),
                        "tsunami": p.get("tsunami"), "url": p["url"]})
    return sorted(out, key=lambda q: -q["mag"])[:20]


def nws_point_alerts():
    d = get_json(f"https://api.weather.gov/alerts/active?point={HOME[0]},{HOME[1]}")
    return [{k: f["properties"].get(k) for k in
             ("event", "severity", "urgency", "headline", "areaDesc", "onset", "ends", "instruction")}
            for f in d.get("features", [])]


def nws_ca_alerts():
    d = get_json("https://api.weather.gov/alerts/active?area=CA")
    out = []
    for f in d.get("features", []):
        p = f["properties"]
        if p.get("severity") in ("Extreme", "Severe"):
            out.append({k: p.get(k) for k in ("event", "severity", "headline", "areaDesc", "onset", "ends")})
    return out[:25]


def nws_forecast():
    pt = get_json(f"https://api.weather.gov/points/{HOME[0]},{HOME[1]}")
    fc = get_json(pt["properties"]["forecast"])
    return [{"name": p["name"], "forecast": p["detailedForecast"]} for p in fc["properties"]["periods"][:6]]


def air_quality():
    d = get_json("https://air-quality-api.open-meteo.com/v1/air-quality"
                 f"?latitude={HOME[0]}&longitude={HOME[1]}&current=us_aqi,pm2_5,pm10,ozone"
                 "&hourly=us_aqi&forecast_days=2&timezone=America%2FLos_Angeles")
    hourly = d.get("hourly", {})
    peak = max(zip(hourly.get("us_aqi", []), hourly.get("time", [])), default=None,
               key=lambda x: x[0] or 0)
    return {"current": d.get("current"), "peak_next_48h": {"us_aqi": peak[0], "time": peak[1]} if peak else None}


def marine_weather():
    d = get_json("https://marine-api.open-meteo.com/v1/marine"
                 f"?latitude={HOME[0]}&longitude={HOME[1] - 0.05}&daily=wave_height_max,wave_period_max"
                 "&forecast_days=3&timezone=America%2FLos_Angeles")
    return d.get("daily")


def tsunami():
    return rss("https://www.tsunami.gov/events/xml/PAAQAtom.xml", 5)


def calfire():
    d = get_json("https://www.fire.ca.gov/umbraco/api/IncidentApi/List?inactive=false")
    out = []
    for i in d:
        la, lo = i.get("Latitude"), i.get("Longitude")
        dist = km(HOME, (la, lo)) if la and lo else None
        out.append({"name": i.get("Name"), "county": i.get("County"), "acres": i.get("AcresBurned"),
                    "contained": i.get("PercentContained"), "lat": la, "lon": lo, "km_from_home": dist,
                    "updated": i.get("Updated"), "url": i.get("Url")})
    return sorted(out, key=lambda x: (x["km_from_home"] is None, x["km_from_home"] or 0))[:20]


def caltrans_d4_closures():
    """Caltrans District 4 (Bay Area) lane closure system, filtered to Pacifica-area routes."""
    d = get_json("https://cwwp2.dot.ca.gov/data/d4/lcs/lcsStatusD04.json")
    routes = {"1", "35", "92", "280", "82", "84"}
    out = []
    for rec in d.get("data", []):
        lcs = rec.get("lcs", {})
        loc = lcs.get("location", {}).get("begin", {})
        route = str(loc.get("beginRoute", "")).lstrip("SR-").lstrip("I-").lstrip("US-")
        county = loc.get("beginCounty", "")
        if county not in ("SM", "SF", "San Mateo", "San Francisco") or re.sub(r"\D", "", route) not in routes:
            continue
        cl = lcs.get("closure", {})
        out.append({"route": loc.get("beginRoute"), "near": loc.get("beginNearbyPlace"),
                    "type": cl.get("typeOfClosure"), "work": cl.get("typeOfWork"),
                    "lanes": cl.get("lanesClosed"),
                    "start": cl.get("closureTimestamp", {}).get("closureStartDate"),
                    "end": cl.get("closureTimestamp", {}).get("closureEndDate")})
    seen, uniq = set(), []
    for c in out:
        key = (c["route"], c["near"], c["type"], c["start"])
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq[:25]


def space_weather():
    d = get_json("https://services.swpc.noaa.gov/products/noaa-scales.json")
    now = d.get("0", {})
    return {"radio_blackout_R": now.get("R", {}).get("Scale"), "solar_radiation_S": now.get("S", {}).get("Scale"),
            "geomagnetic_G": now.get("G", {}).get("Scale")}


def cisa_kev():
    """Vulnerabilities CISA added to its Known Exploited list in the last 7 days."""
    d = get_json("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
    cutoff = datetime.now(timezone.utc).date().toordinal() - 7
    out = [{"cve": v["cveID"], "vendor": v["vendorProject"], "product": v["product"], "name": v["vulnerabilityName"],
            "added": v["dateAdded"], "ransomware": v.get("knownRansomwareCampaignUse")}
           for v in d.get("vulnerabilities", [])
           if datetime.fromisoformat(v["dateAdded"]).date().toordinal() >= cutoff]
    return out[:25]


RSS_FEEDS = {
    # global disasters with coordinates and alert levels
    "gdacs": "https://www.gdacs.org/xml/rss.xml",
    # US travel advisories (level changes are a good world-tension signal)
    "state_dept_advisories": "https://travel.state.gov/_res/rss/TAsTWs.xml",
    # cyber
    # health
    "fda_food_recalls": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/food-safety-recalls/rss.xml",
    # world news
    "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "bbc_asia": "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
    "bbc_us": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    "guardian_world": "https://www.theguardian.com/world/rss",
    "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "npr_world": "https://feeds.npr.org/1004/rss.xml",
    "defense_one": "https://www.defenseone.com/rss/all/",
    # California / Bay Area
    "kqed_news": "https://ww2.kqed.org/news/feed/",
    "calmatters": "https://calmatters.org/feed/",
    "sfgate_bayarea": "https://www.sfgate.com/bayarea/feed/bayarea-news-rss-feed-435.php",
}

SOURCES = {
    "quakes_local": quakes_local,
    "quakes_world": quakes_world,
    "nws_alerts_pacifica": nws_point_alerts,
    "nws_alerts_california_severe": nws_ca_alerts,
    "nws_forecast_pacifica": nws_forecast,
    "air_quality_pacifica": air_quality,
    "surf_pacifica": marine_weather,
    "tsunami_ntwc": tsunami,
    "calfire_active": calfire,
    "caltrans_closures_pacifica_area": caltrans_d4_closures,
    "space_weather": space_weather,
    "cisa_known_exploited_recent": cisa_kev,
}
for _k, _u in RSS_FEEDS.items():
    SOURCES[_k] = (lambda u: (lambda: rss(u)))(_u)


def run(item):
    name, fn = item
    t0 = time.time()
    try:
        return name, fn(), None, round(time.time() - t0, 1)
    except Exception as e:  # noqa: BLE001
        return name, None, f"{type(e).__name__}: {str(e)[:160]}", round(time.time() - t0, 1)


def main():
    result = {"fetched_at": datetime.now(timezone.utc).isoformat(), "home": {"zip": "94044", "lat": HOME[0], "lon": HOME[1]},
              "data": {}, "errors": {}}
    with ThreadPoolExecutor(max_workers=10) as ex:
        for name, data, err, secs in ex.map(run, SOURCES.items()):
            if err:
                result["errors"][name] = err
            else:
                result["data"][name] = data
            print(f"{'FAIL' if err else 'ok  '} {name:34s} {secs:5.1f}s {err or ''}", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB); {len(result['data'])} ok, {len(result['errors'])} failed",
          file=sys.stderr)


if __name__ == "__main__":
    main()
