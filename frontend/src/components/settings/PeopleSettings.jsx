import { useEffect, useState } from "react";
import { Note, Section } from "./SettingsControls.jsx";

// V4.5: pessoas deste PC (perfis locais com rosto, PIN e preferências próprias).
export default function PeopleSettings({ api }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(null);

  const load = () => api("/api/profiles").then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const remove = async (id) => {
    setError("");
    try {
      const res = await api(`/api/profiles/${encodeURIComponent(id)}`, { method: "DELETE" });
      setData((cur) => ({ ...cur, profiles: res.profiles }));
      setConfirming(null);
    } catch (e) {
      setError(e.message);
    }
  };

  const ownerActive = data?.active === "dono";

  return (
    <div className="space-y-3">
      <Section title={`PESSOAS DESTE PC ${data ? `· ${data.profiles.length} / ${data.max}` : ""}`}>
        {!data && !error && <Note>Carregando…</Note>}
        {data?.profiles.map((p) => (
          <div key={p.id} className="flex items-center justify-between gap-2 rounded border border-cyan-500/20 bg-black/30 px-2.5 py-2">
            <div className="min-w-0">
              <div className="truncate text-sm text-cyan-100">
                {p.name} {p.is_owner && <span className="ml-1 text-[10px] font-['Orbitron'] text-emerald-300">PRINCIPAL</span>}
                {p.active && <span className="ml-1 text-[10px] font-['Orbitron'] text-amber-300">VOCÊ</span>}
              </div>
              <div className="text-[10px] text-cyan-400/70">
                {p.has_photo ? "rosto cadastrado" : "sem rosto"} · {p.has_pin ? "com PIN" : "sem PIN"}
              </div>
            </div>
            {ownerActive && !p.is_owner && (
              confirming === p.id ? (
                <div className="flex shrink-0 gap-1">
                  <button type="button" onClick={() => remove(p.id)} className="rounded border border-rose-400/70 px-2 py-1 text-[10px] font-['Orbitron'] text-rose-200 hover:bg-rose-500/20">
                    APAGAR TUDO
                  </button>
                  <button type="button" onClick={() => setConfirming(null)} className="rounded border border-cyan-500/40 px-2 py-1 text-[10px] text-cyan-200">
                    Não
                  </button>
                </div>
              ) : (
                <button type="button" onClick={() => setConfirming(p.id)} className="shrink-0 rounded border border-cyan-500/40 px-2 py-1 text-[10px] font-['Orbitron'] text-cyan-200 hover:border-rose-400/70">
                  REMOVER
                </button>
              )
            )}
          </div>
        ))}
        {confirming && <Note tone="warn">Remover apaga o perfil e todos os dados dessa pessoa neste PC (tarefas, memória, preferências). Não dá para desfazer.</Note>}
        {error && <Note tone="warn">{error}</Note>}
      </Section>

      <Section title="COMO FUNCIONA">
        <Note>
          Cada pessoa entra com o próprio rosto ou PIN e vê só os próprios dados: preferências (Modo Torcedor, fundo,
          tema), tarefas, lembretes, memória, notas, Google Agenda e Spotify. Para adicionar alguém, na tela de bloqueio
          toque em ＋ NOVA PESSOA (o PIN do perfil principal autoriza). Ao bloquear, o PC volta para o perfil principal.
          Tudo fica só neste computador.
        </Note>
      </Section>
    </div>
  );
}
