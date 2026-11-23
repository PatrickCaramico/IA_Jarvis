// V8.12: a janela do Spotify da central fica sempre visível (antes sumia quando nada tocava ou o Spotify
// estava desconectado, e não dava para saber onde ela tinha ido). Parte pura, testada (node --test frontend/tests).

/** O que mostrar quando não há faixa tocando ou pausada: { head, title, sub, action } ("connect" | "play" | "retry"). */
export function standbyView(track) {
  const state = track?.state;
  if (state === "off") {
    return { head: "SPOTIFY · DESCONECTADO", title: "Spotify não conectado", sub: "Conecte para ver e controlar a música aqui.", action: "connect" };
  }
  if (state === "idle") {
    return { head: "SPOTIFY · EM SILÊNCIO", title: "Nada tocando agora", sub: "Toque ▶ ou peça uma música.", action: "play" };
  }
  if (state === "away") {
    return { head: "SPOTIFY · PC SEM SINAL", title: "Sem notícias do PC", sub: "A música aparece aqui quando o JARVIS do PC estiver ligado.", action: "none" };
  }
  return { head: "SPOTIFY · SEM SINAL", title: "Não consegui falar com o Spotify", sub: "Pode ser a internet ou o login dele.", action: "retry" };
}

/** Há faixa para o cartão completo (com capa, barra e tempos)? */
export function hasTrack(track) {
  return track?.state === "playing" || track?.state === "paused";
}

// V8.12.2: central no site (modo nuvem): a música vem do PC a cada sincronização (~1 min). Velha demais = PC sem
// sinal; tocando, o tempo da faixa anda desde a última notícia (sem passar do fim).
export const CLOUD_STALE_S = 3 * 60;

export function cloudTrack(tocando, nowSec = Date.now() / 1000) {
  if (!tocando || typeof tocando !== "object") return { state: "away" };
  const age = nowSec - Number(tocando.at || 0);
  if (!(age >= 0 && age <= CLOUD_STALE_S)) return { state: "away" };
  if (tocando.state !== "playing") return { ...tocando };
  const duration = Number(tocando.duration_ms) || 0;
  const progress = Math.min(duration || Infinity, (Number(tocando.progress_ms) || 0) + age * 1000);
  return { ...tocando, progress_ms: Math.round(progress) };
}
