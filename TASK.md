# Morning Watch: daily briefing task

You are writing today's **Morning Watch**. It's a calm, plain-spoken security briefing for one household in **Pacifica, CA 94044**. The reader isn't in the intelligence business. Write it the way a retired intelligence analyst checks the world each morning out of habit: "Is the world okay, and is there anything I need to do?"

Run this every day at about 4 AM Pacific. The page (`index.html`) only reads `data/brief.json`. Your job is to write that file correctly, then publish it.

## Steps

1. `python scripts/fetch_feeds.py`. This pulls free official feeds into `data/feeds/latest.json` (USGS quakes, NWS alerts and forecast, tsunami center, air quality, surf, CAL FIRE, Caltrans District 4 closures, space weather, CISA exploited vulnerabilities, **FEMA IPAWS public emergency alerts covering Pacifica**, market gauges (S&P 500, VIX, oil, gold, 10-yr yield, dollar), GDACS disasters, State Dept advisories, FDA recalls, and world and California news RSS). Read all of it. A feed listed under `errors` just failed today. Cover that ground with a web search instead.
2. Read yesterday's `data/brief.json` so you can say what changed and set each item's `trend`.
3. Use web search for what the feeds can't give you. Keep it targeted, roughly 10–20 searches:
   - **Local, always check:** SMC Alert / San Mateo County OES notices; PG&E outages or PSPS (Public Safety Power Shutoff) for Pacifica; North Coast County Water District notices; Highway 1 status (Devil's Slide / Tom Lantos Tunnels, Pacifica to Half Moon Bay, Sharp Park), Sharp Park Rd and Hwy 35, Hwy 1 north to Daly City; Pacifica police and city news; coastal bluff and erosion news; cell or internet outages in the area.
   - **California:** fires, storms, atmospheric rivers, grid alerts (CAISO Flex Alert), major unrest, state emergency declarations.
   - **USA, the West, Asia, World:** the main security stories (active wars and ceasefires, terrorism, major cyber incidents, coups and political crises, nuclear and missile news, sea-lane disruptions, outbreaks), plus anything with a supply-chain effect (ports, fuel, food, medicine).
   - **Economy and energy:** read the `markets` feed. Mention markets only when they signal stress (S&P 500 moves of 2% or more in a day, VIX above 25, oil moves of 5% or more, a sharp rise in the dollar) or connect to a story. Check California gasoline prices and grid conditions when energy is in the news.
   - **Information:** large, well-documented disinformation or influence operations, from government attributions or major investigative outlets. Never pass along a rumour as a story. Report it only as "officials say X is a false claim spreading about Y."
   - **Coming up:** scheduled events in the next 7 days: forecast storms, summits, deadlines, votes, court rulings, planned outages or closures.
4. Write `data/brief.json` using the schema below.
5. `python scripts/finalize.py`. It validates the file, copies it to `data/archive/<date>.json` and updates `data/index.json`. If it prints `INVALID`, fix the file and run it again. **Never publish a briefing that fails validation.**
6. Commit and push to `main`: `git add data && git commit -m "Briefing <date>" && git push`. Don't change `index.html`, the scripts or this file during a daily run.

## Editorial rules

- **FEMA IPAWS alerts are top priority.** Any entry in `fema_ipaws_alerts_home` that is still in effect (check `expires`), and is an evacuation, shelter-in-place, tsunami, or civil or local emergency, must be an `ACTION` item under `alerts`, with `confidence: "confirmed"`. Quote its instruction, link https://www.fema.gov/openfema-data-page/ipaws-archived-alerts-v1 and the issuing agency, and lead the BLUF with it. Expired alerts from the last few days can go in `changes`.
- **Official sources first.** County, NWS, USGS, CAL FIRE, Caltrans and utility notices outrank news reports. Name the source on every item and link it.
- **Verify, don't amplify.** Leave out unconfirmed social-media claims. If something matters but isn't confirmed, say "unconfirmed" in the detail and tag it WATCH at most.
- **Every item gets a confidence:** `confirmed` (an official source or two or more independent reputable outlets), `likely` (one reputable report, or an official statement about intentions or plans), or `unconfirmed` (early or single-source reporting that matters anyway). Unconfirmed items are WATCH at most. Never mark a forecast or a threat "confirmed" unless the event itself has been confirmed: "Israel prepares to strike" can be confirmed as a report while the strike is only likely.
- **Every item gets a topic:** `conflict`, `terrorism`, `cyber`, `infrastructure`, `environment` (weather, quakes, fire, surf, air), `economy`, `energy`, `supply`, `health`, `political`, `information`, or `public-safety` (crime, accidents, unrest). Pick the one that fits best.
- **Every item gets a tag:**
  - `ACTION`: the reader should do something in the next 24–72 hours. Must include `action` (the specific step), plus `when` and `where`. Use it sparingly: most days should have zero to two. Example: "Charge phones and battery packs tonight; PG&E shutoff possible 6 PM Wed, Linda Mar."
  - `WATCH`: nothing to do yet, but it could become action. Add `action` saying what to do if it worsens.
  - `INFO`: worth knowing, nothing to do.
- **Translate hazards into household decisions.** Say who is affected, where, for how long, and what the protective step is. For outages, give scope and expected duration, not just "there's an outage."
- **Keep evacuation orders separate from ordinary traffic.** Mention Highway 1 and its alternates whenever verified conditions affect them.
- **Health:** only actionable local advisories, contamination notices, relevant recalls (food or medicine sold in California), and air quality. Not every national health headline.
- **Supplies:** only verified disruptions to fuel, groceries, prescriptions and similar. Mention broad economic or geopolitical news here only when it plausibly connects to availability.
- **Tone:** calm, factual, short. No hype, no adjectives like "shocking" or "terrifying," no politics beyond facts. When the world is quiet, say so plainly. "Nothing needs action today" is a good briefing.
- **Status lights:** `status.local` (Pacifica and the home front), `status.regional` (California and the US) and `status.world` each get a `level` (steady, strained, serious or critical) and a `note` of under 70 characters. `overall.level` is normally the most serious of the three, unless the local situation clearly dominates.
- **Coming up:** 0–8 entries, soonest first. Each has `when` (display text), `date` (YYYY-MM-DD), `level` (a ladder level key), `title`, optional `detail` and `sources`. Only include things actually scheduled or forecast. Don't speculate.
- **Length:** each `detail` is 1–3 sentences. Each ladder level has about 2–6 items, ACTION and WATCH first. Don't repeat the same event at two levels. Put it at the level closest to home that it actually affects.

## Severity, area and the map

Each item can carry a `severity`. Mapped items must have one, and it sets the dot colour:

| severity | meaning | colour |
|---|---|---|
| `critical` | active armed conflict, mass-casualty event, life-safety emergency | red |
| `elevated` | serious and could spread: escalation, major disaster response | orange |
| `watch` | tension or risk building | yellow |
| `hazard` | natural or environmental: quake, storm, surf, smoke, outbreak | blue |
| `low` | minor or resolving | green |

Add `lat` and `lon` (decimal degrees) for anything with a clear location so it appears on the map. `area` (1–5) sets the glow size: how large a region is affected **or could be**. 1 is a town, 2 a county or city, 3 a state or small country, 4 a large country or sub-region, 5 a multi-country or continental region.

## Supply-aware items (optional)

If how urgent an item is depends on how much food or water the household has on hand (port strike, grocery-distribution problem, boil-water notice, quake damage to water mains), add a `supply` override and `supply_dim`:

```json
"supply_dim": "food",
"supply": {"3d": "ACTION", "3w": "WATCH", "3m": "INFO", "1y": "INFO"}
```

The reader picks their level on their own device. The page then re-tags the item. `tag` stays the default for readers who haven't picked a level.

`readiness` gives one practical task for today: always a `default`, and optionally one per supply level (`3d`, `3w`, `3m`, `1y`). Tie it to the day's news when you can, for example "Storm Friday: check flashlight batteries." Otherwise rotate basics: medication refill dates, rotating stored water, testing the weather radio, updating the go-bag, checking the car's fuel level, refreshing the family contact plan, and so on.

## Schema (`data/brief.json`)

```json
{
  "schema": 1,
  "date": "2026-11-11",
  "generated_at": "2026-11-11T04:05:00-08:00",
  "overall": {
    "level": "steady | strained | serious | critical",
    "headline": "One line: the state of things this morning.",
    "bluf": "Bottom line up front: 2–3 sentences covering home and the world."
  },
  "status": {
    "local":    {"level": "steady", "note": "Under 70 characters."},
    "regional": {"level": "steady", "note": "..."},
    "world":    {"level": "strained", "note": "..."}
  },
  "changes": ["Short bullet on what changed since yesterday", "..."],
  "coming_up": [
    {"when": "Fri 6 PM – Sun 4 AM", "date": "2026-11-13", "level": "pacifica", "title": "High Surf Warning on the coast", "detail": "Optional one line.", "sources": [{"name": "NWS", "url": "https://..."}]}
  ],
  "home_front": [
    {"id": "alerts",    "status": "clear | watch | action", "summary": "One line.", "items": [ITEM, ...]},
    {"id": "utilities", "status": "...", "summary": "...", "items": []},
    {"id": "roads",     "status": "...", "summary": "...", "items": []},
    {"id": "health",    "status": "...", "summary": "...", "items": []},
    {"id": "supplies",  "status": "...", "summary": "...", "items": []}
  ],
  "readiness": {
    "default": {"task": "One concrete thing to do today.", "why": "One sentence."},
    "3d": {"task": "...", "why": "..."}
  },
  "ladder": [
    {"level": "pacifica",   "summary": "One line.", "items": [ITEM, ...]},
    {"level": "california", "summary": "...", "items": []},
    {"level": "usa",        "summary": "...", "items": []},
    {"level": "west",       "summary": "...", "items": []},
    {"level": "asia",       "summary": "...", "items": []},
    {"level": "world",      "summary": "...", "items": []}
  ],
  "sources_used": [{"name": "NWS San Francisco", "url": "https://..."}]
}
```

`ITEM`:

```json
{
  "id": "short-unique-kebab-id",
  "tag": "ACTION | WATCH | INFO",
  "severity": "critical | elevated | watch | hazard | low",
  "title": "Short headline",
  "detail": "1–3 sentences: what, who is affected, how long.",
  "action": "Specific step (required for ACTION; for WATCH: what to do if it worsens)",
  "when": "Thu 6 PM – Sat 4 AM",
  "where": "Pacifica coast",
  "trend": "new | rising | steady | easing",
  "confidence": "confirmed | likely | unconfirmed",
  "topic": "conflict | terrorism | cyber | infrastructure | environment | economy | energy | supply | health | political | information | public-safety",
  "lat": 37.61, "lon": -122.49, "area": 2,
  "sources": [{"name": "NWS", "url": "https://..."}]
}
```

`confidence`, `topic` and at least one linked source are required on every item; `finalize.py` rejects the file without them.

Home-front items describe local conditions. `pacifica` on the ladder is for local news and context that isn't a home-front service or hazard item (city decisions, crime trends, bluff erosion). Home-front items appear on the Pacifica map view automatically.

`west` means Western civilization outside the US: Canada, Europe, NATO, the UK, Australia/NZ, Israel, and Latin America where relevant. `asia` covers East, South, Southeast and Central Asia. `world` covers everything else: the Middle East beyond Israel, Africa, Russia's wider war, global markets, pandemics, the UN.
