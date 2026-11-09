# Turni Arese

App per il telefono e per il PC del banco, senza account Claude e senza abbonamenti.

- **Balordi (colleghi)**: entrano con nome, cognome e password (così due colleghi con lo stesso nome non si confondono) e vedono solo la loro area. La loro area mostra i turni, la settimana, il monte ore e gli appuntamenti del Service che cadono nel loro turno. Poi c'è l'ingranaggio con tema, ore da contratto, foto profilo, password ed esci.
- **Responsabile (tu)**: la tua area, l'agenda, il caricamento delle foto degli orari e la gestione degli accessi.
- **PC del banco**: solo l'agenda, collegato con un codice postazione.

Tutto è gratuito:
- l'app sta su **GitHub Pages**;
- i dati stanno su **Firebase**, piano gratuito Spark, senza carta di credito;
- le foto dei fogli le legge **Gemini**, con una chiave gratuita di Google AI Studio.

Tempo per attivarla: circa 20 minuti, una volta sola.

---

## 1. Firebase (il database)

**Già fatto il 9 novembre 2026** sul progetto `turni-arese`: accesso con email/password attivo, dominio `gteam8998.github.io` autorizzato, database Firestore in Europa (`eur3`) con le regole di `firestore.rules` pubblicate, app web "Turni Arese" registrata e i suoi dati già scritti in `firebase-config.js`. I passi qui sotto servono solo se un giorno lo rifai da capo.

1. Apri <https://console.firebase.google.com> con il tuo account Google e premi **Crea un progetto**.
   - Nome: `turni-arese`.
   - Google Analytics: disattivalo, non serve.
2. Nel menu a sinistra apri **Build › Authentication** e premi **Inizia**.
   - Nella scheda **Metodo di accesso** scegli **Email/password**, attiva solo il primo interruttore e premi **Salva**.
   - Nella scheda **Impostazioni › Domini autorizzati** premi **Aggiungi dominio** e scrivi `gteam8998.github.io`.
3. Apri **Build › Firestore Database** e premi **Crea database**.
   - Posizione: una europea, per esempio `eur3 (europe)`.
   - Modalità: **produzione**.
   - Quando è pronto, apri la scheda **Regole**, cancella tutto, incolla il contenuto del file `firestore.rules` e premi **Pubblica**.
4. Premi l'ingranaggio in alto a sinistra e poi **Impostazioni progetto**.
   - In fondo, in "Le tue app", premi l'icona **`</>`** (Web), scrivi un nome qualsiasi e premi **Registra app**. Firebase Hosting non serve.
   - Compare un blocco `const firebaseConfig = { apiKey: "...", ... }`.
5. Copia quei sei valori nel file `firebase-config.js`, al posto delle virgolette vuote.
   - Oppure manda il blocco a Claude e lo mette lui. Non sono dati segreti: la sicurezza la fanno le regole del punto 3.

## 2. GitHub Pages (l'indirizzo dell'app)

1. Su <https://github.com/new>, con l'account `gteam8998`, crea un repository di nome `turni`, **Public**.
2. Premi **Add file › Upload files** e trascina tutti i file di questa cartella:
   - `index.html`, `firebase-config.js`, `sw.js`, `manifest.webmanifest`, `firestore.rules`, `LEGGIMI.md`;
   - la cartella `icons`.
   - **Non** caricare il file `backup-turni-….json`, perché contiene nomi e turni e il repository è pubblico.
3. Premi **Commit changes**.
4. Apri **Settings › Pages**. In "Branch" scegli `main` e `/ (root)`, poi premi **Save**.
5. Dopo un minuto l'app è online su **https://gteam8998.github.io/turni/**.

## 3. Prima apertura (la fai tu)

