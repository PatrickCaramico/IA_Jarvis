import { useMemo } from "react";

export const MESSAGES = [
  "Grandes resultados começam com um próximo passo bem escolhido.",
  "Hoje é uma boa oportunidade para transformar intenção em progresso.",
  "Constância vence a pressa. Vamos avançar com clareza.",
  "O senhor não precisa resolver tudo agora; apenas o que importa primeiro.",
];

export function getMotivationMessage(date = new Date()) {
  return MESSAGES[date.getDate() % MESSAGES.length];
}

export default function MotivationWidget() {
  const message = useMemo(() => getMotivationMessage(), []);

  return (
    <section className="motivation-card" aria-label="Frase motivacional">
      <p className="motivation-kicker">INSPIRAÇÃO DO JARVIS</p>
      <p className="motivation-message">“{message}”</p>
      <p className="motivation-footer">Um passo de cada vez, senhor.</p>
    </section>
  );
}
