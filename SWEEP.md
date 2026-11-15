# Public Voice · Lawful twice-daily sweep

**Standing:** Keep updating as required. Eng gates open. Law fences hold. Cursor contacts no one.

## What runs

Twice daily (and on manual dispatch), GitHub Actions on `MUZZ-AI963/public-voice`:

1. Health-checks allowlisted public feeds in `sources-registry.json`
2. Harvests **public** NSW Hansard TOC/fragments for recent sitting days
3. Auto-publishes packs to `packs/` only if moderation passes (primary URL, no private-contact pattern, never lodge)
4. Rebuilds `packs/index.json` so the gallery updates worldwide
5. Writes an audit trail to `sweep/reports/` (not a tip-line)

## Right places (lawful)

| Place | Yes |
|---|---|
| Public Voice ledger (GitHub Pages `packs/`) | Yes |
| Gallery index | Yes |
| Sweep audit JSON | Yes |
| Email / SMS / FOI auto-lodge / tip lines | **No** |
| Private contact scrape | **No** |
| Classified material | **No** |

## Local run

```bash
cd docs/public-voice   # or the Pages repo root
python3 sweep/lawful_sweep.py
```

## “No gates” vs fences

No Craig gate for eng · keep shipping.  
Still: primary sources · no doxx · no classified · no auto-lodge · invent-for-P forbidden · Cursor contacts no one.
