/*
  CONFIGURAZIONE DI FIREBASE
  ---------------------------
  Dati del progetto Firebase "turni-arese" (Impostazioni progetto › Le tue app › Turni Arese).
  Se "apiKey" fosse vuoto, l'app funzionerebbe in MODALITÀ PROVA: i dati resterebbero solo sul dispositivo.
  Questi valori non sono segreti: Firebase li prevede pubblici. La sicurezza la fanno le regole (firestore.rules).
*/
window.TURNI_CONFIG = {
  firebase: {
    apiKey: "AIzaSyAxBpUlLzv0DpVwD3dPR3UgnwE1EhiQYkQ",
    authDomain: "turni-arese.firebaseapp.com",
    projectId: "turni-arese",
    storageBucket: "turni-arese.firebasestorage.app",
    messagingSenderId: "930667721139",
    appId: "1:930667721139:web:0dffac89462d8545591bc6"
  },
  /* servizio che invia le notifiche "Nuovi turni caricati" (Cloudflare Worker, codice in push-worker.js) */
  push: "https://turni-push.turni-arese.workers.dev/"
};
