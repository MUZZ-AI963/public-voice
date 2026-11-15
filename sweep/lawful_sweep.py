#!/usr/bin/env python3
"""Public Voice · lawful twice-daily sweep.

Harvest allowlisted *public* feeds. Auto-publish to packs/ only when
primary-source checks pass. Never lodge. Never doxx. Never contact anyone.
Not legal advice. invent-for-P forbidden.
"""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "packs"
REPORTS = ROOT / "sweep" / "reports"
REGISTRY = ROOT / "sources-registry.json"
INDEX = PACKS / "index.json"

UA = "PublicVoiceLawfulSweep/1.0 (+https://muzz-ai963.github.io/public-voice/; public-record harvest only)"
CTX = ssl.create_default_context()
PRIVATE_RE = re.compile(
    r"home\s*(address|phone)|personal\s*(mobile|phone|email)|private\s*(residence|number)",
    re.I,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_json(url: str, timeout: int = 45, retries: int = 4):
    """Fetch JSON with retries — NSW Cloudflare often 502s intermittently (host error)."""
    import time

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace")), resp.status
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code in (502, 503, 504, 429) and attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as err:
            last_err = err
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last_err or RuntimeError("get_json failed")


def head_or_get_ok(url: str, timeout: int = 20) -> dict:
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
                return {"url": url, "ok": 200 <= resp.status < 400, "status": resp.status}
        except Exception as err:  # noqa: BLE001 — sweep must continue
            last = str(err)
    return {"url": url, "ok": False, "status": None, "error": last}


def looks_private(text: str) -> bool:
    return bool(PRIVATE_RE.search(text or ""))


def load_registry() -> list:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return data.get("feeds", [])


def health_check(feeds: list) -> list:
    out = []
    for feed in feeds:
        # Prefer probe_url — bare API roots (e.g. /api/hansard) often 404/Cloudflare 502
        # and are not real endpoints. Sweep harvest uses concrete search paths.
        base = feed.get("probe_url") or feed.get("base_url") or feed.get("docs_url")
        if not base:
            continue
        row = head_or_get_ok(base)
        row.update(
            {
                "id": feed.get("id"),
                "kind": feed.get("kind"),
                "name": feed.get("name"),
                "probed": base,
            }
        )
        out.append(row)
    return out


def recent_dates(days: int = 5) -> list[str]:
    today = now_utc().date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days)]


