import { useEffect, useState } from "react";

// V4.3: as mesmas etapas do briefing "bom dia" na central (um card por assunto)
const BRIEFING_STEPS = [
  { id: "clima",    label: "Clima",       sub: "Temperatura, mínima, máxima, chuva e vento" },
  { id: "agenda",   label: "Agenda",      sub: "Google Agenda e lembretes de hoje" },
  { id: "email",    label: "E-mails",     sub: "Triagem: recebidos e quantos pedem ação" },
  { id: "noticias", label: "Notícias",    sub: "Tecnologia, novos modelos de IA e política" },
  { id: "saude",    label: "Prioridades", sub: "Saúde sob demanda e recomendação do dia" },
];

export default function BriefingScreen({ onSend }) {
  const [activeStep, setActiveStep] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    // Animação sequencial das etapas do briefing
    const timer = setInterval(() => {
      setActiveStep((current) => (current < BRIEFING_STEPS.length - 1 ? current + 1 : current));
    }, 600);
    return () => clearInterval(timer);
  }, []);

  const handleRunBriefing = () => {
    if (onSend) onSend("Bom dia");
    setStarted(true);
  };

  return (
    <div className="hs-stack">
      {/* Etapas Animadas */}
      <div className="hl-panel">
        <header className="hl-panel-head">
          <span>ETAPAS DO BRIEFING</span>
          <em>SISTEMA PRONTO</em>
        </header>
        <div className="hl-panel-body">
          <div className="hs-briefing-steps">
            {BRIEFING_STEPS.map((step, idx) => {
              const isDone = idx <= activeStep;
              const isCurrent = idx === activeStep;
              return (
                <div key={step.id} className={`hs-bstep${isDone ? " is-done" : ""}${isCurrent ? " is-current" : ""}`}>
                  <div className="hs-bstep-indicator">{isDone ? "✓" : idx + 1}</div>
                  <div className="hs-bstep-info">
                    <strong>{step.label}</strong>
                    <small>{step.sub}</small>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Conteúdo do Briefing */}
      <div className="hl-panel">
        <header className="hl-panel-head">
          <span>PANORAMA DO DIA & BOM DIA NARRADO</span>
          <button type="button" className="hl-btn" onClick={handleRunBriefing} disabled={started}>
            {started ? "BRIEFING NA CENTRAL" : "▶ REPRODUZIR BRIEFING COMPLETO"}
          </button>
        </header>
        <div className="hl-panel-body">
          <p className="hs-briefing-text">
            {started
              ? "O briefing está passando na central: cada assunto entra como um card enquanto o JARVIS fala dele. Feche esta tela para acompanhar."
              : "Diga \"bom dia\" ou clique acima. O JARVIS abre dizendo se há algo que exige atenção, fala de clima, agenda, e-mails, notícias e saúde (sob demanda) e fecha com uma recomendação do dia."}
          </p>
        </div>
      </div>
    </div>
  );
}
