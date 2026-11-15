// V7.1: HOLOGRAMA. Quais pedidos viram tela viva (apresentação narrada ou receita) e os comandos de voz
// enquanto ela está aberta ("próximo passo", "repete", "pausa", "fecha").

export function norm(text) {
  return String(text || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
}

const NOT_HOLO = /\b(youtube|google|maps|spotify|waze|video|videos|musica|playlist|noticias?)\b/;
// V7.4: pedidos pessoais seguem o caminho normal ("me fala sobre minha agenda", "como funciona meu alarme")
const PERSONAL = /\b(meu|minha|meus|minhas|agenda|tarefas?|lembretes?|compras|agua|clima|previsao|alarmes?|timer|jarvis)\b/;
const RECIPE = /\breceitas?\b|\bcomo (fazer|preparar) (um |uma |o |a )?(bolo|pao|torta|pudim|lasanha|brigadeiro|panqueca|risoto|macarrao|feijoada|mousse|biscoito|cookie|frango|carne|peixe|sopa|salada|molho|pizza|omelete|strogonoff|estrogonofe|coxinha|brownie)\b/;
const EXPLAIN = /\b(me explica|me explique|explica pra mim|explique pra mim|explica como|explique como|me ensina|me ensine|como funciona|como funcionam|faz uma apresentacao|faca uma apresentacao|apresentacao sobre|apresenta sobre|aula sobre|me da uma aula|me mostra sobre|me conta sobre|me fala sobre|pesquisa sobre|pesquise sobre|pesquisa a respeito|holograma (de|do|da|sobre))\b/;

/** Pedido que vira holograma: { kind: "receita" | "apresentacao", query } ou null. */
export function holoIntent(text) {
  const n = norm(text);
  if (!n || NOT_HOLO.test(n)) return null;
  if (RECIPE.test(n)) return { kind: "receita", query: String(text).trim() };
  if (EXPLAIN.test(n) && !PERSONAL.test(n) && n.split(" ").length >= 3) return { kind: "apresentacao", query: String(text).trim() };
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

// V7.14: com a apresentação aberta, uma PERGUNTA pausa, é respondida e a apresentação continua
const QUESTION = /^(espera|peraí|perai|pera|mas|e |o que|oque|qual|quais|quem|como|por que|porque|pq|quando|onde|quanto|quantos|quantas|me explica|explica|isso quer dizer|o que significa)\b/;
export function holoQuestion(text) {
  const raw = String(text || "").trim();
  const n = norm(raw);
  if (n.split(" ").length < 2) return false;
  return raw.endsWith("?") || QUESTION.test(n);
}

// V7.14: resposta do quiz falada: "letra b", "é a c", "alternativa d", "a resposta é a"
export function quizLetter(text) {
  const n = norm(text);
  const m = n.match(/^(?:(?:e |eh |letra |alternativa |opcao |resposta |a resposta e |acho que e |acho que e a |e a |e o )*)([abcd])$/)
    || n.match(/\b(?:letra|alternativa|opcao)\s+([abcd])\b/);
  return m ? "abcd".indexOf(m[1]) : -1;
}

// V7.14: "hologramas salvos", "minhas apresentações salvas"
export function savedHoloIntent(text) {
  const n = norm(text);
  return /\b(hologramas?|apresentacoes|apresentacao|receitas?) salv(o|os|a|as)\b/.test(n) && !/\b(apaga|apague|exclui|deleta)\b/.test(n);
}

// V7.14: o cartão animado das perguntas rápidas só aparece nelas (o PC decide de novo)
export function quickQuestion(text) {
  const n = norm(text);
  if (n.split(" ").length > 14) return false;
  return /\b(quanto (esta|custa|vale|mede|pesa)|qual (e|a|o) (altura|tamanho|populacao|capital|distancia|cotacao|temperatura|idade)|quem ganhou|quem venceu|placar|resultado do jogo|cotacao|dolar|euro|bitcoin|quantos (habitantes|anos|metros|km|quilometros))\b/.test(n);
}
