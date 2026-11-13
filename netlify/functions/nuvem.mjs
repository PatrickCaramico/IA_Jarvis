// Função do Netlify que serve o modo nuvem do JARVIS em /api/cloud/* (lógica em ../nuvem/core.mjs).
import { getStore } from "@netlify/blobs";
import { MsEdgeTTS, OUTPUT_FORMAT } from "msedge-tts";
import { handle } from "../nuvem/core.mjs";

function blobStore() {
  const store = getStore({ name: "jarvis-nuvem", consistency: "strong" });
  return {
    get: (key) => store.get(key, { type: "json" }),
    set: (key, value) => store.setJSON(key, value),
  };
}

// V6.6.9: mesma voz e mesmo formato do PC (edge-tts: audio-24khz-48kbitrate-mono-mp3)
async function synth(text, voice) {
  const tts = new MsEdgeTTS();
  await tts.setMetadata(voice.name, OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);
  const escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const { audioStream } = tts.toStream(escaped, { rate: voice.rate, pitch: voice.pitch });
  const chunks = [];
  await new Promise((resolve, reject) => {
    audioStream.on("data", (c) => chunks.push(c));
    audioStream.on("end", resolve);
    audioStream.on("close", resolve);
    audioStream.on("error", reject);
  });
  tts.close();
  if (!chunks.length) throw new Error("A voz não respondeu.");
  return Buffer.concat(chunks);
}

export default async (req) => handle(req, { store: blobStore(), env: process.env, synth });

export const config = { path: "/api/cloud/*" };
