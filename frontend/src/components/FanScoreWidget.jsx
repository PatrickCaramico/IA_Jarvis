import { useEffect, useState } from "react";
import { startPolling } from "../hooks/usePolling.js";
import { matchLogoUrl, matchSides } from "../hooks/useFanMatch.js";
import { API_URL, getJarvisToken } from "../utils/api.js";

function TeamShield({ src, alt, compact = false }) {
  const [failedSrc, setFailedSrc] = useState(null);
  const errored = failedSrc === src; // volta a tentar quando o escudo (src) muda
  if (!src || errored) {
    return <span className={`inline-flex items-center justify-center rounded-full border border-emerald-400/40 bg-emerald-950/50 text-[9px] font-bold text-emerald-200 ${compact ? "w-5 h-5" : "w-7 h-7"}`} aria-label={alt || "Escudo"}>{(alt || "?").slice(0, 1)}</span>;
  }
  return <img className={`rounded-full object-contain border border-emerald-400/40 bg-emerald-950/50 ${compact ? "w-5 h-5" : "w-7 h-7"}`} src={src} alt={alt || "Escudo"} onError={() => setFailedSrc(src)} loading="lazy" referrerPolicy="no-referrer" />;
}

export default function FanScoreWidget({ api, onSend, compact = false }) {
  const [matchData, setMatchData] = useState(null);
  const [schedule, setSchedule] = useState([]);
  const [teamInfo, setTeamInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showSchedule, setShowSchedule] = useState(false);
  const [reminderMsg, setReminderMsg] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      setError("");
      const [resMatch, resSched] = await Promise.allSettled([
        api ? api("/api/fan/match") : Promise.reject(),
        api ? api("/api/fan/schedule") : Promise.reject(),
      ]);

      if (resMatch.status === "fulfilled" && resMatch.value) {
        setMatchData(resMatch.value.match || null);
        setTeamInfo(resMatch.value.team || null);
      }
      if (resSched.status === "fulfilled" && resSched.value) {
        setSchedule(resSched.value.schedule || []);
      }
    } catch {
      setError("Não foi possível obter os dados da partida.");
    } finally {
      setLoading(false);
    }
  };
  const loadMatch = loadData;

  useEffect(() => {
    return startPolling(loadData, 60000); // a cada 60 s, pausa com a aba oculta
  }, []);

  const handleCreateReminder = async (matchId) => {
    if (!api) return;
    try {
      setReminderMsg("Agendando lembrete...");
      const res = await api("/api/fan/match/reminder", {
        method: "POST",
        body: JSON.stringify({ match_id: matchId, minutes_before: 30 }),
      });
      setReminderMsg(res?.message || "Lembrete agendado!");
      setTimeout(() => setReminderMsg(""), 5000);
    } catch {
      setReminderMsg("Falha ao agendar lembrete.");
      setTimeout(() => setReminderMsg(""), 4000);
    }
  };

  if (loading && !matchData) {
    return (
      <div className="p-4 text-center text-xs text-emerald-300/60 font-['Orbitron'] animate-pulse">
        Sincronizando agenda e placar...
      </div>
    );
  }

  if (error && !matchData) {
    return (
      <div className="p-3 text-center text-xs text-emerald-400/80 font-['Orbitron']">
        <p>{error}</p>
        <button
          type="button"
          onClick={loadData}
          className="mt-2 text-[10px] underline text-emerald-300 hover:text-white"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!matchData) return null;
  if (matchData.status === "unknown") {
    return (
      <div className="p-3 text-center text-xs text-emerald-300/80 font-['Orbitron']">
        Agenda do Verdão ainda não carregou (sem internet?). Tento de novo em 1 minuto.
      </div>
    );
  }

  const isLive = matchData.status === "live";
  const isFinished = matchData.status === "finished";
  const sides = matchSides(matchData, teamInfo?.name || "Palmeiras");

  return (
    <div
      className={`rounded-lg border border-emerald-500/30 bg-emerald-950/20 backdrop-blur-md p-3 select-none text-emerald-100 ${
        compact ? "text-xs" : "text-sm p-4"
      }`}
    >
      {/* Cabeçalho da Competição */}
      <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2 mb-2">
        <div className="flex items-center gap-1.5">
          <span className="text-emerald-400 font-['Orbitron'] text-[10px] tracking-wider uppercase">
            {matchData.competition || "Campeonato"}
          </span>
          {isLive && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-500/30 border border-rose-500/50 text-rose-300 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
              AO VIVO {matchData.minute ? `· ${matchData.minute}` : ""}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={loadData}
          title="Atualizar placar"
          className="text-emerald-400/60 hover:text-emerald-200 text-xs transition"
        >
          ↻
        </button>
      </div>

      {/* Confronto e Placar */}
      <div className="flex items-center justify-around py-2">
        {/* Mandante */}
        <div className="flex flex-col items-center gap-1 text-center flex-1">
          <TeamShield src={matchLogoUrl(matchData, sides.homeLogoSide, { base: API_URL, token: getJarvisToken() })} alt={sides.home} compact={compact} />
          <span className="font-semibold text-xs tracking-wide">{sides.home}</span>
          <span className="text-[10px] text-emerald-400/60 font-['Orbitron']">
            {sides.homeLabel}
          </span>
        </div>

        {/* Placar ou VS */}
        <div className="px-3 flex flex-col items-center">
          {isLive || isFinished ? (
            <div className="flex items-center gap-2 font-['Orbitron'] text-lg font-bold text-white tracking-widest bg-black/40 px-3 py-1 rounded border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
              <span>{matchData.score?.home ?? 0}</span>
              <span className="text-emerald-400/60 text-xs">x</span>
              <span>{matchData.score?.away ?? 0}</span>
            </div>
          ) : (
            <div className="font-['Orbitron'] text-xs font-bold text-emerald-300/80 bg-black/40 px-2.5 py-1 rounded border border-emerald-500/20">
              VS
            </div>
          )}
          <span className="text-[9px] text-emerald-300/70 mt-1 font-['Orbitron'] tracking-wider">
            {matchData.countdown}
          </span>
        </div>

        {/* Visitante */}
        <div className="flex flex-col items-center gap-1 text-center flex-1">
          <TeamShield src={matchLogoUrl(matchData, sides.awayLogoSide, { base: API_URL, token: getJarvisToken() })} alt={sides.away} compact={compact} />
          <span className="font-semibold text-xs tracking-wide">{sides.away}</span>
          <span className="text-[10px] text-emerald-400/60 font-['Orbitron']">
            {sides.awayLabel}
          </span>
        </div>
      </div>

      {/* Rodapé com Estádio e Ação */}
      <div className="mt-2 pt-2 border-t border-emerald-500/20 flex flex-col gap-2">
        <div className="flex items-center justify-between text-[10px] text-emerald-300/70">
          <span>📍 {matchData.venue || "Estádio"}</span>
          <div className="flex items-center gap-2">
            {schedule.length > 0 && (
              <button
                type="button"
                onClick={() => setShowSchedule((prev) => !prev)}
                className="text-[10px] font-['Orbitron'] text-emerald-300 hover:text-white underline cursor-pointer"
              >
                {showSchedule ? "▲ OCULTAR AGENDA" : "▼ CALENDÁRIO DE JOGOS"}
              </button>
            )}
            {onSend && (
              <button
                type="button"
                onClick={() => onSend(`como está o jogo do Palmeiras?`)}
                className="hover:text-emerald-200 underline cursor-pointer"
              >
                Perguntar à IA ▸
              </button>
            )}
          </div>
        </div>

        {/* Botões de Ação para o Jogo */}
        <div className="flex items-center gap-1.5 pt-1">
          <button
            type="button"
            onClick={() => handleCreateReminder(matchData.id)}
            className="flex-1 py-1 px-2 rounded bg-emerald-500/15 hover:bg-emerald-500/30 border border-emerald-400/40 text-[9px] font-['Orbitron'] text-emerald-200 hover:text-white transition flex items-center justify-center gap-1 cursor-pointer active:scale-95"
            title="Criar lembrete no JARVIS para este jogo"
          >
            <span>⏰</span> LEMBRAR JOGO
          </button>
          {schedule.find((s) => s.id === matchData.id)?.google_calendar_url && (
            <a
              href={schedule.find((s) => s.id === matchData.id)?.google_calendar_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 py-1 px-2 rounded bg-emerald-500/15 hover:bg-emerald-500/30 border border-emerald-400/40 text-[9px] font-['Orbitron'] text-emerald-200 hover:text-white transition flex items-center justify-center gap-1 text-center"
              title="Adicionar evento no Google Calendar"
            >
              <span>📅</span> GOOGLE CALENDAR ↗
            </a>
          )}
        </div>

        {/* Mensagem de Feedback de Lembrete */}
        {reminderMsg && (
          <div className="text-[10px] text-center font-['Orbitron'] text-emerald-300 bg-emerald-950/80 p-1.5 rounded border border-emerald-400/40 animate-pulse">
            ✓ {reminderMsg}
          </div>
        )}

        {/* Lista Expandida de Próximos Jogos */}
        {showSchedule && schedule.length > 0 && (
          <div className="mt-2 flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-1 border-t border-emerald-500/20 pt-2">
            <span className="text-[9px] font-['Orbitron'] text-emerald-400/70 font-semibold tracking-wider">
              PRÓXIMOS CONFRONTOS DO VERDÃO
            </span>
            {schedule.map((item) => (
              <div
                key={item.id}
                className="p-2 rounded bg-black/40 border border-emerald-500/20 flex items-center justify-between gap-2 text-[10px]"
              >
                <div className="flex flex-col min-w-0">
                  <span className="font-semibold text-white truncate">
                    {item.home_away === "away" ? `${item.opponent} x Palmeiras` : `Palmeiras x ${item.opponent}`}
                  </span>
                  <span className="text-[9px] text-emerald-300/60 font-mono">
                    {item.competition} · {item.date_human}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleCreateReminder(item.id)}
                    className="p-1 px-1.5 rounded bg-emerald-500/20 hover:bg-emerald-500/40 border border-emerald-400/30 text-[8px] font-['Orbitron'] text-emerald-200 hover:text-white"
                    title="Agendar lembrete no JARVIS"
                  >
                    ⏰ LEMBRAR
                  </button>
                  <a
                    href={item.google_calendar_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 px-1.5 rounded bg-emerald-500/20 hover:bg-emerald-500/40 border border-emerald-400/30 text-[8px] font-['Orbitron'] text-emerald-200 hover:text-white"
                    title="Salvar no Google Agenda"
                  >
                    📅 CALENDAR
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
