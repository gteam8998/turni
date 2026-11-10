/*
  TURNI ARESE · invio delle notifiche (Cloudflare Worker)
  ------------------------------------------------------
  Non contiene chiavi né password. Funziona così:
  1. l'app del responsabile chiama questo indirizzo con il suo "gettone" di accesso Firebase
  2. con quel gettone leggo da Firestore la chiave delle notifiche (config/push) e l'elenco dei telefoni iscritti (push/…):
     Firestore li dà solo al responsabile, quindi nessun altro può usare questo servizio
  3. mando a ogni telefono la notifica, cifrata come chiede lo standard Web Push (RFC 8291 + VAPID RFC 8292)
*/
const PROJECT = "turni-arese";
const ORIGINS = ["https://gteam8998.github.io"];
const FS = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents`;

const enc = new TextEncoder();
const b64u = buf => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const unb64u = s => { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; return Uint8Array.from(atob(s), c => c.charCodeAt(0)); };
const cat = (...a) => { const o = new Uint8Array(a.reduce((n, x) => n + x.length, 0)); let i = 0; for (const x of a){ o.set(x, i); i += x.length; } return o; };

async function hkdf(salt, ikm, info, len){
  const k = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({name: "HKDF", hash: "SHA-256", salt, info}, k, len * 8));
}

/* cifratura aes128gcm del messaggio per un telefono (RFC 8291) */
async function encrypt(sub, text){
  const ua = unb64u(sub.keys.p256dh), auth = unb64u(sub.keys.auth);
  const as = await crypto.subtle.generateKey({name: "ECDH", namedCurve: "P-256"}, true, ["deriveBits"]);
  const asPub = new Uint8Array(await crypto.subtle.exportKey("raw", as.publicKey));
  const uaKey = await crypto.subtle.importKey("raw", ua, {name: "ECDH", namedCurve: "P-256"}, false, []);
  const secret = new Uint8Array(await crypto.subtle.deriveBits({name: "ECDH", public: uaKey}, as.privateKey, 256));
  const ikm = await hkdf(auth, secret, cat(enc.encode("WebPush: info\0"), ua, asPub), 32);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const cek = await hkdf(salt, ikm, enc.encode("Content-Encoding: aes128gcm\0"), 16);
  const nonce = await hkdf(salt, ikm, enc.encode("Content-Encoding: nonce\0"), 12);
  const key = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["encrypt"]);
  const ct = new Uint8Array(await crypto.subtle.encrypt({name: "AES-GCM", iv: nonce}, key, cat(enc.encode(text), new Uint8Array([2]))));
  const rs = new Uint8Array([0, 0, 16, 0]);   // 4096
  return cat(salt, rs, new Uint8Array([asPub.length]), asPub, ct);
}

/* firma VAPID (JWT ES256) per il servizio di notifiche di quel telefono */
async function vapid(endpoint, jwk, pub, subject){
  const aud = new URL(endpoint).origin;
  const head = b64u(enc.encode(JSON.stringify({typ: "JWT", alg: "ES256"})));
  const body = b64u(enc.encode(JSON.stringify({aud, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: subject})));
  const key = await crypto.subtle.importKey("jwk", jwk, {name: "ECDSA", namedCurve: "P-256"}, false, ["sign"]);
  const sig = await crypto.subtle.sign({name: "ECDSA", hash: "SHA-256"}, key, enc.encode(head + "." + body));
  return `vapid t=${head}.${body}.${b64u(sig)}, k=${pub}`;
}

async function sendOne(sub, text, cfg){
  const body = await encrypt(sub, text);
  const r = await fetch(sub.endpoint, {method: "POST", body, headers: {
    "Content-Type": "application/octet-stream", "Content-Encoding": "aes128gcm", TTL: "86400", Urgency: "normal",
    Authorization: await vapid(sub.endpoint, cfg.jwk, cfg.pub, cfg.subject)}});
  return r.status;
}

const fsStr = (doc, f) => doc && doc.fields && doc.fields[f] && doc.fields[f].stringValue || "";
async function fsGet(path, token){
  const r = await fetch(`${FS}/${path}`, {headers: {Authorization: "Bearer " + token}});
  if (r.status === 403 || r.status === 401) throw {status: 403};
  if (!r.ok) throw {status: 502};
  return r.json();
}

function cors(req){
  const o = req.headers.get("Origin") || "";
  return {"Access-Control-Allow-Origin": ORIGINS.includes(o) ? o : ORIGINS[0], "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Max-Age": "86400", Vary: "Origin"};
}
const json = (req, obj, status = 200) => new Response(JSON.stringify(obj), {status, headers: {...cors(req), "Content-Type": "application/json"}});

export default {
  async fetch(req){
    if (req.method === "OPTIONS") return new Response(null, {status: 204, headers: cors(req)});
    if (req.method !== "POST") return json(req, {ok: true, service: "turni-push"});
    const token = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
    if (!token) return json(req, {error: "no_token"}, 401);
    let msg = {}; try { msg = await req.json(); } catch {}
    const title = String(msg.title || "Turni Arese").slice(0, 80), text = String(msg.body || "").slice(0, 200), url = String(msg.url || "./").slice(0, 200);
    try {
      const conf = await fsGet("config/push", token);
      const cfg = {jwk: JSON.parse(fsStr(conf, "priv") || "null"), pub: fsStr(conf, "pub"), subject: fsStr(conf, "subject") || "https://gteam8998.github.io/turni/"};
      if (!cfg.jwk || !cfg.pub) return json(req, {error: "no_keys"}, 400);
      const list = await fsGet("push?pageSize=300", token);
      const subs = (list.documents || []).map(d => { try { return {id: d.name.split("/").pop(), sub: JSON.parse(fsStr(d, "sub"))}; } catch { return null; } }).filter(x => x && x.sub && x.sub.endpoint);
      const payload = JSON.stringify({title, body: text, url});
      const res = await Promise.all(subs.map(async s => { try { return {id: s.id, status: await sendOne(s.sub, payload, cfg)}; } catch (e) { return {id: s.id, status: 0}; } }));
      return json(req, {sent: res.filter(r => r.status >= 200 && r.status < 300).length, total: subs.length, gone: res.filter(r => r.status === 404 || r.status === 410).map(r => r.id), results: res});
    } catch (e) {
      return json(req, {error: e && e.status === 403 ? "forbidden" : "failed"}, e && e.status === 403 ? 403 : 502);
    }
  }
};
