// V8.12.3: tela "RECONECTANDO AO SEU JARVIS" com o estado de verdade (há quanto tempo procura, quantas tentativas,
// quando é a próxima) e se este PC está no "sempre ligado". Antes ela só dizia "assim que responder, eu entro"
// e não dava para saber se estava mesmo tentando ou travada.
// Nada aqui é segredo: guarda só se o PC liga sozinho (vem do /api/health).

const KEY_ALWAYS_ON = "jarvis.alwaysOn";

export function rememberAlwaysOn(value) {
  try {
    localStorage.setItem(KEY_ALWAYS_ON, value ? "1" : "0");
  } catch {
    /* aba anônima: segue sem lembrar */
  }
}

// V9.4.1: quanto o PC levou para ligar o JARVIS da última vez (do /api/health "startup"), para a tela de reconexão
// mostrar onde está a demora: no Windows até o JARVIS começar, ou no próprio JARVIS até responder.
const KEY_STARTUP = "jarvis.lastStartup";

export function rememberStartup(info) {
  if (!info || typeof info !== "object" || info.process_to_ready_s == null) return;
  try {
    localStorage.setItem(KEY_STARTUP, JSON.stringify({
      windows_to_process_s: info.windows_to_process_s ?? null,
      process_to_ready_s: info.process_to_ready_s,
      ready_at: info.ready_at || "",
    }));
  } catch {
    /* aba anônima: segue sem lembrar */
  }
}

export function knownStartup() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY_STARTUP) || "null");
    return v && typeof v === "object" ? v : null;
  } catch {
    return null;
  }
}

/** "Windows → JARVIS: 48 s · JARVIS pronto em 3 s" (ou só a 2ª parte, quando o PC já estava ligado). */
export function startupText(info) {
  if (!info || info.process_to_ready_s == null) return "";
  const ready = `JARVIS pronto em ${formatElapsed(info.process_to_ready_s * 1000)}`;
  return info.windows_to_process_s != null ? `Windows até o JARVIS: ${formatElapsed(info.windows_to_process_s * 1000)} · ${ready}` : ready;
}

// true | false | null (nunca soube)
export function knownAlwaysOn() {
  let raw = null;
  try {
    raw = localStorage.getItem(KEY_ALWAYS_ON);
  } catch {
    return null;
  }
  return raw === "1" ? true : raw === "0" ? false : null;
}

// "8 s", "1 min 20 s", "2 h 05 min"
export function formatElapsed(ms) {
  const s = Math.max(0, Math.floor((Number(ms) || 0) / 1000));
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  if (m < 60) return s % 60 ? `${m} min ${s % 60} s` : `${m} min`;
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min`;
}

// Frase curta embaixo do título, conforme o que está acontecendo.
export function reconnectHint({ launchState = "", alwaysOn = null, elapsedMs = 0 } = {}) {
  if (launchState === "opening") return "Ligando o JARVIS do PC… pode levar 1 ou 2 minutos.";
  if (launchState === "asked") return "O Chrome perguntou se pode abrir o programa? Clique em Abrir.";
  if (alwaysOn && elapsedMs > 5 * 60_000) {
    return "O PC deve estar desligado ou sem internet. Quando ele ligar, o JARVIS sobe sozinho e eu entro.";
  }
  // V9.5.2: demorando: diz o que está acontecendo no PC (antes a mesma frase ficava minutos na tela)
  if (alwaysOn && elapsedMs > 90_000) {
    return "Está demorando mais que o normal. O PC confere o motivo sozinho, instala o que faltar e religa o JARVIS; eu entro assim que ele responder.";
  }
  if (alwaysOn) return "Este PC liga o JARVIS sozinho. Assim que ele responder, eu entro.";
  return "Assim que o JARVIS do PC responder, eu entro sozinho.";
}

// 0 a 1: quanto falta para a próxima conferência (a barrinha embaixo do status)
export function nextCheckProgress(now, lastAt, nextAt) {
  if (!nextAt || !lastAt || nextAt <= lastAt) return 0;
  return Math.min(1, Math.max(0, (now - lastAt) / (nextAt - lastAt)));
}
