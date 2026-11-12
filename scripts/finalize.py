#!/usr/bin/env python3
"""Validate data/brief.json, then archive it and update data/index.json.

Exits non-zero (and changes nothing) if the briefing is malformed, so a bad
run never replaces a good page.

Usage:  python scripts/finalize.py
"""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KEEP_DAYS = 120

TAGS = {"ACTION", "WATCH", "INFO"}
SEVS = {"critical", "elevated", "watch", "hazard", "low"}
TRENDS = {"new", "rising", "steady", "easing"}
OVERALL = {"steady", "strained", "serious", "critical"}
HF_IDS = ["alerts", "utilities", "roads", "health", "supplies"]
HF_STATUS = {"clear", "watch", "action"}
LEVELS = ["pacifica", "california", "usa", "west", "asia", "world"]
SUPPLY_KEYS = {"3d", "3w", "3m", "1y"}
CONFIDENCE = {"confirmed", "likely", "unconfirmed"}
TOPICS = {"conflict", "terrorism", "cyber", "infrastructure", "environment", "economy", "energy",
          "supply", "health", "political", "information", "public-safety"}
STATUS_KEYS = ["local", "regional", "world"]

errors = []


def err(path, msg):
    errors.append(f"{path}: {msg}")


def check_sources(srcs, path):
    if not isinstance(srcs, list):
        return err(path, "sources must be a list")
    for i, s in enumerate(srcs):
        if not isinstance(s, dict) or not s.get("name"):
            err(f"{path}[{i}]", "source needs a name")
        elif s.get("url") and not str(s["url"]).startswith(("http://", "https://")):
            err(f"{path}[{i}]", "url must be http(s)")


def check_item(it, path, ids):
    if not isinstance(it, dict):
        return err(path, "item must be an object")
    for k in ("id", "tag", "title"):
        if not it.get(k):
            err(path, f"missing {k}")
    if it.get("id") in ids:
        err(path, f"duplicate id {it.get('id')}")
    ids.add(it.get("id"))
    if it.get("tag") not in TAGS:
        err(path, f"tag must be one of {sorted(TAGS)}")
    if it.get("confidence") not in CONFIDENCE:
        err(path, f"confidence must be one of {sorted(CONFIDENCE)}")
    if it.get("topic") not in TOPICS:
        err(path, f"topic must be one of {sorted(TOPICS)}")
    if not it.get("sources"):
        err(path, "needs at least one source with a link")
    elif not any(str(x.get("url", "")).startswith(("http://", "https://")) for x in it["sources"] if isinstance(x, dict)):
        err(path, "at least one source needs a url")
    if it.get("tag") == "ACTION" and not it.get("action"):
        err(path, "ACTION items need an 'action' (what to do)")
    if "severity" in it and it["severity"] not in SEVS:
        err(path, f"severity must be one of {sorted(SEVS)}")
    if "trend" in it and it["trend"] not in TRENDS:
        err(path, f"trend must be one of {sorted(TRENDS)}")
    has_lat, has_lon = "lat" in it, "lon" in it
    if has_lat != has_lon:
        err(path, "lat and lon go together")
    if has_lat:
        if not isinstance(it["lat"], (int, float)) or not -90 <= it["lat"] <= 90:
            err(path, "lat out of range")
        if not isinstance(it["lon"], (int, float)) or not -180 <= it["lon"] <= 180:
            err(path, "lon out of range")
        if "severity" not in it:
            err(path, "mapped items (lat/lon) need a severity")
    if "area" in it and (not isinstance(it["area"], int) or not 1 <= it["area"] <= 5):
        err(path, "area must be an integer 1-5")
    if "supply" in it:
        sup = it["supply"]
        if not isinstance(sup, dict) or not set(sup) <= SUPPLY_KEYS or not set(sup.values()) <= TAGS:
            err(path, "supply must map 3d/3w/3m/1y to ACTION/WATCH/INFO")
    if "supply_dim" in it and it["supply_dim"] not in ("food", "water"):
        err(path, "supply_dim must be food or water")
    check_sources(it.get("sources", []), path + ".sources")


