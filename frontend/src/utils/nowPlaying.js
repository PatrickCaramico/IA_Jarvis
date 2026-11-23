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
  return { head: "SPOTIFY · SEM SINAL", title: "Não consegui falar com o Spotify", sub: "Pode ser a internet ou o login dele.", action: "retry" };
}

/** Há faixa para o cartão completo (com capa, barra e tempos)? */
export function hasTrack(track) {
  return track?.state === "playing" || track?.state === "paused";
}
