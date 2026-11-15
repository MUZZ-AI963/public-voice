/* Public Voice — offline shell for every laptop. Cache-first static; network for fresh packs when online. */
const CACHE = "public-voice-v6";
const PRECACHE = [
  "./",
  "./index.html",
  "./gallery.html",
  "./onboarding.html",
  "./security.html",
  "./ai-forward.html",
  "./LIMITS.md",
  "./LICENSE",
  "./pack.schema.json",
  "./jurisdictions.json",
  "./sources-registry.json",
  "./manifest.webmanifest",
  "./icon.svg",
  "./packs/index.json",
  "./packs/demo-foi-silence.json",
  "./packs/demo-claim-rehash.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(req).then((cached) => {
      const fetched = fetch(req)
        .then((res) => {
          if (res && res.ok && url.pathname.indexOf("/packs/") !== -1) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put(req, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || fetched;
    })
  );
});
