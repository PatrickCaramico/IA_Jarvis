import { useState, useEffect } from "react";
import { startPolling } from "../hooks/usePolling.js";

// Mostra, em tempo real, o que o backend está fazendo.
// status de cada etapa: "pending" | "active" | "done" | "error"

export const STEP_DEFS = [
  { key: "camera", label: "Câmera ativa", hint: "Capturando imagem" },
  { key: "news", label: "Buscando notícias", hint: "Google News Brasil" },
  { key: "llm", label: "Analisando contexto", hint: "Imagem + notícias + IA" },
  { key: "tts", label: "Sintetizando voz", hint: "Português do Brasil" },
];

const SERVICE_DEFS = [
  ["ai", "IA"],
  ["microphone", "Microfone"],
  ["camera", "Câmera"],
  ["internet", "Internet"],
  ["backend", "Backend"],
];

function Indicator({ status }) {
  if (status === "active") {
    return (
      <span className="relative flex h-3 w-3">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-arc-300 opacity-70" />
        <span className="relative inline-flex h-3 w-3 rounded-full bg-arc-300" />
      </span>
    );
  }
  if (status === "done") {
    return <span className="h-3 w-3 rounded-full bg-arc-400 shadow-[0_0_8px_#1fc2f5]" />;
  }
  if (status === "error") {
    return <span className="h-3 w-3 rounded-full bg-red-500 shadow-[0_0_8px_#ef4444]" />;
  }
  return <span className="h-3 w-3 rounded-full border border-arc-700" />;
}

export default function StatusPanel({ steps, connected, services = {}, api }) {
  const [quota, setQuota] = useState({ allowed: false, count: 0, limit: 5 });
  const [searchMode, setSearchMode] = useState("browser");
  const [cooldown, setCooldown] = useState({ active: false, remaining: 0 });

  useEffect(() => {
    if (!api) return;
    const fetchQuota = () => {
      api("/api/search/quota")
        .then((q) => {
          if (q) setQuota(q);
        })
        .catch(() => {});
      api("/api/prefs")
        .then((p) => {
          if (p?.search_mode) setSearchMode(p.search_mode);
          if (p?.deep_search_quota) setQuota(p.deep_search_quota);
          if (p?.ai_cooldown) setCooldown(p.ai_cooldown);
        })
        .catch(() => {});
    };
    return startPolling(fetchQuota, 10000); // era 5 s; pausa com a aba oculta
  }, [api]);

  return (
    <section className="hud-panel p-3.5" aria-label="Status do sistema">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-display text-xs tracking-wide text-arc-200">Sistema</h2>
        <span className="flex items-center gap-1.5 text-xs">
          <span className={`h-2 w-2 rounded-full ${connected ? "bg-arc-300" : "bg-red-500"}`} />
          {connected ? "Conectado" : "Desconectado"}
        </span>
      </div>

      <ul className="space-y-2">
        {STEP_DEFS.map(({ key, label, hint }) => {
          const status = steps[key] ?? "pending";
          const dim = status === "pending" ? "opacity-45" : "opacity-100";
          return (
            <li key={key} className={`flex items-center gap-2.5 transition-opacity ${dim}`}>
              <Indicator status={status} />
              <div className="leading-none">
                <p className="text-xs font-semibold">{label}</p>
                <p className="text-[11px] text-arc-300/70">
                  {status === "error" ? "Falhou — seguindo sem essa etapa" : hint}
                </p>
              </div>
            </li>
          );
        })}
      </ul>

      {/* Indicador de Pesquisa e Cota de IA */}
      <div className="mt-3.5 border-t border-arc-700/60 pt-2.5">
        <p className="mb-1.5 font-display text-[10px] tracking-widest text-arc-300/60">MODO DE PESQUISA & COTA</p>
        <div className="flex flex-col gap-1 text-[11px] font-mono">
          <div className="flex items-center justify-between rounded bg-black/40 px-2 py-1 border border-arc-700/40">
            <span className="text-arc-300/70">Pesquisa:</span>
            <span className="font-semibold text-arc-200 uppercase">
              {searchMode === "browser" ? "Navegador" : searchMode === "ask" ? "Perguntar" : "API"}
            </span>
          </div>
          <div className="flex items-center justify-between rounded bg-black/40 px-2 py-1 border border-arc-700/40">
            <span className="text-arc-300/70">Profunda:</span>
            <span className={quota.allowed ? "font-semibold text-cyan-300" : "font-semibold text-amber-400"}>
              {quota.allowed ? "liberada" : "bloqueada"} ({quota.count}/{quota.limit} hoje)
            </span>
          </div>
          {cooldown.active && (
            <div className="flex items-center justify-between rounded bg-amber-950/40 px-2 py-1 border border-amber-500/50 text-amber-300">
              <span className="flex items-center gap-1.5 font-semibold">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400" />
                </span>
                Cooldown IA (429):
              </span>
              <span className="font-bold text-amber-200">{cooldown.remaining}s</span>
            </div>
          )}
        </div>
      </div>

      <div className="mt-3.5 border-t border-arc-700/60 pt-2.5">
        <p className="mb-1.5 font-display text-[10px] tracking-widest text-arc-300/60">DIAGNÓSTICO</p>
        <div className="grid grid-cols-2 gap-1.5">
          {SERVICE_DEFS.map(([key, label]) => {
            const isAiInCooldown = key === "ai" && cooldown.active;
            const online = key === "backend" ? connected && services[key] !== false : services[key] === true;
            if (isAiInCooldown) {
              return (
                <span key={key} className="rounded border px-2 py-1 text-[10px] border-amber-400/50 text-amber-300 bg-amber-950/20">
                  ● {label} ({cooldown.remaining}s)
                </span>
              );
            }
            return <span key={key} className={`rounded border px-2 py-1 text-[10px] ${online ? "border-emerald-400/40 text-emerald-300" : "border-red-400/40 text-red-300"}`}>{online ? "●" : "○"} {label}</span>;
          })}
        </div>
      </div>
    </section>
  );
}
