// V8.11.1: centro da central renovado (linha de estado, telemetria em volta do reator e legenda do microfone).
// Partes puras, testadas (node --test frontend/tests).

/** Segundos decorridos como texto curto: 4 -> "4 s", 75 -> "1 min 15 s". */
export function elapsedText(sec) {
  const s = Math.max(0, Math.floor(Number(sec) || 0));
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return r ? `${m} min ${r} s` : `${m} min`;
}

// A partir daqui o "pensando" vira um convite para cancelar (a IA tem prazo no backend, mas a tela não pode
// parecer travada: antes ficava "PROCESSANDO" piscando sem dizer nada).
export const SLOW_AFTER_S = 25;

/**
 * O que a linha abaixo do estado diz: { text, tone, cancel }.
 * tone: "idle" | "listen" | "work" | "slow" | "talk"; cancel: mostra o botão de cancelar.
 */
export function stateHint({ state = "idle", listening = false, interim = "", elapsed = 0, micOk = true, doing = "" } = {}) {
  if (listening) {
    const said = String(interim || "").trim();
    return { text: said ? `“${said.length > 70 ? `${said.slice(0, 69)}…` : said}”` : "Pode falar, senhor. Estou ouvindo.", tone: "listen", cancel: false };
  }
  if (state === "processing") {
    // V9.1.2: diz COM O QUÊ está ocupado (vem do PC: "pensando com a inteligência artificial", "esperando o pedido
    // anterior terminar", o nome da habilidade…). Antes era só "Pensando…" e "Está demorando", sem motivo.
    const what = String(doing || "").trim();
    const label = what ? what.charAt(0).toUpperCase() + what.slice(1) : "Pensando";
    if (elapsed >= SLOW_AFTER_S) {
      return { text: `Está demorando (${elapsedText(elapsed)})${what ? `: ${what}` : ""}. Pode cancelar e pedir de novo.`, tone: "slow", cancel: true };
    }
    return { text: elapsed >= 1 ? `${label}… ${elapsedText(elapsed)}` : `${label}…`, tone: "work", cancel: true };
  }
  if (state === "speaking") return { text: "Respondendo. Toque em parar para interromper.", tone: "talk", cancel: true };
  return {
    text: micOk ? "Toque no microfone ou aperte espaço para falar." : "Digite seu pedido no canal ao lado.",
    tone: "idle",
    cancel: false,
  };
}

/** Legenda embaixo do botão do microfone. */
export function micCaption({ listening = false, state = "idle" } = {}) {
  if (listening) return "OUVINDO · TOQUE P/ ENVIAR";
  if (state === "processing") return "AGUARDE";
  if (state === "speaking") return "FALANDO";
  return "FALAR";
}

/** Próximo compromisso numa linha: { when, title } ou null. */
export function nextAgenda(items) {
  const it = (items || []).find((i) => i && (i.title || i.label));
  if (!it) return null;
  const title = String(it.title || "Compromisso");
  return { when: String(it.label || "").trim() || "Em breve", title: title.length > 28 ? `${title.slice(0, 27)}…` : title };
}

/** Disco livre: 412.3 -> "412 GB"; 1536 -> "1,5 TB". */
export function diskText(gb) {
  if (gb === null || gb === undefined || gb === "") return "—";
  const v = Number(gb);
  if (!Number.isFinite(v)) return "—";
  return v >= 1000 ? `${(v / 1024).toFixed(1).replace(".", ",")} TB` : `${Math.round(v)} GB`;
}

/**
 * V9.4.5: o menu que abre ao tocar numa leitura em volta do reator (processador, memória, disco, próximo).
 * Puro: devolve o título, o valor, as linhas e as ações; o componente só desenha e executa.
 * Ação: { id, icon, label, command } (frase para o JARVIS) ou { id, icon, label, event } (evento da central).
 */
export function telemetryMenu(kind, sys = {}, agenda = []) {
  const s = sys || {};
  const temp = typeof s.temperature === "number" ? `${s.temperature} °C` : null;
  const heavy = { id: "heavy", icon: "🔎", label: "O QUE ESTÁ PESANDO?", command: "o que está pesando no pc" };
  const analyze = { id: "analyze", icon: "⚡", label: "AUTO-ANÁLISE", command: "faz uma auto análise" };
  const scan = { id: "scan", icon: "🧹", label: "VARREDURA COMPLETA", event: "pc-scan" };
  if (kind === "cpu" || kind === "ram") {
    const v = kind === "cpu" ? s.cpu_percent : s.ram_percent;
    const n = Number(v);
    const note = !Number.isFinite(n) ? "Sem leitura agora." : n >= 90 ? "Muito alto: vale ver o que está pesando."
      : n >= 70 ? "Alto: algum programa está exigindo." : "Tranquilo.";
    return {
      title: kind === "cpu" ? "PROCESSADOR" : "MEMÓRIA",
      value: Number.isFinite(n) ? `${Math.round(n)}%` : "—",
      bar: Number.isFinite(n) ? Math.min(100, Math.max(0, n)) : null,
      note,
      rows: [
        ["Programas e processos", s.processes != null ? String(s.processes) : null],
        ["Temperatura", temp],
        [kind === "cpu" ? "Memória" : "Processador", Number.isFinite(Number(kind === "cpu" ? s.ram_percent : s.cpu_percent))
          ? `${Math.round(Number(kind === "cpu" ? s.ram_percent : s.cpu_percent))}%` : null],
      ].filter(([, val]) => val),
      actions: [heavy, analyze, scan],
    };
  }
  if (kind === "disk") {
    const gb = Number(s.disk_free_gb);
    return {
      title: "DISCO LIVRE",
      value: diskText(s.disk_free_gb),
      bar: null,
      note: !Number.isFinite(gb) ? "Sem leitura agora." : gb < 15 ? "Pouco espaço: vale limpar temporários e a lixeira." : "Espaço de sobra.",
      rows: [],
      actions: [{ ...scan, label: "VER O QUE DÁ PARA LIMPAR" }, analyze],
    };
  }
  // próximo compromisso
  const items = (agenda || []).filter((i) => i && (i.title || i.label)).slice(0, 3);
  return {
    title: "PRÓXIMOS",
    list: true, // V9.4.6: hora em cima e o título embaixo, quebrando linha (títulos longos passavam da borda)
    value: items[0] ? String(items[0].label || "").trim() || "Em breve" : "Nada marcado",
    bar: null,
    note: items.length ? null : "Nenhum compromisso ou lembrete pendente.",
    rows: items.map((i) => [String(i.label || "").trim() || "Em breve", `${i.kind === "lembrete" ? "⏰ " : "📅 "}${i.title || "Compromisso"}`]),
    actions: [
      { id: "reminder", icon: "⏰", label: "NOVO LEMBRETE", event: "new-reminder" },
      { id: "agenda", icon: "📅", label: "MINHA AGENDA", command: "minha agenda" },
    ],
  };
}
