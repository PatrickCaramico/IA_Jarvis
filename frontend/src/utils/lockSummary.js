// Montagem do resumo do dia falado ao entrar (seção 17.3). Função pura e testável.
// A fala precisa caber em ~20 segundos: as partes opcionais saem primeiro quando passa do limite.

export const MAX_SUMMARY_WORDS = 55; // ~20 s na voz pt-BR-AntonioNeural em velocidade normal

export function spokenTime(hour, minute) {
  if (minute === 0) {
    return `${hour === 0 ? "meia-noite" : hour === 12 ? "meio-dia" : `${hour} horas`} em ponto`;
  }
  return `${hour === 0 ? "meia-noite" : hour === 1 ? "uma hora" : `${hour} horas`} e ${minute} minuto${minute === 1 ? "" : "s"}`;
}

export function shouldSpeakSummary(mode, isFirstAccessOfDay) {
  if (mode === "off") return false;
  if (mode === "always") return true;
  return Boolean(isFirstAccessOfDay); // "first_login" (padrão)
}

const countWords = (text) => text.split(/\s+/).filter(Boolean).length;

/**
 * parts: { hour, minute, weather, tasks, fanMatch, waterYesterday, motivation }
 * Retorna { text, parts: [chaves usadas] }.
 */
export function buildDailySummary({ hour, minute, weather, tasks = [], fanMatch = null, waterYesterday = null, motivation = "" },
  maxWords = MAX_SUMMARY_WORDS) {
  const greeting = hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
  const segments = [];
  segments.push({ key: "greeting", required: true, text: `${greeting}, senhor. São ${spokenTime(hour, minute)}.` });
  if (weather) {
    segments.push({ key: "weather", required: true, text: `Em ${weather.place}, ${weather.temperature} graus, ${weather.description}.` });
  }
  const pending = tasks.filter((t) => !t.concluida);
  segments.push({
    key: "tasks",
    required: true,
    text: pending.length
      ? `${pending.length} tarefa${pending.length === 1 ? "" : "s"} pendente${pending.length === 1 ? "" : "s"}: ${pending.slice(0, 2).map((t) => t.texto).join(", ")}${pending.length > 2 ? " e outras" : ""}.`
      : "Nenhuma tarefa pendente.",
  });
  if (fanMatch && fanMatch.opponent) {
    let when = "";
    try {
      const d = new Date(fanMatch.date);
      if (!Number.isNaN(d.getTime())) {
        when = fanMatch.is_match_day
          ? ` hoje às ${String(d.getHours()).padStart(2, "0")}h${d.getMinutes() ? String(d.getMinutes()).padStart(2, "0") : ""}`
          : ` em ${d.toLocaleDateString("pt-BR", { day: "numeric", month: "long" })}`;
      }
    } catch { /* data inválida: sem horário */ }
    segments.push({ key: "fan", required: false, priority: 2, text: `Próximo jogo: contra o ${fanMatch.opponent}${when}.` });
  }
  if (waterYesterday && Number.isFinite(waterYesterday.total_ml) && waterYesterday.total_ml > 0) {
    segments.push({ key: "water", required: false, priority: 1, text: `Ontem você bebeu ${waterYesterday.total_ml} ml de água.` });
  }
  if (motivation) {
    segments.push({ key: "motivation", required: false, priority: 0, text: motivation });
  }

  let chosen = [...segments];
  const total = () => countWords(chosen.map((s) => s.text).join(" "));
  // Remove opcionais da menor prioridade para a maior até caber
  const optional = segments.filter((s) => !s.required).sort((a, b) => a.priority - b.priority);
  for (const seg of optional) {
    if (total() <= maxWords) break;
    chosen = chosen.filter((s) => s !== seg);
  }
  // Ainda grande: encurta a lista de tarefas
  if (total() > maxWords) {
    chosen = chosen.map((s) => (s.key === "tasks" && pending.length
      ? { ...s, text: `${pending.length} tarefa${pending.length === 1 ? "" : "s"} pendente${pending.length === 1 ? "" : "s"}.` }
      : s));
  }
  return { text: chosen.map((s) => s.text).join(" "), parts: chosen.map((s) => s.key) };
}
