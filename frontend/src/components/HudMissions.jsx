import { useCallback, useEffect, useRef, useState } from "react";
import { MISSION_ICON, MISSION_KIND, missionHint, missionPct, progressDelta } from "../utils/hudProgress.js";

// V8.12.5: XP, ofensiva e missões do dia na central (antes só no Modo Desk). Mesmos dados e rotas do Modo Desk
// (/api/desk/xp e /api/desk/missions): o que você faz aqui conta lá, e vice-versa.
export function useDeskProgress(api, response) {
  const [level, setLevel] = useState(null);
  const [missions, setMissions] = useState(null);
  const refresh = useCallback(() => {
    api("/api/desk/xp").then(setLevel).catch(() => {});
    api("/api/desk/missions").then((m) => m?.itens && setMissions(m)).catch(() => {});
  }, [api]);
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 60_000);
    const onPush = (e) => {
      if (e.detail?.itens) setMissions(e.detail);
      api("/api/desk/xp").then(setLevel).catch(() => {});
    };
    window.addEventListener("jarvis-desk-missions", onPush);
    return () => {
      clearInterval(t);
      window.removeEventListener("jarvis-desk-missions", onPush);
    };
  }, [refresh, api]);
  // conversou com o JARVIS: as missões de uso e o XP da conversa podem ter mudado
  useEffect(() => {
    if (!response) return undefined;
    const t = setTimeout(refresh, 800);
    return () => clearTimeout(t);
  }, [response, refresh]);
  const onMissions = useCallback((m) => {
    if (m?.itens) setMissions(m);
    api("/api/desk/xp").then(setLevel).catch(() => {});
  }, [api]);
  return { level, missions, onMissions };
}

function MissionLine({ api, m, cloud, onChange }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [msg, setMsg] = useState("");
  const run = async (path, body) => {
    try {
      const r = await api(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      onChange(r.missoes || r);
      setMsg("");
      setOpen(false);
    } catch (err) {
      setMsg(err.message);
    }
  };
  const pct = missionPct(m);
  const canAnswer = !m.feita && m.tipo === "sobre" && !cloud;
  return (
    <li className={`hm-mission is-${m.tipo}${m.feita ? " is-done" : ""}`}
      title={`${m.texto}\n${MISSION_KIND[m.tipo] || "Missão"} · +${m.xp} XP · ${missionHint(m, { cloud })}`}>
      <span className="hm-ico" aria-hidden="true">{m.feita ? "✓" : MISSION_ICON[m.tipo] || "🎯"}</span>
      <div className="hm-body">
        <b>{m.texto}</b>
        {!m.feita && (m.meta || 1) > 1 && <i className="hm-bar" aria-hidden="true"><b style={{ width: `${pct}%` }} /></i>}
        {open && canAnswer && (
          <form className="hm-answer" onSubmit={(e) => { e.preventDefault(); if (text.trim()) run("/api/desk/missions/answer", { id: m.id, resposta: text.trim() }); }}>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Sua resposta (vai para a memória)" aria-label={m.texto} maxLength={300} autoFocus />
            <button type="submit" disabled={!text.trim()} aria-label="Responder">➤</button>
          </form>
        )}
        {msg && <small className="hm-err" role="alert">{msg}</small>}
      </div>
      <span className="hm-xp">+{m.xp}</span>
      {!m.feita && m.tipo === "bem" && <button type="button" className="hm-btn" onClick={() => run(`/api/desk/missions/${m.id}/done`)} title="Marcar como feita">FEITO</button>}
      {canAnswer && !open && <button type="button" className="hm-btn" onClick={() => setOpen(true)} title="Responder (vai para a memória)">✎</button>}
    </li>
  );
}

const KEY_OPEN = "jarvis.hud.missions.open";

function readOpen() {
  try {
    return localStorage.getItem(KEY_OPEN) !== "0";
  } catch {
    return true;
  }
}

export default function HudMissions({ api, level, missions, onMissions }) {
  // recolhido = só a linha do nível (o chat ganha espaço); lembra a escolha neste navegador
  const [open, setOpen] = useState(readOpen);
  const toggle = () => setOpen((v) => {
    try {
      localStorage.setItem(KEY_OPEN, v ? "0" : "1");
    } catch {
      /* sem armazenamento: só não lembra */
    }
    return !v;
  });
  const [burst, setBurst] = useState(null); // { xp, levelUp, nivel } por alguns segundos
  const prevRef = useRef(null);
  useEffect(() => {
    const delta = progressDelta(prevRef.current, level);
    prevRef.current = level;
    if (!delta) return undefined;
    setBurst(delta);
    const t = setTimeout(() => setBurst(null), delta.levelUp ? 6000 : 3000);
    return () => clearTimeout(t);
  }, [level]);
  // item novo do guarda-roupa liberado (o mesmo aviso do Modo Desk)
  const [novos, setNovos] = useState("");
  useEffect(() => {
    const list = missions?.novos || [];
    if (!list.length) return undefined;
    setNovos(`Item novo liberado para o robô: ${list.map((n) => n.nome).join(", ")}!`);
    api("/api/desk/missions/seen", { method: "POST" }).catch(() => {});
    const t = setTimeout(() => setNovos(""), 8000);
    return () => clearTimeout(t);
  }, [missions?.novos, api]);

  const of = missions?.ofensiva;
  const semana = missions?.semana;
  return (
    <div className="hm-wrap">
      {level ? (
        <div className="hm-level" title={`${level.xp} XP no total`}>
          <span className="hm-lv">NÍVEL <b>{level.nivel}</b></span>
          <i className="hm-xpbar" aria-label={`${level.no_nivel} de ${level.para_subir} XP`}><b style={{ width: `${level.pct}%` }} /></i>
          <span className="hm-num">{level.no_nivel}/{level.para_subir} XP</span>
          {of && (
            <span className={`hm-streak${of.feita_hoje ? " is-lit" : ""}`}
              title={`Ofensiva: ${of.atual} dias (recorde ${of.recorde}). ${of.feita_hoje ? "Hoje já conta." : "Faça 1 missão hoje para manter."}`}>
              🔥 {of.atual}
            </span>
          )}
          <button type="button" className="hm-toggle" onClick={toggle} aria-expanded={open}
            title={open ? "Recolher as missões" : "Mostrar as missões de hoje"}>{open ? "▾" : "▸"}</button>
          {burst && (
            <span className={`hm-burst${burst.levelUp ? " is-level" : ""}`} role="status">
              {burst.levelUp ? `NÍVEL ${burst.nivel}!` : `+${burst.xp} XP`}
            </span>
          )}
        </div>
      ) : (
        <p className="hm-muted">Carregando seu nível…</p>
      )}
      {novos && <p className="hm-new" role="status">🎁 {novos}</p>}
      {!open ? null : missions ? (
        <ul className="hm-list">
          {missions.itens.map((m) => <MissionLine key={m.id} api={api} m={m} cloud={missions.cloud} onChange={onMissions} />)}
          {semana && !semana.feita && (
            <li className="hm-week" title={semana.texto}>
              <span aria-hidden="true">🏆</span>
              <span className="hm-week-text">{semana.texto}</span>
              <i className="hm-bar" aria-hidden="true"><b style={{ width: `${missionPct(semana)}%` }} /></i>
              <small>{semana.progresso || 0}/{semana.meta || 1} · +{semana.xp} XP</small>
            </li>
          )}
        </ul>
      ) : (
        <p className="hm-muted">Carregando missões…</p>
      )}
    </div>
  );
}
