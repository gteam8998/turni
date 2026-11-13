#!/usr/bin/env python3
"""
TURNI ARESE · controllo serale
------------------------------
Apre l'app in MODALITÀ PROVA (dati finti, niente Firebase) in un browser automatico e controlla:
  - errori JavaScript e risorse che non si caricano
  - testi che escono dal loro riquadro, pagina più larga dello schermo, scritte sovrapposte, immagini rotte
  - tempo di apertura dell'app e peso dei file
su telefono piccolo (320), telefono (390), tablet (768) e PC (1366), tema chiaro, scuro e con sfondo,
per collega, responsabile e PC del banco, compresa la vista "Prossimo turno" con le frecce.

Uso (dalla cartella del repository):  python3 controlli/controllo.py --out /percorso/cartella-report
Scrive report.json, report.md e le schermate. Non tocca i dati veri: i nomi sono inventati.
"""
import argparse, json, os, shutil, socket, sys, tempfile, threading, time, http.server, functools, datetime, re

try:
    from zoneinfo import ZoneInfo
    TODAY = datetime.datetime.now(ZoneInfo("Europe/Rome")).date()
except Exception:
    TODAY = datetime.date.today()

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ---------- dati finti ----------
STAFF = [  # id, nome, cognome, contratto
    ("adm", "Giulio", "Ferraresi", 40),
    ("usr", "Maria Antonietta", "Bellavista Castiglioni", 30),
    ("jo", "Jo", "Li", 24),
    ("fra", "Francesco Saverio", "Dell'Acqua Montecristo", 36),
    ("ele", "Eleonora", "Santangelo", 30),
    ("max", "Massimiliano", "Quattrocchi", 40),
    ("ann", "Anna", "Re", 20),
    ("gab", "Gabriele", "Vitali", 30),
]
PATTERNS = [  # turni che si alternano: liste di (inizio, fine, reparto, sigla altro reparto)
    [("09:00", "13:00", "tel", ""), ("13:30", "18:00", "tel", "")],
    [("15:30", "21:30", "srv", "")],
    [("08:30", "12:00", "tel", ""), ("12:30", "15:00", "srv", "")],
    [],  # riposo
    [("13:30", "18:00", "alt", "MAG A"), ("18:30", "22:00", "tel", "")],
    [("10:00", "14:00", "srv", ""), ("14:30", "19:00", "srv", "")],
    [("07:00", "13:00", "alt", "TV")],
]