def validate(b):
    if b.get("schema") != 1:
        err("schema", "must be 1")
    try:
        date.fromisoformat(b.get("date", ""))
    except ValueError:
        err("date", "must be YYYY-MM-DD")
    try:
        datetime.fromisoformat(b.get("generated_at", ""))
    except ValueError:
        err("generated_at", "must be an ISO timestamp with offset")
    ov = b.get("overall", {})
    if ov.get("level") not in OVERALL:
        err("overall.level", f"must be one of {sorted(OVERALL)}")
    for k in ("headline", "bluf"):
        if not ov.get(k):
            err(f"overall.{k}", "required")
    st = b.get("status", {})
    for k in STATUS_KEYS:
        v = st.get(k) if isinstance(st, dict) else None
        if not isinstance(v, dict) or v.get("level") not in OVERALL or not v.get("note"):
            err(f"status.{k}", f"needs {{level: one of {sorted(OVERALL)}, note}}")
    cu = b.get("coming_up", [])
    if not isinstance(cu, list):
        err("coming_up", "must be a list")
    else:
        if len(cu) > 10:
            err("coming_up", "keep it to 10 or fewer")
        for i, c in enumerate(cu):
            path = f"coming_up[{i}]"
            if not isinstance(c, dict) or not c.get("title") or not c.get("when"):
                err(path, "needs when and title")
                continue
            if "date" in c:
                try:
                    date.fromisoformat(c["date"])
                except (TypeError, ValueError):
                    err(path + ".date", "must be YYYY-MM-DD")
            if c.get("level") not in LEVELS:
                err(path + ".level", f"must be one of {LEVELS}")
            check_sources(c.get("sources", []), path + ".sources")
    ids = set()
    hf = b.get("home_front", [])
    got = [s.get("id") for s in hf]
    if got != HF_IDS:
        err("home_front", f"must list sections in this order: {HF_IDS} (got {got})")
    for i, s in enumerate(hf):
        if s.get("status") not in HF_STATUS:
            err(f"home_front[{i}].status", f"must be one of {sorted(HF_STATUS)}")
        if not s.get("summary"):
            err(f"home_front[{i}].summary", "required")
        for j, it in enumerate(s.get("items", [])):
            check_item(it, f"home_front[{i}].items[{j}]", ids)
    lad = b.get("ladder", [])
    got = [l.get("level") for l in lad]
    if got != LEVELS:
        err("ladder", f"must list levels in this order: {LEVELS} (got {got})")
    for i, l in enumerate(lad):
        if not l.get("summary"):
            err(f"ladder[{i}].summary", "required")
        for j, it in enumerate(l.get("items", [])):
            check_item(it, f"ladder[{i}].items[{j}]", ids)
    r = b.get("readiness", {})
    if not isinstance(r, dict) or "default" not in r:
        err("readiness", "needs at least a 'default' task")
    for k, v in (r.items() if isinstance(r, dict) else []):
        if k not in SUPPLY_KEYS | {"default"}:
            err(f"readiness.{k}", "unknown key")
        if not isinstance(v, dict) or not v.get("task"):
            err(f"readiness.{k}", "must be {task, why}")
    if not isinstance(b.get("changes", []), list):
        err("changes", "must be a list of strings")
    check_sources(b.get("sources_used", []), "sources_used")


def main():
    path = DATA / "brief.json"
    try:
        b = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"INVALID: cannot parse {path}: {e}")
        sys.exit(1)
    validate(b)
    if errors:
        print("INVALID briefing:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    arch = DATA / "archive"
    arch.mkdir(exist_ok=True)
    (arch / f"{b['date']}.json").write_text(json.dumps(b, indent=1, ensure_ascii=False), encoding="utf-8")
    cutoff = date.fromisoformat(b["date"]) - timedelta(days=KEEP_DAYS)
    for f in arch.glob("*.json"):
        try:
            if date.fromisoformat(f.stem) < cutoff:
                f.unlink()
        except ValueError:
            pass
    dates = sorted((f.stem for f in arch.glob("*.json")), reverse=True)
    (DATA / "index.json").write_text(json.dumps({"dates": dates}, indent=1), encoding="utf-8")
    n = sum(len(s.get("items", [])) for s in b["home_front"]) + sum(len(l.get("items", [])) for l in b["ladder"])
    print(f"OK: {b['date']} — {n} items, overall {b['overall']['level']}; archive has {len(dates)} days")


if __name__ == "__main__":
    main()
