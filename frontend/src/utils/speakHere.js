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

export async function speakHere(text, id = "x") {
  stopHere();
  const clean = String(text || "").trim();
  if (!clean) return;
  const token = getJarvisToken();
  const res = await fetch(`${API_URL}/api/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { "X-Jarvis-Token": token } : {}) },
    body: JSON.stringify({ text: clean }),
  });
  if (!res.ok) throw new Error("Não consegui gerar a voz agora.");
  const blob = await res.blob();
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