def seed(today):
    db = {"setup/state": {"admin": "u-adm", "at": "2026-01-01T00:00:00Z"}}
    for i, (sid, n, c, h) in enumerate(STAFF):
        db[f"staff/{sid}"] = {"name": n, "full": f"{n} {c}", "cognome": c, "order": i, "contratto": h}
    users = {}
    for uid, sid, role in [("u-adm", "adm", "admin"), ("u-usr", "usr", "user"), ("u-pc", "", "banco")]:
        db[f"members/{uid}"] = {"role": role, "staffId": sid, "at": "2026-01-01T00:00:00Z"}
        email = f"{uid}@prova.test"; users[email] = {"pw": "prova123", "uid": uid}
        if sid: db[f"logins/{sid}"] = {"staffId": sid, "email": email, "uid": uid}
    for k in range(-14, 22):
        d = today + datetime.timedelta(days=k)
        if k >= 16 and k % 2: continue                      # alcuni giorni lontani "non ancora caricati"
        rows = {}
        for j, (sid, *_r) in enumerate(STAFF):
            p = PATTERNS[(k + j * 3) % len(PATTERNS)]
            if sid == "usr" and k == 0: p = PATTERNS[0]      # oggi la collega lavora (spezzato)
            rows[sid] = [dict(s=a, e=b, d=dep, **({"g": g} if g else {})) for a, b, dep, g in p]
        db[f"shifts/{d.isoformat()}"] = {"date": d.isoformat(), "rows": rows}
    for k, (t, kind) in enumerate([("10:30", "rip"), ("16:00", "dati"), ("", "rip")]):
        d = (today + datetime.timedelta(days=k + 1)).isoformat()
        db[f"appts/p{k}"] = {"date": d, "time": t, "kind": kind, "model": "iPhone 15 Pro Max 256 GB Titanio Naturale" if k == 0 else "Galaxy A55",
                             "part": "Schermo", "gb": 128, "price": 89.9, "name": "Cliente di prova con nome lungo", "status": "attesa"}
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)
    db["news/novita-prova"] = {"kind": "novita", "title": "Novità: apri il tuo prossimo turno ✨", "body": "Tocca «Prossimo turno» nella tua area: vedi quel giorno come se fosse oggi.\n\n‹ › frecce per scorrere i giorni\n«Torna a oggi» per rientrare", "at": now.isoformat() + "Z", "by": "adm"}
    db["news/t-prova"] = {"kind": "turni", "title": "Nuovi turni caricati", "body": "Turni dal 16 al 22 novembre: li trovi nella tua area.", "at": (now - datetime.timedelta(days=1)).isoformat() + "Z", "by": "adm"}
    db["shifts/_push"] = {"kind": "push", "pub": "", "admin": "Giulio"}
    db["feedback/f-prova"] = {"uid": "u-usr", "staffId": "usr", "name": "Maria Antonietta Bellavista Castiglioni", "kind": "errore", "text": "Nella settimana non vedo il sabato quando ho il turno spezzato, mi sembra che manchi una riga. Succede solo a me?", "at": (now - datetime.timedelta(hours=2)).isoformat() + "Z"}
    db["feedback/f-prova2"] = {"uid": "u-usr", "staffId": "usr", "name": "Maria Antonietta Bellavista Castiglioni", "kind": "idea", "text": "Sarebbe utile poter scambiare un turno con un collega.", "at": (now - datetime.timedelta(days=2)).isoformat() + "Z", "reply": "Bella idea, ci lavoro!", "replyAt": (now - datetime.timedelta(days=1)).isoformat() + "Z"}
    return db, users

# ---------- server locale ----------
def serve(folder):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=folder)
    H.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}/"

AUDIT_JS = r"""
() => {
  const vw = innerWidth, out = [];
  const shown = el => { if (el.closest('[hidden]')) return false; const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false; const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const nm = el => { const p = el.parentElement; const one = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + [...e.classList].slice(0, 2).map(c => '.' + c).join(''); return (p ? one(p) + ' > ' : '') + one(el); };
  const tx = el => (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 70);
  const direct = el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
  const fixedAnc = el => { for (let a = el; a && a !== document.body; a = a.parentElement) if (getComputedStyle(a).position === 'fixed' || getComputedStyle(a).position === 'sticky') return true; return false; };
  const scrollAnc = el => { for (let a = el.parentElement; a && a !== document.body; a = a.parentElement){ const o = getComputedStyle(a).overflowX; if (o === 'auto' || o === 'scroll') return true; } return false; };
  if (document.documentElement.scrollWidth > vw + 1) out.push({tipo: 'pagina più larga dello schermo', dettaglio: document.documentElement.scrollWidth + 'px su ' + vw + 'px'});
  const leaves = [];
  for (const el of document.body.querySelectorAll('*')){
    const tag = el.tagName.toLowerCase();
    if (['script','style','svg','path','circle','rect','g','canvas','video','option','br','noscript'].includes(tag) || el.closest('svg') || !shown(el)) continue;
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    if (tag === 'img'){ if (el.complete && !el.naturalWidth) out.push({tipo: 'immagine rotta', dove: nm(el)}); continue; }
    if (cs.position !== 'fixed' && !scrollAnc(el) && (r.right > vw + 1.5 || r.left < -1.5) && direct(el)) out.push({tipo: 'esce dallo schermo', dove: nm(el), testo: tx(el), dettaglio: Math.round(r.left) + '…' + Math.round(r.right) + ' su ' + vw});
    const clip = cs.textOverflow === 'ellipsis';
    if (!clip && direct(el) && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll' && el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0 && !['input','textarea','select','button'].includes(tag))
      out.push({tipo: 'testo più largo del suo riquadro', dove: nm(el), testo: tx(el), dettaglio: el.scrollWidth + 'px in ' + el.clientWidth + 'px'});
    if (direct(el) && !fixedAnc(el) && cs.position !== 'absolute' && !el.closest('.dayline,.bars,.ring')) leaves.push(el);
  }
  // scritte sovrapposte (fra elementi che non si contengono)
  // ogni riga di testo ha il suo rettangolo (un testo su due righe non conta come sovrapposto)
  const R = leaves.slice(0, 600).map(e => [e, [...e.getClientRects()].filter(r => r.width > 0 && r.height > 0)]);
  const hit = (ra, rb) => { const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left), h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top); return w > 4 && h > 4 && w * h > .25 * Math.min(ra.width * ra.height, rb.width * rb.height); };
  for (let i = 0; i < R.length; i++) for (let j = i + 1; j < R.length; j++){
    const [a, ra] = R[i], [b, rb] = R[j]; if (a.contains(b) || b.contains(a)) continue;
    if (ra.some(x => rb.some(y => hit(x, y)))) out.push({tipo: 'scritte sovrapposte', dove: nm(a) + '  ×  ' + nm(b), testo: tx(a) + '  ×  ' + tx(b)});
  }
  return out;
}
"""

