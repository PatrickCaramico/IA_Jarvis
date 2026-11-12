/**
 * V4.3: demo do briefing "bom dia" sem backend e sem desbloqueio.
 * Abre a central real (HudLayout + orbe) e toca a mesma sequência de eventos que
 * core/briefing_flow.py envia pelo WebSocket. Uso: npm run dev e abra /briefing-demo.html.
 */
import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import HudLayout from "../components/HudLayout.jsx";
import WireOrb from "../components/WireOrb.jsx";
import "../index.css";
import "../brand.css";
import "../feedback.css";
import "../briefing.css";
import "../blueprint.css";
import "../mobile.css"; // V5.8: mostra também o layout do celular

const TABS = [
  { id: "clima", label: "Clima" },
  { id: "agenda", label: "Agenda" },
  { id: "tarefas", label: "Tarefas" },
  { id: "jogo", label: "Jogo" },
  { id: "email", label: "E-mails" },
  { id: "noticias", label: "Notícias" },
  { id: "saude", label: "Prioridades" },
];

const SEGMENTS = [
  { tab: "clima", progress: "Lendo o clima de hoje...", speech: "Em Maragogi, 27 graus e predomínio de sol, com mínima de 23 e máxima de 28. A chance de chuva é de 62 por cento. Vale levar um guarda-chuva.",
    card: { kind: "weather", label: "PANORAMA · CLIMA", icon: "☂", tip: "Vale levar um guarda-chuva.", title: "Maragogi", temperature: 26.7, description: "chuva fraca", minimum: 23.3, maximum: 27.5, apparent: 30, rain_probability: 62, wind: 18.3, footer: "Open-Meteo · 07:42" } },
  { tab: "agenda", progress: "Conferindo a agenda de hoje...", speech: "Você tem 2 compromissos hoje. O primeiro é Reunião com o time, às 09:30, daqui a 45 minutos. Depois, Dentista às 15:00.",
    card: { kind: "agenda", label: "AGENDA · HOJE", title: "2 compromissos", next_in: 45, items: [{ time: "09:30", title: "Reunião com o time", location: "Google Meet" }, { time: "15:00", title: "Dentista", location: "Lembrete" }], more: 0, footer: "Google Agenda + lembretes" } },
  { tab: "tarefas", progress: "Montando as prioridades do dia...", speech: "Você tem 4 tarefas pendentes. Sugiro começar por Pagar a luz, e depois Revisar o contrato.",
    card: { kind: "tasks", label: "PRIORIDADES · HOJE", title: "Comece por: Pagar a luz", items: [{ text: "Pagar a luz" }, { text: "Revisar o contrato" }, { text: "Ligar para o banco" }], more: 1, total: 4, footer: "As mais antigas primeiro · diga \"concluir tarefa\" ao terminar" } },
  { tab: "jogo", progress: "Conferindo o jogo de hoje...", speech: "E hoje tem Palmeiras, contra Remo, às 21:30.",
    card: { kind: "metrics", badge: "◉", label: "MODO TORCEDOR · HOJE", title: "Palmeiras x Remo", items: [{ label: "Adversário", value: "Remo" }, { label: "Horário", value: "21:30" }, { label: "Competição", value: "Brasileirão" }, { label: "Local", value: "Allianz Parque" }], footer: "Agenda do time · ESPN" } },
  { tab: "email", progress: "Verificando e-mails importantes...", speech: "Chegaram 20 e-mails desde ontem, e 5 pedem uma ação sua, a começar por Stripe, Santander.",
    card: { kind: "email", label: "COMUNICAÇÕES · E-MAIL", title: "Pedem sua atenção", connected: true, received: 20, to_act: 5, more: 3,
      items: [{ sender: "Stripe", summary: "Sua fatura de novembro vence em 3 dias" }, { sender: "Santander", summary: "Confirme o novo acesso ao aplicativo" }],
      footer: "Triagem do briefing · somente itens verificados" } },
  { tab: "noticias", progress: "Atualizando o radar de notícias...", speech: "Em tecnologia: Nova geração de chips promete dobrar autonomia de notebooks. A informação é do Tecmundo.",
    card: { kind: "news", label: "RADAR · NOTÍCIAS", title: "Tecnologia", headline: "Nova geração de chips promete dobrar autonomia de notebooks", source: "Tecmundo", domain: "www.tecmundo.com.br", link: "https://www.tecmundo.com.br", published: new Date().toISOString(), footer: "Google News" } },
  { tab: "noticias", progress: "Atualizando o radar de notícias...", speech: "Em novos modelos de IA: Laboratórios anunciam modelos com raciocínio mais longo. A informação é do g1.",
    card: { kind: "news", label: "RADAR · NOTÍCIAS", title: "Novos modelos de IA", headline: "Laboratórios anunciam modelos com raciocínio mais longo", source: "g1", domain: "g1.globo.com", link: "https://g1.globo.com", published: new Date().toISOString(), footer: "Google News" } },
  { tab: "noticias", progress: "Atualizando o radar de notícias...", speech: "Em política: Congresso vota pauta econômica nesta semana. A informação é do Correio Braziliense.",
    card: { kind: "news", label: "RADAR · NOTÍCIAS", title: "Política", headline: "Congresso vota pauta econômica nesta semana", source: "Correio Braziliense", domain: "www.correiobraziliense.com.br", link: "https://www.correiobraziliense.com.br", published: new Date().toISOString(), footer: "Google News" } },
  { tab: "saude", progress: "Organizando prioridades...", speech: "Seus dados de saúde estão disponíveis sob demanda.",
    card: { kind: "health", label: "SAÚDE · LEITURA DE DADOS", title: "Observações disponíveis", chip: "sob demanda", text: "Por privacidade, não leio detalhes de saúde automaticamente. Peça \"meus dados de saúde\" quando quiser.", footer: "20 leituras sensíveis preservadas" } },
];

