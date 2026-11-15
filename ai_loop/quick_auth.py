#!/usr/bin/env python3
"""Public Voice AI loop — URL in → structural auth + formal email report.

Lawful assist only: fetches public URLs, structures status, drafts report.
Does not lodge, doxx, or contact anyone. invent-for-P forbidden.

Usage:
  python3 ai_loop/quick_auth.py --url 'https://…' [--quote '…'] [--counter 'https://…'] [--out report.txt]
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "PublicVoiceAI/1.0 (+https://muzz-ai963.github.io/public-voice/; primary-source assist)"
CTX = ssl.create_default_context()


def fetch(url: str, timeout: int = 40) -> str:
    readers = [
        "https://r.jina.ai/" + url,
        url,
    ]
    last = None
    for endpoint in readers:
        try:
            req = urllib.request.Request(
                endpoint, headers={"User-Agent": UA, "Accept": "text/plain,text/html,*/*"}
            )
            with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                if len(text) > 40:
                    return text[:120000]
        except Exception as err:  # noqa: BLE001
            last = err
    raise RuntimeError(f"fetch failed: {last}")


def tokens(s: str) -> set[str]:
    return {w for w in re.sub(r"[^a-z0-9\s]", " ", s.lower()).split() if len(w) > 3}


def overlap(a: str, b: str) -> float:
    A, B = tokens(a), tokens(b)
    if not A or not B:
        return 0.0
    return len(A & B) / min(len(A), len(B))


def pick_quote(user_quote: str, fetched: str) -> str:
    if user_quote and len(user_quote) >= 8:
        return user_quote[:1200]
    lines = [l.strip() for l in fetched.splitlines() if 40 < len(l.strip()) < 280]
    scored = [l for l in lines if re.search(r"said|announc|deliver|under review|completed|budget", l, re.I)]
    return (scored[0] if scored else (lines[0] if lines else "See primary source URL."))[:1200]


def authenticate(quote: str, source: str, counter: str | None, counter_text: str) -> dict:
    src = (source or "") + "\n" + quote
    under = bool(re.search(r"under review|being considered|cannot comment", src, re.I))
    delivered = bool(re.search(r"deliver(ed|y)|on time|under budget|completed", quote, re.I))
    denies = bool(
        counter
        and re.search(
            r"planning|not yet|delayed|cancelled|proposed|incorrect|correction|clarify",
            counter_text or "",
            re.I,
        )
    )
    ov = overlap(quote, counter_text) if counter else 0.0
    if counter and (denies or ov < 0.12):
        return {
            "status": "contradicted_by_source" if denies else "rehash_unanchored",
            "spotlight": (
                "Public statement does not stack with the counter primary source."
                if denies
                else "Little overlap with counter source — possible unanchored rehash."
            ),
            "explain_ask": "Point to the matching primary record — or correct the public line.",
        }
    if delivered and under:
        return {
            "status": "rehash_unanchored",
            "spotlight": "Completion language alongside ‘under review’ process language.",
            "explain_ask": "Publish the completion notice or amend the claim.",
        }
    if not counter:
        return {
            "status": "awaiting_sources",
            "spotlight": "Primary source captured; no counter URL in this pass.",
            "explain_ask": "Confirm against the full public record or add a counter URL.",
        }
    return {
        "status": "matches_source",
        "spotlight": "No strong structural mismatch in this automated pass.",
        "explain_ask": "Confirm on the record or supply a sourced correction.",
    }


def report(auth: dict, url: str, quote: str, counter: str | None, country: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""PUBLIC VOICE · FORMAL REPORT — DRAFT · NOT LODGED
Your right to challenge · Free platform for people
Prepared: {today} (device/runner clock)
Holder: Anonymous
Country: {country}

=== AUTHENTICATION (structural — not a legal finding) ===
Status: {auth['status']}
Method: Public Voice AI loop (primary-source assist)
Spotlight: {auth['spotlight']}
Explain ask: {auth['explain_ask']}

=== PRIMARY SOURCE ===
URL: {url}
Statement / quote:
{quote}

=== COUNTER / CHECK ===
{('URL: ' + counter) if counter else '(none)'}

=== REQUEST ===
I request an on-record explanation that stacks with the primary sources above, or a public correction if the line does not.

Please reply within 14 days of receiving this. That 14 days is the reply I am asking for; it is not stated here as a statutory period.

=== LIMITS ===
General information, not legal advice. Public Voice does not lodge.
Primary sources only. AI assists; AI is not itself a publishable source of “not true.”
No doxx. No classified. Seal separately in the browser Quick path.
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Public Voice AI quick auth loop")
    p.add_argument("--url", required=True)
    p.add_argument("--quote", default="")
    p.add_argument("--counter", default="")
    p.add_argument("--country", default="AU")
    p.add_argument("--out", default="")
    p.add_argument("--json-out", default="")
    args = p.parse_args(argv)

    source = fetch(args.url)
    quote = pick_quote(args.quote, source)
    counter_text = ""
    if args.counter:
        try:
            counter_text = fetch(args.counter)
        except Exception as err:  # noqa: BLE001
            counter_text = f"(counter fetch failed: {err})"
    auth = authenticate(quote, source, args.counter or None, counter_text)
    text = report(auth, args.url, quote, args.counter or None, args.country)
    payload = {
        "auth": auth,
        "url": args.url,
        "quote": quote,
        "counter": args.counter or None,
        "formal_report": text,
        "method": "ai_assisted_primary",
        "lodged": False,
    }
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
