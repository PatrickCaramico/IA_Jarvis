// V5.5: fala NESTE aparelho (celular ou navegador), não na caixa de som do PC.
// Pede ao PC o MP3 da voz do JARVIS (POST /api/tts, com a chave de acesso) e toca aqui.
// Uma fala por vez: começar outra (ou tocar de novo no 🔊) para a anterior.
import { API_URL, getJarvisToken } from "./api.js";

let current = null; // { audio, url, id }
const listeners = new Set();

function notify() {
  const id = current?.id ?? null;
  listeners.forEach((fn) => {
    try {
      fn(id);
    } catch {
      /* ouvinte quebrado não derruba os outros */
    }
  });
}

// Avisa quem está falando agora (id da mensagem) para o botão 🔊 mudar para ■
export function onSpeakingChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function stopHere() {
  if (!current) return;
  try {
    current.audio.pause();
  } catch {
    /* já parado */
  }
  URL.revokeObjectURL(current.url);
  current = null;
  notify();
}

export function speakingId() {
  return current?.id ?? null;
}

let stopGen = 0; // V6.5.3: muda a cada "pular/cancelar": uma voz que ainda estava baixando não toca

export async function speakHere(text, id = "x") {
  stopHere();
  const clean = String(text || "").trim();
  if (!clean) return;
  const gen = stopGen;
  const token = getJarvisToken();
  const res = await fetch(`${API_URL}/api/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { "X-Jarvis-Token": token } : {}) },
    body: JSON.stringify({ text: clean }),
  });
  if (!res.ok) throw new Error("Não consegui gerar a voz agora.");
  const blob = await res.blob();
  if (gen !== stopGen) return; // pularam ou cancelaram enquanto a voz baixava
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  const mine = { audio, url, id };
  current = mine;
  notify();
  audio.onended = () => {
    if (current === mine) stopHere();
  };
  await audio.play();
}

// V5.7: falas que o PC mandou para este aparelho (evento "speak_on_device"), uma depois da outra
// V6.5.1: avisa o PC quando cada fala termina (say_id), para o briefing trocar o card na hora certa
function ackPlayed(sayId) {
  if (!sayId) return;
  const token = getJarvisToken();
  fetch(`${API_URL}/api/tts/played`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { "X-Jarvis-Token": token } : {}) },
    body: JSON.stringify({ say_id: sayId }),
  }).catch(() => { /* o PC segue pelo tempo estimado */ });
}

const queue = [];
let draining = false;
let playingSayId = null;

// V6.5.3: "pular" cala só a fala indicada; "cancelar" (sem id) cala tudo e esvazia a fila
export function stopSpeech(sayId = null) {
  if (sayId) {
    for (let i = queue.length - 1; i >= 0; i -= 1) if (queue[i].sayId === sayId) queue.splice(i, 1);
    if (playingSayId === sayId) {
      stopGen += 1;
      stopHere();
    }
    return;
  }
  queue.length = 0;
  stopGen += 1;
  stopHere();
}
export function enqueueHere(text, sayId = null) {
  queue.push({ text, sayId });
  if (draining) return;
  draining = true;
  (async () => {
    while (queue.length) {
      const next = queue.shift();
      playingSayId = next.sayId;
      try {
        await speakHere(next.text, `q${Date.now()}`);
        await new Promise((resolve) => {
          const a = current?.audio;
          if (!a || a.ended || a.paused) { resolve(); return; }
          a.addEventListener("ended", resolve, { once: true });
          a.addEventListener("pause", resolve, { once: true });
        });
      } catch {
        /* sem voz agora: segue para a próxima */
      }
      playingSayId = null;
      ackPlayed(next.sayId);
    }
    draining = false;
  })();
}
export function clearQueue() {
  queue.length = 0;
}

// Preferência deste aparelho: ler as respostas em voz alta automaticamente (alto-falante do chat)
const KEY = "jarvis.chat.speaker";
export function speakerOn() {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}
export function setSpeakerOn(on) {
  try {
    localStorage.setItem(KEY, on ? "1" : "0");
  } catch {
    /* sem armazenamento: vale só nesta sessão */
  }
}
