# Morning Watch

A calm daily security briefing, from Pacifica (94044) out to the world.

- `index.html` is the whole site. It reads `data/brief.json` and draws everything client-side.
- `TASK.md` is the instructions the daily 4 AM Claude scheduled task follows.
- `scripts/fetch_feeds.py` pulls free official feeds into `data/feeds/latest.json` (not committed).
- `scripts/finalize.py` validates `data/brief.json`, archives it to `data/archive/` and updates `data/index.json`.
- `tests/levels.html` previews all six map zoom levels at phone width.

Preview locally: `python -m http.server 8790` and open http://localhost:8790/.