const READINESS = {
  recovery: 54,
  metrics: [
    { label: "Movimento", value: "0 passos" },
    { label: "Esforço", value: "0,2" },
    { label: "Sono", value: "7,4 h" },
    { label: "Hidratação", value: "0,0 L" },
  ],
  footer: "Relógio · 07:40",
};

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const speechMs = (text) => Math.max(1800, text.length * 55); // ~ritmo da voz

function Demo() {
  const [state, setState] = useState("idle");
  const [briefing, setBriefing] = useState(null);
  const [userText, setUserText] = useState("");
  const [response, setResponse] = useState("");
  const [cards, setCards] = useState([]);
  const [run, setRun] = useState(0);
  const skipRef = React.useRef(null);

  useEffect(() => {
    if (!run) return undefined;
    let alive = true;
    // Fala simulada: espera o tempo da frase ou até clicarem em PRÓXIMO
    const say = async (text) => {
      if (!alive) return;
      setState("speaking");
      await new Promise((resolve) => {
        const t = setTimeout(resolve, speechMs(text));
        skipRef.current = () => { clearTimeout(t); resolve(); };
      });
      skipRef.current = null;
    };
    (async () => {
      setUserText("Bom dia");
      setResponse("");
      setCards([]);
      setState("processing");
      await wait(900);
      const opening = "Bom dia. Hoje é quarta-feira, 4 de novembro. Revisei o que já está consolidado e nada exige interromper a sua manhã.";
      setBriefing({ phase: "running", mode: "morning", title: "BRIEFING", tabs: TABS, greeting: "Bom dia.",
        opening: "Sem desvios relevantes", opening_sub: "dados consolidados desde ontem", index: -1, total: SEGMENTS.length,
        plan: SEGMENTS.map((seg) => seg.card), current: null, cards: [], speech: opening });
      setResponse(opening);
      await say(opening);
      for (let i = 0; i < SEGMENTS.length && alive; i += 1) {
        const s = SEGMENTS[i];
        setBriefing((b) => ({ ...b, index: i, total: SEGMENTS.length, activeTab: s.tab, progress: s.progress, speech: s.speech, current: s.card, cards: [...b.cards, s.card] }));
        setResponse(s.speech);
        await say(s.speech);
      }
      if (!alive) return;
      const closing = "Hoje, resolva primeiro os e-mails que pedem ação e depois mantenha o foco no essencial.";
      setBriefing((b) => ({ ...b, phase: "done", cards: SEGMENTS.map((s) => s.card), readiness: READINESS, closing }));
      setCards([{ type: "briefing", data: { cards: SEGMENTS.map((s) => s.card), closing } }]);
      setResponse(closing);
      await say(closing);
      setState("idle");
    })();
    return () => { alive = false; };
  }, [run]);

  const STATE_LABEL = { idle: "Em espera", processing: "Processando", speaking: "Falando" };
  return (
    <>
      <HudLayout
        aiName="J.A.R.V.I.S."
        stateLabel={STATE_LABEL[state]}
        jarvisState={state}
        listening={false}
        interim=""
        connected
        services={{ ai: true, microphone: true, camera: true, internet: true, backend: true }}
        busy={state !== "idle"}
        api={() => Promise.reject(new Error("demo"))}
        userText={userText}
        response={response}
        responseCards={cards}
        briefing={briefing}
        onCloseBriefing={() => setBriefing(null)}
        onSkipBriefing={() => skipRef.current && skipRef.current()}
        photoUrl="/brand/avatar-512.png"
        error=""
        onCommand={() => setRun((n) => n + 1)}
        onToggleZen={() => {}}
        onOpenWidgets={() => {}}
        orbSlot={<WireOrb state={state} />}
        commandSlot={null}
        tasksSlot={null}
      />
      <button type="button" className="bf-demo-run" onClick={() => setRun((n) => n + 1)}>▶ Simular "bom dia"</button>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<Demo />);
