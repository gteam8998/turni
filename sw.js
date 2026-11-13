/* Service worker: tiene in memoria l'app per aprirla subito, anche con rete scarsa.
   I dati (Firebase) e la lettura delle foto (Gemini) passano sempre da internet. */
const CACHE = "turni-2026.11.13-38";
const LIBS = "turni-libs-1";              // non cambia a ogni versione: le librerie restano
const SHELL = ["./", "manifest.webmanifest", "icons/logo-192.png", "icons/logo-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE && k !== LIBS).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  /* librerie di Firebase (versione fissa nell'indirizzo) e font: le tengo sul telefono, così l'app si apre senza riscaricarle */
  if (u.origin !== location.origin){
    const keep = (u.hostname === "www.gstatic.com" && u.pathname.startsWith("/firebasejs/")) || u.hostname === "fonts.gstatic.com" || u.hostname === "fonts.googleapis.com";
    if (!keep) return;                                                                  // dati di Firebase, Gemini, notifiche: sempre rete
    const net = c => fetch(e.request).then(r => { if (r.ok || r.type === "opaque") c.put(e.request, r.clone()); return r; });
    e.respondWith(caches.open(LIBS).then(c => c.match(e.request).then(hit => {
      if (!hit) return net(c);
      if (u.hostname === "fonts.googleapis.com") net(c).catch(() => {});                // il foglio dei font lo aggiorno dietro le quinte
      return hit;
    })));
    return;
  }
  if (e.request.mode === "navigate" || u.pathname.endsWith("firebase-config.js") || u.pathname.endsWith("manifest.webmanifest")){     // pagina, configurazione e manifest: sempre dalla rete
    /* cache: "no-cache" = chiedo sempre a GitHub se c'è una versione nuova (senza, il telefono teneva la vecchia fino a 10 minuti) */
    const key = e.request.mode === "navigate" ? "./" : e.request;
    const net = fetch(e.request, {cache: "no-cache"}).then(r => { if (r.ok){ const c = r.clone(); e.waitUntil(caches.open(CACHE).then(x => x.put(key, c))); } return r; });
    const old = () => caches.match(key, {ignoreSearch: true});
    /* con rete lenta non resto ad aspettare: dopo 2,5 secondi apro la copia sul telefono (le versioni nuove arrivano comunque con l'aggiornamento automatico) */
    e.respondWith(new Promise(res => {
      let done = false; const go = r => { if (!done && r){ done = true; res(r); } };
      const t = setTimeout(() => old().then(go), 2500);
      net.then(r => { clearTimeout(t); go(r); }).catch(() => { clearTimeout(t); old().then(r => r ? go(r) : go(Response.error())); });
    }));
    return;
  }
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => { if (r.ok){ const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); } return r; })));
});

/* notifiche: «Nuovi turni caricati» e messaggi del responsabile */
self.addEventListener("push", e => {
  let d = {}; try { d = e.data ? e.data.json() : {}; } catch { d = {body: e.data ? e.data.text() : ""}; }
  e.waitUntil(Promise.all([
    self.registration.showNotification(d.title || "Turni Arese", {body: d.body || "Ci sono turni nuovi", icon: "icons/logo-192.png", badge: "icons/logo-badge-96.png", tag: d.tag || "turni-nuovi", renotify: true, data: {url: d.url || "./#me"}}),
    self.navigator && self.navigator.setAppBadge ? self.navigator.setAppBadge(1).catch(() => {}) : null
  ]));
});
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "./#me", self.registration.scope).href;
  e.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then(list => {
    for (const c of list){ if (c.url.startsWith(self.registration.scope)){ c.focus(); return c.navigate ? c.navigate(url).catch(() => {}) : null; } }
    return self.clients.openWindow(url);
  }));
});
