# Public Voice · Gate check · 15 Nov 2026

## NSW Cloudflare 502 (your screenshots)

**Not a Public Voice gate.** It is **api.parliament.nsw.gov.au host error** behind Cloudflare (Sydney). Browser + Cloudflare working; **origin failing** for some paths/clients (VPN/edge).

| URL | Notes |
|---|---|
| `/api/hansard` | Never a real endpoint — often 404/502 |
| `/api/hansard/search/bydate?date=…` | Real endpoint; may still 502 when NSW origin flaps |
| Eng probe (same bydate URL) | Often still **200** while a browser/VPN path shows 502 |

**What we do:** sweep retries 502/503/504; if NSW returns nothing, fall back to **European Parliament Open Data** (public). Public Voice site stays up either way.

Try again in a few minutes, or open the ledger (does not need NSW live in your tab):  
https://muzz-ai963.github.io/public-voice/gallery.html

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
