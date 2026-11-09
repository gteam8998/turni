/* Service worker: tiene in memoria l'app per aprirla subito, anche con rete scarsa.
   I dati (Firebase) e la lettura delle foto (Gemini) passano sempre da internet. */
const CACHE = "turni-2026.11.10-1";
const SHELL = ["./", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;            // Firebase, Gemini, font: sempre rete
  if (e.request.mode === "navigate" || u.pathname.endsWith("firebase-config.js")){     // pagina e configurazione: prima la rete
    e.respondWith(fetch(e.request).then(r => { if (r.ok){ const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request.mode === "navigate" ? "./" : e.request, c)); } return r; })
      .catch(() => caches.match(e.request.mode === "navigate" ? "./" : e.request, {ignoreSearch: true})));
    return;
  }
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => { if (r.ok){ const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); } return r; })));
});
