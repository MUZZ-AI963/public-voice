# Public Voice · Gate check · 15 Nov 2026

## Your screenshot (NSW `/api/hansard`)

**Not a Public Voice gate.**  
`https://api.parliament.nsw.gov.au/api/hansard` is **not** a working endpoint. Cloudflare shows **502 Bad gateway** / host error on that bare path.

| URL | Result | Use? |
|---|---|---|
| `/api/hansard` | 404 or Cloudflare 502 | No — do not open |
| `/api/hansard/search/bydate?date=YYYY-MM-DD` | 200 | Yes — sweep uses this |
| `/api/hansard/search/year/2026` | 200 | Yes |

Working example:  
https://api.parliament.nsw.gov.au/api/hansard/search/bydate?date=2026-11-12

## Full gate pass (probed from eng machine)

| Asset | Status | Notes |
|---|---|---|
| Public Voice live site | **OPEN** | https://muzz-ai963.github.io/public-voice/ |
| Gallery / packs index | **OPEN** | Auto Hansard packs present |
| Twice-daily Actions sweep | **OPEN** | Last run success |
| NSW Hansard search APIs | **OPEN** | Bare root gated/broken |
| UK Parliament API | **OPEN** | |
| UK Historic Hansard | **OPEN** | |
| TheyWorkForYou docs | **OPEN** | |
| EuroParl Open Data | **OPEN** | |
| FOIA.gov | **OPEN** | |
| Tor / Tails download | **OPEN** | |
| OAIC / Ombudsman HTML | **WAF 403 to bots** | Pathway still for humans in browser |
| NSW Hansard docs HTML | **WAF 403 to bots** | API search paths still work |

## Eng fences (unchanged — not Craig gates)

Primary sources · no doxx · no classified · no auto-lodge · invent-for-P forbidden · Cursor contacts no one.

## Fix applied

Registry + sweep now probe real endpoints (`probe_url`), not bare `/api/hansard`.