def main():
    global ROOT
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(tempfile.gettempdir(), "turni-controllo"))
    ap.add_argument("--app", default=ROOT, help="cartella con index.html (di solito la radice del repository)"); a = ap.parse_args()
    ROOT = os.path.abspath(a.app)
    out = os.path.abspath(a.out); shots = os.path.join(out, "schermate"); os.makedirs(shots, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Manca playwright per Python"); sys.exit(2)

    # copia dell'app in modalità prova
    tmp = tempfile.mkdtemp(prefix="turni-prova-")
    for f in os.listdir(ROOT):
        if f.startswith(".") or f in ("controlli",): continue
        src = os.path.join(ROOT, f)
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, os.path.join(tmp, f))
    with open(os.path.join(tmp, "firebase-config.js"), "w") as fh:
        fh.write('window.TURNI_CONFIG = {firebase: {apiKey: ""}, push: ""};\n')
    with open(os.path.join(tmp, "blank.txt"), "w") as fh: fh.write("ok")
    srv, base = serve(tmp)

    report = {"data": TODAY.isoformat(), "versione": "", "pesi": {}, "tempi": [], "errori_js": [], "problemi": [], "schermate": []}
    sw = open(os.path.join(ROOT, "sw.js"), encoding="utf-8").read()
    m = re.search(r'turni-(\d{4}\.\d{2}\.\d{2}-\d+)', sw); report["versione"] = m.group(1) if m else "?"
    for f in ["index.html", "sw.js", "firebase-config.js", "manifest.webmanifest"]:
        p = os.path.join(ROOT, f); report["pesi"][f] = os.path.getsize(p) if os.path.exists(p) else None
    try:
        man = json.load(open(os.path.join(ROOT, "manifest.webmanifest")))
        for ic in man.get("icons", []):
            if not os.path.exists(os.path.join(ROOT, ic["src"])): report["problemi"].append({"tipo": "icona mancante", "dove": ic["src"]})
    except Exception as e: report["problemi"].append({"tipo": "manifest illeggibile", "dettaglio": str(e)})
    if report["pesi"].get("index.html", 0) and report["pesi"]["index.html"] > 450_000:
        report["problemi"].append({"tipo": "pagina pesante", "dettaglio": f"index.html {report['pesi']['index.html']//1024} KB (soglia 450 KB)"})

    db, users = seed(TODAY)
    bg = None
    try:  # immagine colorata per provare lo sfondo personale
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (600, 1000)); dr = ImageDraw.Draw(im)
        for y in range(1000): dr.line([(0, y), (600, y)], fill=(40 + y // 6, 30, 160 - y // 8))
        for i in range(18): dr.ellipse([i * 37 % 600 - 60, i * 113 % 1000 - 60, i * 37 % 600 + 80, i * 113 % 1000 + 80], fill=[(255, 200, 40), (40, 220, 255), (255, 80, 140)][i % 3])
        bg = os.path.join(tmp, "sfondo.jpg"); im.save(bg, quality=80)
    except Exception: pass

    who = {"collega": "u-usr@prova.test", "responsabile": "u-adm@prova.test", "banco": "u-pc@prova.test", "accesso": None}
    piani = [  # (chi, larghezza, altezza, tema, schermate)
        ("collega", 320, 640, "light", ["me", "me-prossimo", "me-frecce", "msg", "set"]),
        ("collega", 390, 844, "light", ["me", "me-prossimo", "me-frecce", "me-passato", "set"]),
        ("collega", 390, 844, "dark", ["me", "me-prossimo", "msg", "set"]),
        ("collega", 390, 844, "sfondo", ["me", "me-prossimo"]),
        ("responsabile", 390, 844, "light", ["me", "agenda", "carica", "msg", "set"]),
        ("responsabile", 768, 1024, "dark", ["me", "agenda", "set"]),
        ("responsabile", 1366, 860, "light", ["agenda", "me", "me-prossimo", "carica", "msg", "set"]),
        ("banco", 1366, 860, "dark", ["agenda", "set"]),
        ("accesso", 320, 640, "light", ["login"]),
        ("accesso", 390, 844, "dark", ["login"]),
    ]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for chi, w, h, tema, screens in piani:
            ctx = b.new_context(viewport={"width": w, "height": h}, locale="it-IT", timezone_id="Europe/Rome", service_workers="block")
            ctx.route(re.compile(r"https://(fonts\.(googleapis|gstatic)|www\.gstatic)\.com/.*"), lambda r: r.abort())
            pg = ctx.new_page(); tag = f"{chi}-{w}-{tema}"
            pg.on("pageerror", lambda e, tag=tag: report["errori_js"].append({"dove": tag, "errore": str(e)[:300]}))
            pg.on("console", lambda m, tag=tag: m.type == "error" and "fonts.g" not in m.text and "gstatic" not in m.text and "ERR_FAILED" not in m.text and report["errori_js"].append({"dove": tag, "errore": "console: " + m.text[:300]}))
            pg.goto(base + "blank.txt")
            auth = {"users": users, "current": who[chi]}
            pg.evaluate("([db, auth, mode]) => { localStorage.clear(); localStorage.setItem('turni-demo-db', JSON.stringify(db)); localStorage.setItem('turni-demo-auth', JSON.stringify(auth)); localStorage.setItem('ui-mode', mode); }",
                        [db, auth, "light" if tema == "sfondo" else tema])
            if tema == "sfondo" and bg:
                import base64
                pg.evaluate("u => { localStorage.setItem('ui-bg', u); localStorage.setItem('ui-bg-l', '.35'); }", "data:image/jpeg;base64," + base64.b64encode(open(bg, "rb").read()).decode())
            for sc in screens:
                route = sc.split("-")[0] if sc != "login" else ""
                t0 = time.time()
                pg.goto(base + ("#" + route if route else ""));
                try:
                    pg.wait_for_function("() => !document.querySelector('#scr-boot') || document.querySelector('#scr-boot').hidden", timeout=8000)
                except Exception: report["problemi"].append({"tipo": "l'app non si apre", "dove": tag + " " + sc})
                if route == "me":
                    try: pg.wait_for_selector("#scr-me .me-hero", timeout=6000); report["tempi"].append({"dove": tag, "ms": round((time.time() - t0) * 1000)})
                    except Exception: report["problemi"].append({"tipo": "la mia area non si apre", "dove": tag})
                pg.wait_for_timeout(700)
                try:
                    if sc in ("me-prossimo", "me-frecce", "me-passato"):
                        pg.click("#scr-me .next-c"); pg.wait_for_timeout(500)
                        if not pg.locator("#scr-me .me-dnav").count(): report["problemi"].append({"tipo": "frecce dei giorni non comparse", "dove": tag})
                        if not pg.locator("#scr-me .today-fab").count(): report["problemi"].append({"tipo": "tasto Torna a oggi mancante", "dove": tag})
                    if sc == "me-frecce":
                        for _ in range(3): pg.click("#scr-me .me-dnav [data-act=me-dnext]"); pg.wait_for_timeout(250)
                    if sc == "me-passato":
                        for _ in range(4): pg.click("#scr-me .me-dnav [data-act=me-dprev]"); pg.wait_for_timeout(250)
                    pg.evaluate("() => window.scrollTo(0, 0)"); pg.wait_for_timeout(200)
                except Exception as e:
                    report["problemi"].append({"tipo": "azione non riuscita", "dove": f"{tag} {sc}", "dettaglio": str(e)[:200]})
                issues = pg.evaluate(AUDIT_JS)
                for it in issues: it["schermata"] = f"{tag} {sc}"; report["problemi"].append(it)
                f = os.path.join(shots, f"{tag}-{sc}.png"); pg.screenshot(path=f, full_page=True); report["schermate"].append(f)
                if sc in ("me-prossimo", "me-frecce", "me-passato"):
                    pg.click("#scr-me .today-fab") if pg.locator("#scr-me .today-fab").count() else None
            ctx.close()
        b.close()
    srv.shutdown()
    # problemi uguali su più schermate: li conto una volta
    seen, uniq = {}, []
    for it in report["problemi"]:
        k = (it.get("tipo"), it.get("dove"), it.get("testo"))
        if k in seen: seen[k]["volte"] += 1; continue
        it["volte"] = 1; seen[k] = it; uniq.append(it)
    report["problemi"] = uniq
    slow = [t for t in report["tempi"] if t["ms"] > 2500]
    for t in slow: report["problemi"].append({"tipo": "apertura lenta (in locale)", "dove": t["dove"], "dettaglio": f"{t['ms']} ms"})
    json.dump(report, open(os.path.join(out, "report.json"), "w"), ensure_ascii=False, indent=1)
    md = [f"# Controllo Turni Arese · {report['data']} · versione {report['versione']}", "",
          f"Errori JavaScript: {len(report['errori_js'])}  ·  Problemi: {len(report['problemi'])}  ·  Schermate: {len(report['schermate'])}",
          f"Pesi: " + ", ".join(f"{k} {v // 1024 if v else '?'} KB" for k, v in report["pesi"].items()),
          "Nota: i font di Google non si scaricano nel controllo, quindi i testi usano un font di riserva un po' più largo.",
          f"Apertura in locale (ms): " + ", ".join(f"{t['dove']} {t['ms']}" for t in report["tempi"]), ""]
    for e in report["errori_js"][:30]: md.append(f"- ERRORE JS [{e['dove']}]: {e['errore']}")
    for it in report["problemi"][:80]:
        md.append(f"- {it.get('tipo')} [{it.get('schermata', it.get('dove', ''))}] {it.get('dove', '') if it.get('schermata') else ''} {('«' + it['testo'] + '»') if it.get('testo') else ''} {it.get('dettaglio', '')} {('×' + str(it['volte'])) if it.get('volte', 1) > 1 else ''}")
    open(os.path.join(out, "report.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md[:5])); print(f"Report: {os.path.join(out, 'report.md')}")
    try:  # provini: tutte le schermate rimpicciolite in due fogli, per guardarle in un colpo d'occhio
        from PIL import Image
        tel = [f for f in report["schermate"] if "-1366-" not in f and "-768-" not in f]; pc = [f for f in report["schermate"] if f not in tel]
        for nome, fs, w in (("provini-telefono.png", tel, 390), ("provini-pc.png", pc, 1366)):
            if not fs: continue
            ims = [Image.open(f) for f in fs]; H = 1500 if w == 390 else 1100; per = 6 if w == 390 else 3
            ims = [i.crop((0, 0, i.width, min(i.height, H))) for i in ims]
            cols = min(per, len(ims)); rows = (len(ims) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * (w + 20), rows * (H + 20)), "white")
            for k, i in enumerate(ims): sheet.paste(i, ((k % cols) * (w + 20), (k // cols) * (H + 20)))
            sc = 0.5 if w == 390 else 0.35; sheet = sheet.resize((int(sheet.width * sc), int(sheet.height * sc)))
            sheet.save(os.path.join(out, nome)); print("Provini:", os.path.join(out, nome))
    except Exception as e: print("provini non creati:", e)
    shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
