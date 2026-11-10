import useNow from "../hooks/useNow.js";

const TIME_ZONE = "America/Sao_Paulo";

export default function DigitalClockWidget() {
  const now = useNow();

  const time = new Intl.DateTimeFormat("pt-BR", {
    timeZone: TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(now);
  const date = new Intl.DateTimeFormat("pt-BR", {
    timeZone: TIME_ZONE,
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(now);

  return (
    <section className="digital-clock-card" aria-label="Relógio digital de Brasília">
      <p className="digital-clock-zone">HORÁRIO DE BRASÍLIA · BRT</p>
      <time className="digital-clock-time" dateTime={now.toISOString()}>{time}</time>
      <p className="digital-clock-date">{date}</p>
    </section>
  );
}