1. Apri l'indirizzo dal telefono. Compare **Prima configurazione**.
2. Scrivi nome e cognome (servono per entrare; dentro l'app ti saluta solo con il nome) e scegli una password di almeno 6 caratteri.
3. In "Backup da importare" scegli `backup-turni-2026-11-09.json`. Così ritrovi balordi e turni già letti.
4. Premi **Crea l'app ed entra**: diventi il responsabile.
5. Mettila sulla schermata Home:
   - **iPhone**: in Safari tocca **Condividi › Aggiungi alla schermata Home**.
   - **Android**: in Chrome apri il menu **⋮ › Installa app**.

## 4. La chiave di Gemini (lettura delle foto)

1. Apri <https://aistudio.google.com/apikey> e premi **Create API key**. Se te lo chiede, scegli il progetto `turni-arese`.
2. Copia la chiave (inizia con `AIza…`).
3. Nell'app apri **Impostazioni › Lettura delle foto**, incolla la chiave e premi **Salva e prova**.
   - L'app sceglie da sola il miglior modello gratuito disponibile.
   - La chiave la vede solo il responsabile.
4. Consigliato: limita la chiave al tuo sito. Su <https://console.cloud.google.com> vai in **API e servizi › Credenziali** e apri la chiave. In "Restrizioni delle applicazioni" scegli **Siti web** e aggiungi `https://gteam8998.github.io/*`.

Sul piano gratuito Google può usare le immagini inviate per migliorare i suoi servizi. Ci sono anche limiti giornalieri, circa una ventina di foto al giorno con il modello migliore. Se finiscono, l'app passa da sola a un modello più leggero.

## 5. Far entrare un collega

1. **Impostazioni › Accessi dei balordi**: accanto al suo nome scrivi **nome e cognome** e premi **Crea codice**. Il codice ha 6 cifre e vale 14 giorni.
2. Dagli il link dell'app, oppure fagli inquadrare il QR che trovi nelle impostazioni, insieme al codice.
3. Lui apre l'app, tocca **Primo accesso? Ho un codice**, scrive nome, cognome e codice e sceglie la sua password. Da lì in poi entra con nome, cognome e password.
4. **Password dimenticata?** Premi **Azzera accesso** accanto al suo nome: esce un codice nuovo.

## 6. Il PC del banco

1. **Impostazioni › PC del banco › Crea codice postazione**.
2. Sul PC apri l'app, premi **PC del negozio** e scrivi il codice. Il PC resta collegato all'agenda e non vede nessuna area personale.

## 7. Caricare gli orari

**Carica foto** (solo il responsabile) funziona così:
1. Scatta una foto o sceglila dalla galleria. Puoi metterne anche tante insieme.
2. Premi **Leggi i turni**. Gemini trascrive la tabella e l'app confronta le colonne Da/A con le celle colorate: se non tornano, segna **Da controllare** e mostra la riga sulla foto.
3. Si salvano:
   - chi è in TLC o HE;
   - i balordi già in elenco qualunque sia il reparto del giorno (TV, PE…). Nell'agenda di Telefonia e Service compaiono solo le ore TLC e HE; nella loro area vedono tutte le ore, con il reparto.
4. Controlla le schede e premi **Salva i turni**.

## 8. Limiti gratuiti (abbondanti per un reparto)

- **Firestore**: 1 GB di spazio, 50.000 letture e 20.000 scritture al giorno.
- **Gemini**: limiti al minuto e al giorno, visibili su AI Studio.
- **GitHub Pages**: gratuito per i repository pubblici.

## 9. Dati personali

- Gli appuntamenti contengono numeri di telefono dei clienti. Tienili solo il tempo necessario e non dare l'accesso a chi non lavora in reparto.
- Le foto dei fogli non vengono salvate: restano sul telefono di chi le carica.
- In caso di dubbio sui turni fa fede il foglio orari appeso in negozio.

## Per modificare l'app

Il sorgente è `sorgente/src.html`. Lancia `python3 sorgente/build.py`: rigenera la cartella `dist` da caricare su GitHub. Cambia `VER` in `build.py` a ogni versione, così i telefoni scaricano quella nuova.
