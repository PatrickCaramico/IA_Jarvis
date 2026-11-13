// V7.1: HOLOGRAMA. Quais pedidos viram tela viva (apresentação narrada ou receita) e os comandos de voz
// enquanto ela está aberta ("próximo passo", "repete", "pausa", "fecha").

export function norm(text) {
  return String(text || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
}

const NOT_HOLO = /\b(youtube|google|maps|spotify|waze|video|videos|musica|playlist|noticias?)\b/;
const RECIPE = /\breceitas?\b|\bcomo (fazer|preparar) (um |uma |o |a )?(bolo|pao|torta|pudim|lasanha|brigadeiro|panqueca|risoto|macarrao|feijoada|mousse|biscoito|cookie|frango|carne|peixe|sopa|salada|molho|pizza|omelete|strogonoff|estrogonofe|coxinha|brownie)\b/;
const EXPLAIN = /\b(me explica|me explique|explica pra mim|explique pra mim|explica como|explique como|me ensina|me ensine|como funciona|como funcionam|faz uma apresentacao|faca uma apresentacao|apresentacao sobre|apresenta sobre|aula sobre|me da uma aula|me mostra sobre|me conta sobre|me fala sobre|pesquisa sobre|pesquise sobre|pesquisa a respeito|holograma (de|do|da|sobre))\b/;

/** Pedido que vira holograma: { kind: "receita" | "apresentacao", query } ou null. */
export function holoIntent(text) {
  const n = norm(text);
  if (!n || NOT_HOLO.test(n)) return null;
  if (RECIPE.test(n)) return { kind: "receita", query: String(text).trim() };
  if (EXPLAIN.test(n) && n.split(" ").length >= 3) return { kind: "apresentacao", query: String(text).trim() };
  return null;
}

/** Comando de voz com o holograma aberto. */
export function holoCommand(text) {
  const n = norm(text);
  if (/\b(fecha|fechar|feche|sai|sair|encerra|encerrar)\b/.test(n)) return "close";
  if (/\b(proximo|proxima|avanca|avancar|seguinte|continua o passo)\b/.test(n)) return "next";
  if (/\b(anterior|volta|voltar|volte)\b/.test(n)) return "prev";
  if (/\b(repete|repita|repetir|de novo|fala de novo)\b/.test(n)) return "repeat";
  const shortCmd = n.split(" ").length <= 4; // "para" e "segue" também aparecem em pedidos comuns
  if (shortCmd && /\b(pausa|pausar|pause|para|parar|espera)\b/.test(n)) return "pause";
  if (shortCmd && /\b(continua|continuar|continue|segue|play)\b/.test(n)) return "play";
  return null;
}

// Fala estimada (s) para avançar a cena se o aviso de "terminei de falar" não chegar.
export function speechSeconds(text) {
  const words = String(text || "").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(3, words / 2.4);
}

// "deixe 40 minutos no forno" -> rótulo do timer do passo
export function stepTimerText(minutes, title) {
  const m = Math.round(Number(minutes) || 0);
  if (m <= 0) return "";
  const h = Math.floor(m / 60);
  const rest = m % 60;
  const dur = h ? `${h} hora${h > 1 ? "s" : ""}${rest ? ` e ${rest} minutos` : ""}` : `${m} minutos`;
  return `timer de ${dur}${title ? ` para ${title}` : ""}`;
}
