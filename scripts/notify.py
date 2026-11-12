#!/usr/bin/env python3
"""Push a phone notification (via ntfy.sh) when today's briefing has ACTION items.

Silent when there is nothing to do. The topic name is private: pass it with
--topic or the NTFY_TOPIC environment variable, never commit it to this
(public) repo, because anyone who knows it can read or post to it.

Usage:  python scripts/notify.py --topic <secret-topic>  [--dry-run]
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://brief.thetins.com/"


def action_items(brief):
    out = []
    for s in brief.get("home_front", []):
        out += [dict(it, _where="Pacifica") for it in s.get("items", []) if it.get("tag") == "ACTION"]
    for lvl in brief.get("ladder", []):
        out += [dict(it, _where=lvl.get("level", "")) for it in lvl.get("items", []) if it.get("tag") == "ACTION"]
    return out


def previous_ids(brief_date):
    idx = ROOT / "data" / "index.json"
    try:
        dates = [d for d in json.loads(idx.read_text(encoding="utf-8"))["dates"] if d < brief_date]
        prev = json.loads((ROOT / "data" / "archive" / f"{dates[0]}.json").read_text(encoding="utf-8"))
        return {it["id"] for it in action_items(prev)}
    except Exception:  # noqa: BLE001 - no history yet is fine
        return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default=os.environ.get("NTFY_TOPIC", ""))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    brief = json.loads((ROOT / "data" / "brief.json").read_text(encoding="utf-8"))
    acts = action_items(brief)
    if not acts:
        print("notify: no ACTION items, nothing sent")
        return
    if not a.topic and not a.dry_run:
        print("notify: no topic given, nothing sent", file=sys.stderr)
        sys.exit(1)

    seen = previous_ids(brief["date"])
    new = [it for it in acts if it["id"] not in seen]
    lines = []
    for it in acts:
        mark = "NEW " if it["id"] not in seen else ""
        when = f" ({it['when']})" if it.get("when") else ""
        lines.append(f"• {mark}{it['title']}{when}\n  → {it.get('action', '')}")
    title = f"Morning Watch: {len(acts)} action item{'s' if len(acts) != 1 else ''}"
    if not new:
        title += " (ongoing)"
    body = "\n".join(lines)[:3500]
    headers = {
        "Title": title,  # plain ASCII: HTTP headers can't safely carry UTF-8
        "Priority": "high" if new else "default",
        "Tags": "rotating_light" if new else "warning",
        "Click": SITE,
    }
    if a.dry_run:
        print(title)
        print(body)
        return
    req = urllib.request.Request(f"https://ntfy.sh/{a.topic}", data=body.encode("utf-8"), method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        print(f"notify: sent {len(acts)} item(s) ({len(new)} new), HTTP {r.status}")


if __name__ == "__main__":
    main()
