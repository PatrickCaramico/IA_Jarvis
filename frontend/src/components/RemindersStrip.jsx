import { useCallback, useEffect, useState } from "react";
import { upcoming, whenLabel } from "../utils/reminderTime.js";

// V9.4.2: os próximos lembretes visíveis na central (acima da frase de inspiração). Atualiza sozinha quando um
// lembrete é criado ou apagado (botão, voz ou outro aparelho) e a cada minuto (os que já tocaram somem).
export default function RemindersStrip({ api }) {
  const [items, setItems] = useState([]);
  const [now, setNow] = useState(new Date());
  const load = useCallback(() => {
    api("/api/reminders?only_pending=true", { timeout: 8000 })
      .then((d) => setItems(upcoming(d.reminders, 4)))
      .catch(() => {});
  }, [api]);

  useEffect(() => {
    load();
    const t = setInterval(() => { setNow(new Date()); load(); }, 60_000);
    const onWs = (e) => {
      const type = e.detail?.type;
      // "response": o lembrete pode ter sido criado por voz ("me lembra de ... às 15h")
      if (type === "reminders_updated" || type === "reminder" || type === "response") load();
    };
    window.addEventListener("jarvis_ws_event", onWs);
    window.addEventListener("jarvis-reminders-changed", load);
    return () => {
      clearInterval(t);
      window.removeEventListener("jarvis_ws_event", onWs);
      window.removeEventListener("jarvis-reminders-changed", load);
    };
  }, [load]);

  const remove = async (id) => {
    setItems((list) => list.filter((r) => r.id !== id));
    try {
      await api(`/api/reminders/${id}`, { method: "DELETE" });
    } catch {
      load();
    }
  };

  const add = () => window.dispatchEvent(new CustomEvent("jarvis-new-reminder"));
  return (
    <div className="rms" aria-label="Próximos lembretes">
      <span className="rms-label">⏰ LEMBRETES</span>
      {items.map((r, i) => (
        <span key={r.id} className="rms-item" style={{ "--i": i }}>
          <b>{whenLabel(r.data_hora, now)}</b>
          <span title={r.texto}>{r.texto}</span>
          <button type="button" onClick={() => remove(r.id)} aria-label={`Apagar o lembrete ${r.texto}`} title="Apagar">✕</button>
        </span>
      ))}
      {!items.length && <span className="rms-empty">Nenhum lembrete pendente.</span>}
      <button type="button" className="rms-add" onClick={add} title="Novo lembrete">＋ LEMBRETE</button>
    </div>
  );
}
