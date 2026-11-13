// Função do Netlify que serve o modo nuvem do JARVIS em /api/cloud/* (lógica em ../nuvem/core.mjs).
import { getStore } from "@netlify/blobs";
import { handle } from "../nuvem/core.mjs";

function blobStore() {
  const store = getStore({ name: "jarvis-nuvem", consistency: "strong" });
  return {
    get: (key) => store.get(key, { type: "json" }),
    set: (key, value) => store.setJSON(key, value),
  };
}

export default async (req) => handle(req, { store: blobStore(), env: process.env });

export const config = { path: "/api/cloud/*" };
