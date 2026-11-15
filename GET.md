# Public Voice · available on every laptop

**Goal:** Anyone, anywhere, with a laptop and a browser, can open the desk and the ledger — free, anonymous-capable, no app store.

## Ways it reaches a laptop

| Path | Who | What |
|---|---|---|
| **Hosted HTTPS** | Everyone | One URL (GitHub Pages or any mirror). First visit caches the shell; works offline after. |
| **Zip** | Offline / USB / school lab | `muzz-public-voice.zip` → local `python3 -m http.server` → `http://127.0.0.1:8765` |
| **Mirror host** | NGO, library, agency, journalist | Copy folder under LICENSE onto their HTTPS |
| **PWA install** | Chromium / Edge / Android | “Install on this laptop” after HTTPS visit |

Seal needs a **secure context** (`https://` or `http://127.0.0.1`). Plain `file://` can browse drafts but may not sign.

## Go live (Murray)

When ready, say: **“create public public-voice Pages repo and push.”**

Cursor will (and will contact no one else):

1. Create public `MUZZ-AI963/public-voice` (same pattern as lockout-reporter).  
2. Push `docs/public-voice/` static files.  
3. Enable Pages.  
4. Live URL target: **https://muzz-ai963.github.io/public-voice/**

Until then: local prove at `http://127.0.0.1:8765/` and the zip in this folder.

## Operator face

No personal names on the UI. LICENSE keeps company copyright for free worldwide hosting.
