import { useEffect, useState } from "react";

// V4.4: partida do Modo Torcedor (agenda real ESPN + Google Notícias, sem IA).
// Atualiza a cada 30 s com a bola rolando ou perto do jogo, e a cada 2 min no resto do tempo.
// Pausa com a aba escondida. `refreshKey` força uma nova leitura (ex.: depois de um gol).
export default function useFanMatch(api, enabled = true, refreshKey = 0) {
  const [data, setData] = useState({ match: null, team: null, upcoming: [] });

  useEffect(() => {
    if (!enabled || !api) return undefined;
    let active = true;
    let timer;
    const tick = async () => {
      let next = 120_000;
      if (!document.hidden) {
        try {
          const res = await api("/api/fan/match");
          if (active && res?.match) {
            setData({ match: res.match, team: res.team || null, upcoming: res.upcoming || [] });
            const soon = res.match.status === "scheduled" && res.match.time_known && res.match.seconds_until_match < 1800;
            if (res.match.status === "live" || soon) next = 30_000;
          }
        } catch {
          /* sem backend: tenta de novo depois */
        }
      }
      if (active) timer = setTimeout(tick, next);
    };
    tick();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [api, enabled, refreshKey]);

  return data;
}

// "Palmeiras 1 x 0 Remo" respeitando quem é mandante.
export function matchSides(match, teamName = "Palmeiras") {
  const weAreHome = match?.home_away !== "away";
  return {
    home: weAreHome ? teamName : match.opponent,
    away: match ? (weAreHome ? match.opponent : teamName) : "",
    homeScore: match?.score?.home ?? 0,
    awayScore: match?.score?.away ?? 0,
    weAreHome,
    homeLogoSide: weAreHome ? "ours" : "theirs",
    awayLogoSide: weAreHome ? "theirs" : "ours",
    homeLabel: "MANDANTE",
    awayLabel: "VISITANTE",
  };
}

// Escudo servido pelo backend (porta 8000), não pela interface. `base` é o API_URL e `token` vai só
// quando existe (celular); o backend aceita o token pela query, como nas outras imagens.
export function matchLogoUrl(match, side, { base = "", token = "" } = {}) {
  const query = new URLSearchParams({ v: String(match?.id ?? "") });
  if (token) query.set("token", token);
  return `${base}/api/fan/logo/${side}?${query.toString()}`;
}

export function matchTime(match) {
  if (!match?.time_known) return "horário a confirmar";
  try {
    return new Date(match.date).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });
  } catch {
    return "";
  }
}
