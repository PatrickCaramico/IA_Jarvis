import { useEffect, useState } from "react";
import WaterVessel from "../WaterVessel.jsx";
import { Note, SaveStatus, Section, SelectRow, Toggle } from "./SettingsControls.jsx";

const VESSELS = [["glass", "Copo"], ["bottle", "Garrafa"], ["reactor", "Reator"]];

// Aba "Hidratação" (seção 18): recipiente com pré-visualização, valores rápidos, som e ritmo.
export default function WaterSettings({ api, prefs, onPatch }) {
  const [quick, setQuick] = useState((prefs.water_quick_ml || [200, 300, 500]).join(", "));
  const [goal, setGoal] = useState("");
  const [status, setStatus] = useState(null);
  const [preview, setPreview] = useState(1100);
  const [interval, setIntervalMin] = useState("120");

  useEffect(() => {
    api("/api/water").then((d) => {
      setGoal(String(d.goal_ml || 2000));
      setIntervalMin(String(d.reminder_interval_min ?? 120));
    }).catch(() => {});
  }, [api]);

  const saveInterval = async (value) => {
    setIntervalMin(value);
    try {
      await api("/api/water/reminder", { method: "POST", body: JSON.stringify({ interval_min: Number(value) }) });
      setStatus({ ok: Number(value) ? "Lembrete de água atualizado." : "Lembrete de água desligado." });
    } catch (err) {
      setStatus({ error: err.message });
    }
  };

  const saveQuick = () => {
    const list = quick.split(/[,;\s]+/).map((v) => parseInt(v, 10)).filter((v) => Number.isFinite(v));
    if (!list.length || list.length > 4 || list.some((v) => v < 20 || v > 3000)) {
      setStatus({ error: "Use de 1 a 4 valores entre 20 e 3000 ml." });
      return;
    }
    setStatus(null);
    onPatch({ water_quick_ml: list });
  };

  const saveGoal = async () => {
    const value = parseInt(goal, 10);
    try {
      await api("/api/water/goal", { method: "POST", body: JSON.stringify({ goal_ml: value }) });
      setStatus({ ok: "Meta diária atualizada." });
    } catch (err) {
      setStatus({ error: err.message });
    }
  };

  return (
    <div className="space-y-3">
      <Section title="RECIPIENTE">
        <div className="grid grid-cols-3 gap-2">
          {VESSELS.map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => onPatch({ water_vessel: key })}
              className={`rounded border p-1.5 text-[11px] font-['Orbitron'] ${prefs.water_vessel === key || (!prefs.water_vessel && key === "glass") ? "border-cyan-300 bg-cyan-500/20 text-white" : "border-cyan-500/20 bg-black/30 text-cyan-300/70"}`}
            >
              <div className="h-24"><WaterVessel totalMl={preview} goalMl={2000} vessel={key} size="compact" /></div>
              {label}
            </button>
          ))}
        </div>
        <button type="button" className="text-[10px] text-cyan-400 underline" onClick={() => setPreview((p) => (p >= 1900 ? 300 : p + 400))}>
          testar animação
        </button>
      </Section>

      <Section title="REGISTRO">
        <label className="block text-xs font-['Orbitron'] text-cyan-200">Valores rápidos (ml)</label>
        <input value={quick} onChange={(e) => setQuick(e.target.value)} onBlur={saveQuick}
          className="w-full rounded border border-cyan-500/30 bg-black/50 px-2 py-1.5 text-xs text-cyan-100" aria-label="Valores rápidos" />
        <label className="block text-xs font-['Orbitron'] text-cyan-200 pt-1">Meta diária (ml)</label>
        <div className="flex gap-2">
          <input value={goal} onChange={(e) => setGoal(e.target.value.replace(/\D/g, ""))}
            className="flex-1 rounded border border-cyan-500/30 bg-black/50 px-2 py-1.5 text-xs text-cyan-100" aria-label="Meta diária" />
          <button type="button" onClick={saveGoal} className="rounded border border-cyan-400/60 bg-cyan-500/20 px-3 text-[11px] font-['Orbitron'] text-cyan-100">SALVAR</button>
        </div>
        <SelectRow
          label="Lembrar de beber água"
          value={interval}
          onChange={saveInterval}
          options={[["0", "Desligado"], ["30", "A cada 30 min"], ["60", "A cada 1 hora"], ["90", "A cada 1h30"],
            ["120", "A cada 2 horas"], ["180", "A cada 3 horas"], ["240", "A cada 4 horas"]]}
        />
        <Note>Conta a partir do último copo registrado ou do último lembrete, só entre 8h e 22h.</Note>
        <SaveStatus status={status} />
      </Section>

      <Section title="EXTRAS">
        <Toggle label="Dica de ritmo do dia" hint='Ex.: "Você está 300 ml acima do ritmo", pela janela de horário do lembrete.'
          checked={prefs.water_pace_hint !== false} onChange={(v) => onPatch({ water_pace_hint: v })} />
        <Toggle label="Som de água ao registrar" hint="Sintetizado no navegador; respeita o modo silencioso."
          checked={prefs.water_sound} onChange={(v) => onPatch({ water_sound: v })} />
        <Note>Com "reduzir movimento" ativo no sistema, o recipiente não tem ondas, fio de água nem bolhas.</Note>
      </Section>
    </div>
  );
}