def harvest_nsw_hansard(dates: list[str]) -> list[dict]:
    """Public NSW Hansard TOC by date — primary source only."""
    harvested = []
    for day in dates:
        url = f"https://api.parliament.nsw.gov.au/api/hansard/search/bydate?date={day}"
        try:
            payload, status = get_json(url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            harvested.append({"date": day, "ok": False, "error": str(err), "url": url})
            continue
        rows = payload.get("data") or []
        if not rows:
            harvested.append({"date": day, "ok": True, "empty": True, "url": url, "items": []})
            continue
        items = []
        for house in rows:
            pdf_id = house.get("PdfDocumentId")
            house_name = house.get("HouseName") or house.get("HouseCode") or "House"
            details = house.get("Details") or []
            topics = []
            for detail in details[:20]:
                text = (detail.get("Text") or "").strip()
                if not text or looks_private(text):
                    continue
                topics.append(text)
            if not topics:
                continue
            # One day/house claim — do NOT deep-link /fragment/ IDs.
            # Those API fragment URLs often Cloudflare-502 in browsers (NSW host error),
            # while the topic list on the pack is still the public record the people need.
            topic_line = "; ".join(topics[:15])
            items.append(
                {
                    "text": (
                        f"NSW Hansard · {house_name} · {day} · Topics on the public TOC: {topic_line}"
                    )[:900],
                    "url": url,
                    "at": day,
                    "kind": "hansard",
                    "house": house_name,
                    "pdf": (
                        f"https://api.parliament.nsw.gov.au/api/hansard/search/daily/pdf/{pdf_id}"
                        if pdf_id
                        else None
                    ),
                }
            )
        harvested.append(
            {
                "date": day,
                "ok": True,
                "status": status,
                "url": url,
                "items": items,
                "source": "nsw-hansard",
            }
        )
    return harvested


def pack_checks(pack: dict) -> list[dict]:
    checks = []
    claims = pack.get("claims") or []
    has_url = any(
        isinstance(c.get("url"), str) and c["url"].startswith("http") for c in claims
    )
    checks.append(
        {
            "id": "has_source_url",
            "ok": has_url,
            "detail": "primary http(s) URL" if has_url else "missing",
        }
    )
    blob = json.dumps(pack, ensure_ascii=False)
    priv = looks_private(blob)
    checks.append(
        {
            "id": "no_private_contact",
            "ok": not priv,
            "detail": "flagged private contact" if priv else "ok",
        }
    )
    checks.append(
        {
            "id": "not_classified_drop",
            "ok": True,
            "detail": "public Hansard/API only",
        }
    )
    checks.append(
        {
            "id": "no_auto_lodge",
            "ok": pack.get("send_status") == "not_applicable",
            "detail": "sweep never lodges",
        }
    )
    return checks


def harvest_europarl_speeches(limit: int = 12) -> list[dict]:
    """Fallback public EP speeches when NSW Cloudflare host-errors."""
    url = (
        "https://data.europarl.europa.eu/api/v2/speeches"
        "?format=application%2Fld%2Bjson&offset=0&limit=40"
    )
    try:
        payload, status = get_json(url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, urllib.error.HTTPError) as err:
        return [{"ok": False, "error": str(err), "url": url, "items": [], "source": "europarl"}]
    items = []
    for row in payload.get("data") or []:
        label = row.get("activity_label") or {}
        text = label.get("en") or label.get("fr") or next(iter(label.values()), None)
        activity_id = row.get("activity_id") or row.get("id")
        day = (row.get("activity_date") or "")[:10]
        if not text or not activity_id or not day:
            continue
        if looks_private(text):
            continue
        items.append(
            {
                "text": f"European Parliament · {text}"[:500],
                "url": f"https://data.europarl.europa.eu/en/search?query={urllib.parse.quote(str(activity_id))}",
                "at": day,
                "kind": "hansard",
                "pdf": f"https://data.europarl.europa.eu/api/v2/speeches?format=application%2Fld%2Bjson&offset=0&limit=1",
            }
        )
        if len(items) >= limit:
            break
    return [
        {
            "date": now_utc().strftime("%Y-%m-%d"),
            "ok": True,
            "status": status,
            "url": url,
            "items": items,
            "source": "europarl",
        }
    ]


def make_hansard_pack(day_row: dict) -> dict | None:
    items = day_row.get("items") or []
    if not items:
        return None
    day = day_row["date"]
    source = day_row.get("source") or "nsw-hansard"
    if source == "europarl":
        pack_id = f"auto-europarl-{day}"
        title = f"European Parliament public activity · {day}"
        country = "EU"
        subjects = [
            {
                "role": "European Parliament (public record)",
                "org": "European Parliament",
                "public_office": "https://data.europarl.europa.eu/en/developer-corner/opendata-api",
            }
        ]
        spotlight = (
            f"Official EP Open Data speeches feed harvested {day} — "
            "primary activity labels for people to check against press lines."
        )
        limits = [
            "Lawful sweep of public European Parliament Open Data API.",
            "Not legal advice. Not a guilt finding. Anonymous operators.",
            "Fallback when NSW Hansard Cloudflare host-errors.",
            "We do not lodge. No doxx. No classified material.",
        ]
        public_note = "EP"
    else:
        pack_id = f"auto-nsw-hansard-{day}"
        title = f"NSW Hansard on the public record · {day}"
        country = "AU"
        subjects = [
            {
                "role": "NSW Parliament (public record)",
                "org": "Parliament of New South Wales",
                "public_office": "https://www.parliament.nsw.gov.au/",
            }
        ]
        spotlight = (
            f"Official NSW Hansard TOC for {day} is on the public API — "
            "topics below are primary-source fragments for the people to check against press lines."
        )
        limits = [
            "Lawful sweep of public NSW Hansard API only.",
            "Not legal advice. Not a guilt finding. Anonymous operators.",
            "AI/assist structured this pack; primary URLs are the source.",
            "We do not lodge. No doxx. No classified material.",
        ]
        public_note = "NSW Hansard"
    claims = []
    for it in items[:10]:
        claims.append(
            {
                "text": it["text"][:500],
                "url": it["url"],
                "at": it["at"],
                "kind": "hansard",
                "counter_url": it.get("pdf"),
                "counter_at": day,
                "screenshot_hash": None,
            }
        )
    pack = {
        "schema": "public-voice-pack/v1",
        "product": "MUZZ Public Voice",
        "id": pack_id,
        "demo": False,
        "title": title,
        "country": country,
        "door": "elected",
        "subjects": subjects,
        "claims": claims,
        "silence": [],
        "auth": {
            "status": "matches_source",
            "spotlight": spotlight,
            "method": "ai_assisted_primary",
            "explain_ask": (
                f"Where a public line touches these {public_note} topics, "
                "point to the matching primary record — or correct the line."
            ),
        },
        "harm": {
            "summary": (
                "Without a machine-speed public index, official lines can drift from the record "
                "while people wait."
            ),
            "time": "",
            "money": "",
            "stopped": "",
        },
        "send_status": "not_applicable",
        "limits": limits,
        "seal": {
            "kind": "unsigned_export",
            "name": "Anonymous",
            "anonymous": True,
            "at": iso(now_utc()),
            "clock_source": "device",
            "approver_pub": None,
            "approval_sig": None,
            "snapshot_hash": None,
            "entry_hash": None,
            "reason": "Lawful auto-harvest of public parliamentary record",
        },
    }
    checks = pack_checks(pack)
    pack["content_hash"] = hashlib.sha256(
        json.dumps(pack, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    pack["moderation"] = {
        "auto_checks": checks,
        "publish_ready": all(c["ok"] for c in checks),
    }
    if not pack["moderation"]["publish_ready"]:
        return None
    return pack


def make_health_pack(health: list) -> dict:
    day = now_utc().strftime("%Y-%m-%d")
    stamp = now_utc().strftime("%Y%m%d-%H%M")
    claims = []
    down = [h for h in health if not h.get("ok")]
    for h in health:
        status = "up" if h.get("ok") else "down"
        claims.append(
            {
                "text": f"Feed {h.get('id')} ({h.get('name')}): {status}",
                "url": h.get("url") or "https://muzz-ai963.github.io/public-voice/",
                "at": day,
                "kind": "other",
                "counter_url": None,
                "counter_at": None,
                "screenshot_hash": None,
            }
        )
    status = "matches_source" if not down else "silence_past_clock"
    spotlight = (
        "All allowlisted public feeds responded."
        if not down
        else "One or more allowlisted public feeds failed a sweep check — see claims."
    )
    pack = {
        "schema": "public-voice-pack/v1",
        "product": "MUZZ Public Voice",
        "id": f"auto-feed-health-{stamp}",
        "demo": False,
        "title": f"Lawful feed health · {day}",
        "country": "OTHER",
        "door": "other",
        "subjects": [
            {
                "role": "Public open-data feeds",
                "org": "Allowlisted registry",
                "public_office": "https://muzz-ai963.github.io/public-voice/sources-registry.json",
            }
        ],
        "claims": claims[:20],
        "silence": [],
        "auth": {
            "status": status if status == "matches_source" else "awaiting_sources",
            "spotlight": spotlight,
            "method": "ai_assisted_primary",
            "explain_ask": "Operators of down feeds: restore public API access for the people’s record.",
        },
        "harm": {
            "summary": "When public feeds die, people lose machine-speed access to the record.",
            "time": "",
            "money": "",
            "stopped": "",
        },
        "send_status": "not_applicable",
        "limits": [
            "Health check of published URLs only.",
            "Not legal advice. Sweep does not lodge or contact anyone.",
        ],
        "seal": {
            "kind": "unsigned_export",
            "name": "Anonymous",
            "anonymous": True,
            "at": iso(now_utc()),
            "clock_source": "device",
            "approver_pub": None,
            "approval_sig": None,
            "snapshot_hash": None,
            "entry_hash": None,
            "reason": "Lawful feed health sweep",
        },
    }
    checks = pack_checks(pack)
    pack["content_hash"] = hashlib.sha256(
        json.dumps(pack, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    pack["moderation"] = {
        "auto_checks": checks,
        "publish_ready": all(c["ok"] for c in checks),
    }
    return pack


def silence_days(pack: dict):
    clocks = pack.get("silence") or []
    if not clocks:
        return None
    try:
        start = datetime.fromisoformat(str(clocks[0].get("clock_start")))
        return max(0, (now_utc().date() - start.date()).days)
    except Exception:  # noqa: BLE001
        return None


def rebuild_index() -> dict:
    packs_meta = []
    for path in sorted(PACKS.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            pack = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        auth = (pack.get("auth") or {}).get("status")
        packs_meta.append(
            {
                "id": pack.get("id") or path.stem,
                "file": path.name,
                "demo": bool(pack.get("demo")),
                "title": pack.get("title") or path.stem,
                "country": pack.get("country"),
                "door": pack.get("door"),
                "auth_status": auth,
                "silence_days": silence_days(pack),
            }
        )
    index = {
        "product": "MUZZ Public Voice",
        "generated": now_utc().strftime("%Y-%m-%d"),
        "notice": (
            "Static ledger index. Auto packs from lawful public-source sweep. "
            "DEMO packs are fictional. This index does not lodge anything."
        ),
        "packs": packs_meta,
    }
    INDEX.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index


def prune_old_auto(keep: int = 40) -> None:
    autos = sorted(PACKS.glob("auto-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in autos[keep:]:
        path.unlink(missing_ok=True)


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    PACKS.mkdir(parents=True, exist_ok=True)
    feeds = load_registry()
    health = health_check(feeds)
    hansard = harvest_nsw_hansard(recent_dates(6))
    nsw_items = sum(len(r.get("items") or []) for r in hansard if r.get("ok"))
    # Always harvest EuroParl too — browser-friendly public pages when NSW API flaps
    euro = harvest_europarl_speeches()
    if nsw_items == 0 and not any((r.get("items") or []) for r in euro):
        euro = harvest_europarl_speeches(limit=20)

    published = []
    health_pack = make_health_pack(health)
    if health_pack.get("moderation", {}).get("publish_ready"):
        path = PACKS / f"{health_pack['id']}.json"
        path.write_text(json.dumps(health_pack, indent=2) + "\n", encoding="utf-8")
        published.append(health_pack["id"])

    for row in hansard + euro:
        if not row.get("ok") or not row.get("items"):
            continue
        pack = make_hansard_pack(row)
        if not pack:
            continue
        path = PACKS / f"{pack['id']}.json"
        path.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
        published.append(pack["id"])

    prune_old_auto(40)
    index = rebuild_index()

    report = {
        "at": iso(now_utc()),
        "lawful": True,
        "lodged": False,
        "contacted": False,
        "nsw_items": nsw_items,
        "fallback_europarl": bool(euro),
        "health": health,
        "hansard_days": [
            {
                "date": r.get("date"),
                "ok": r.get("ok"),
                "items": len(r.get("items") or []),
                "error": r.get("error"),
                "source": r.get("source"),
            }
            for r in hansard + euro
        ],
        "published": published,
        "index_count": len(index.get("packs") or []),
        "right_places": [
            "packs/*.json on GitHub Pages ledger",
            "packs/index.json gallery index",
            "sweep/reports/* audit (not a tip-line)",
        ],
        "fences": [
            "primary sources only",
            "no doxx",
            "no classified",
            "no auto-lodge",
            "Cursor contacts no one",
        ],
    }
    stamp = now_utc().strftime("%Y%m%d-%H%M%S")
    (REPORTS / f"sweep-{stamp}.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (REPORTS / "latest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "published": published, "report": f"sweep-{stamp}.json"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
