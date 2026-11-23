import { useCallback, useEffect, useState } from "react";
import { cardText, deepCard, groupByMonitor, memText, pctText, processName, runSkill, usageLevel } from "../utils/deskSkills.js";

// V8.11: as Habilidades (Skills) no Modo Desk, com botões: Janelas, Meu PC ao vivo, Agenda e Ferramentas.
// Tudo passa por /api/skills/{nome}/run (só no PC); o que é crítico pede confirmação aqui na tela.

function Card({ title, icon, right, children, className = "" }) {
  return (
    <section className={`dk-card ${className}`}>
      {(title || right) && <header>{icon && <span className="dk-card-ico">{icon}</span>}<h3>{title}</h3>{right}</header>}
      {children}
    </section>
  );
}

function Status({ text, ok = true }) {
  if (!text) return null;
  return <p className={`dkt-status${ok ? "" : " is-err"}`} role="status" aria-live="polite">{text}</p>;
}

function useSkill(api) {
  const [busy, setBusy] = useState("");
  const [status, setStatus] = useState({ text: "", ok: true });
  const run = useCallback(async (name, opts = {}, key = name) => {
    setBusy(key);
    const r = await runSkill(api, name, opts);
    setBusy("");
    if (r.speech) setStatus({ text: r.speech, ok: r.ok !== false });
    return r;
  }, [api]);
  return { busy, status, setStatus, run };
}

// ------------------------------------------------------------------ 🪟 Janelas e workspaces
export function WindowsPanel({ api }) {
  const { busy, status, run } = useSkill(api);
  const [wins, setWins] = useState(null);
  const [spaces, setSpaces] = useState([]);
  const [name, setName] = useState("");

  const load = useCallback(async () => {
    const r = await runSkill(api, "janelas_abertas");
    setWins(r.ok ? r.data?.janelas || [] : { erro: r.speech });
    const w = await runSkill(api, "listar_workspaces");
    setSpaces(w.data?.workspaces || []);
  }, [api]);
  useEffect(() => { load(); }, [load]);

  const act = async (skill, args, key) => { await run(skill, { args }, key); load(); };
  const groups = Array.isArray(wins) ? groupByMonitor(wins) : [];
  const monitors = groups.map((g) => g.monitor);
  const save = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    await act("salvar_workspace", { nome: name.trim() }, "salvar");
    setName("");
  };
  const remove = async (n) => {
    if (!window.confirm(`Apagar o workspace "${n}"?`)) return;
    await run("apagar_workspace", { args: { nome: n }, confirm: true }, `apagar-${n}`);
    load();
  };

  return (
    <div className="dkt-grid">
      <Card title="Janelas abertas" icon="🪟" className="dk-span2" right={(
        <div className="dk-row">
          <button type="button" className="dk-btn" disabled={!!busy} onClick={() => act("organizar_janelas", { layout: "grade" }, "grade")}>▦ GRADE</button>
          <button type="button" className="dk-btn" disabled={!!busy} onClick={() => act("organizar_janelas", { layout: "lado_a_lado" }, "lado")}>◫ LADO A LADO</button>
          <button type="button" className="dk-btn" disabled={!!busy} onClick={load} aria-label="Atualizar a lista">↻</button>
        </div>
      )}>
        {wins === null && <p className="dk-muted">Lendo as janelas…</p>}
        {wins?.erro && <p className="dk-muted">{wins.erro}</p>}
        {groups.map((g) => (
          <div key={g.monitor} className="dkt-mon">
            {monitors.length > 1 && <small className="dk-label">MONITOR {g.monitor}{g.monitor === 1 ? " · PRINCIPAL" : ""}</small>}
            <ul className="dk-list">
              {g.janelas.map((j, i) => (
                <li key={`${j.programa}-${i}`}>
                  <span className="dkt-win"><b>{j.programa}</b><small>{j.titulo}</small></span>
                  {monitors.filter((m) => m !== g.monitor).map((m) => (
                    <button type="button" key={m} className="dk-btn is-sm" disabled={!!busy} title={`Mandar para o monitor ${m}`}
                      onClick={() => act("janela_para_monitor", { app: j.programa, monitor: m }, `mov-${i}`)}>→ {m}</button>
                  ))}
                  <button type="button" className="dk-btn is-sm" disabled={!!busy} title="Maximizar e minimizar as outras deste monitor"
                    onClick={() => act("organizar_janelas", { layout: "foco", apps: [j.programa] }, `foco-${i}`)}>⤢ FOCO</button>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {Array.isArray(wins) && wins.length === 0 && <p className="dk-muted">Nenhuma janela aberta.</p>}
        <Status {...status} />
      </Card>
      <Card title="Workspaces" icon="💾">
        <p className="dk-muted">Guarde onde está cada janela (programa, monitor e tamanho) e remonte tudo com um toque; o que estiver fechado abre sozinho.</p>
        <form className="dk-add" onSubmit={save}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nome (estudo, trabalho, reunião) e Enter" aria-label="Nome do workspace" />
        </form>
        <ul className="dk-list">
          {spaces.map((w) => (
            <li key={w.nome}>
              <span className="dkt-win"><b>{w.nome}</b><small>{w.janelas} janelas · {w.salvo}</small></span>
              <button type="button" className="dk-btn is-sm is-main" disabled={!!busy} onClick={() => act("abrir_workspace", { nome: w.nome }, `abrir-${w.nome}`)}>
                {busy === `abrir-${w.nome}` ? "Montando…" : "▶ MONTAR"}
              </button>
              <button type="button" className="dk-del" onClick={() => remove(w.nome)} aria-label={`Apagar ${w.nome}`}>✕</button>
            </li>
          ))}
          {spaces.length === 0 && <li className="dk-muted">Nenhum salvo ainda. Arrume as janelas e dê um nome acima.</li>}
        </ul>
        <p className="dk-muted dkt-tip">Dica: um workspace chamado <b>reuniao</b> é montado sozinho no modo reunião.</p>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------ 🖥 Meu PC ao vivo
export function PcBars({ api, compact = false }) {
  const [snap, setSnap] = useState(null);
  useEffect(() => {
    let alive = true;
    const tick = () => api("/api/system", { timeout: 8000 }).then((s) => alive && setSnap(s)).catch(() => {});
    tick();
    const t = setInterval(tick, compact ? 8000 : 4000);
    return () => { alive = false; clearInterval(t); };
  }, [api, compact]);
  const rows = [["Processador", snap?.cpu_percent], ["Memória", snap?.ram_percent]];
  return (
    <div className={`dkt-bars${compact ? " is-compact" : ""}`}>
      {rows.map(([label, v]) => (
        <div key={label} className={`dkt-bar ${usageLevel(v)}`}>
          <span>{label}</span>
          <i><b style={{ width: `${Math.min(100, Math.max(0, Number(v) || 0))}%` }} /></i>
          <em>{pctText(v)}</em>
        </div>
      ))}
      {!compact && snap?.disk_free_gb != null && <p className="dk-muted">Disco: {String(snap.disk_free_gb).replace(".", ",")} GB livres · {snap.processes ?? "—"} processos</p>}
    </div>
  );
}

export function PcLive({ api }) {
  const { busy, status, run } = useSkill(api);
  const [heavy, setHeavy] = useState(null);
  const check = useCallback(async () => {
    const r = await run("programas_pesados", {}, "pesados");
    setHeavy(r.ok ? r.data?.programas || [] : null);
  }, [run]);
  const close = async (p) => {
    if (!window.confirm(`Fechar o ${p.label}? O que não estiver salvo nele pode se perder.`)) return;
    await run("fechar_programa", { args: { programa: processName(p.name) }, confirm: true }, `fechar-${p.name}`);
    check();
  };
  return (
    <Card title="Agora no PC" icon="📈" right={(
      <button type="button" className="dk-btn" disabled={!!busy} onClick={check}>{busy === "pesados" ? "Medindo…" : "🔎 O QUE ESTÁ PESANDO?"}</button>
    )}>
      <PcBars api={api} />
      {heavy && (
        <ul className="dk-list dkt-heavy">
          {heavy.map((p) => (
            <li key={p.name}>
              <span className="dkt-win"><b>{p.label}</b><small>{memText(p.mem_mb)} · CPU {Math.round(p.cpu_percent)}%{p.count > 1 ? ` · ${p.count} processos` : ""}</small></span>
              <button type="button" className="dk-btn is-sm is-danger" disabled={!!busy} onClick={() => close(p)}>✕ FECHAR</button>
            </li>
          ))}
        </ul>
      )}
      <Status {...status} />
      <p className="dk-muted dkt-tip">O vigia do sistema avisa sozinho quando o processador ou a memória ficam no limite. Para desligar: "desliga o vigia do sistema".</p>
    </Card>
  );
}

// ------------------------------------------------------------------ 📅 Agenda e modo reunião
export function AgendaPanel({ api }) {
  const { busy, status, run } = useSkill(api);
  const [next, setNext] = useState(null);
  const [pilot, setPilot] = useState(null);
  const load = useCallback(async () => {
    const n = await runSkill(api, "proxima_reuniao");
    setNext(n);
    const p = await runSkill(api, "piloto_agenda");
    setPilot(p.data || null);
  }, [api]);
  useEffect(() => { load(); }, [load]);
  const act = async (skill, args, key) => { await run(skill, { args }, key); load(); };
  return (
    <div className="dkt-grid">
      <Card title="Próxima reunião" icon="📅" className="dk-span2">
        <p className="dkt-big">{next ? next.speech : "Lendo a agenda…"}</p>
        <div className="dk-row">
          {pilot?.reuniao_ativa
            ? <button type="button" className="dk-btn is-main" disabled={!!busy} onClick={() => act("sair_modo_reuniao", null, "sair")}>✓ TERMINEI A REUNIÃO</button>
            : <button type="button" className="dk-btn is-main" disabled={!!busy} onClick={() => act("modo_reuniao", next?.data?.link ? { evento: next.data.titulo || "", link: next.data.link } : null, "reuniao")}>🎧 ATIVAR MODO REUNIÃO</button>}
          <button type="button" className="dk-btn" onClick={load} aria-label="Atualizar">↻</button>
        </div>
        {pilot?.reuniao_ativa && <p className="dk-muted">Modo reunião ativo{pilot.reuniao ? `: ${pilot.reuniao}` : ""}. O {"JARVIS"} está em silêncio até você terminar.</p>}
        <Status {...status} />
      </Card>
      <Card title="Aviso antes das reuniões" icon="⏰">
        <p className="dk-muted">Alguns minutos antes de cada compromisso com horário, o JARVIS avisa e oferece o modo reunião (pausa a música, abre o link da chamada e fica em silêncio).</p>
        {pilot && (
          <>
            <label className="dk-toggle-row">
              <input type="checkbox" checked={pilot.ativo} onChange={(e) => act("piloto_agenda", { ativo: e.target.checked }, "ativo")} />
              <span>Avisar antes das reuniões</span>
            </label>
            <div className="dk-row dkt-chips" role="radiogroup" aria-label="Minutos de antecedência">
              {[2, 5, 10, 15].map((m) => (
                <button type="button" key={m} role="radio" aria-checked={pilot.minutos === m} disabled={!pilot.ativo || !!busy}
                  className={`dk-btn is-sm${pilot.minutos === m ? " is-main" : ""}`} onClick={() => act("piloto_agenda", { minutos: m }, `min-${m}`)}>{m} min</button>
              ))}
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------ 🧰 Ferramentas
export function ToolsPanel({ api }) {
  const conv = useSkill(api);
  const clip = useSkill(api);
  const pass = useSkill(api);
  const dossier = useSkill(api);
  const [convText, setConvText] = useState("");
  const [clipOut, setClipOut] = useState("");
  const [topic, setTopic] = useState("");
  const [dossies, setDossies] = useState([]);
  const [lastDeep, setLastDeep] = useState(null);
  const loadDossies = useCallback(() => runSkill(api, "listar_dossies").then((r) => setDossies(r.data?.dossies || [])), [api]);
  useEffect(() => { loadDossies(); }, [loadDossies]);
  const openPanel = (data) => data && window.dispatchEvent(new CustomEvent("jarvis_open_deep_search", { detail: data }));

  const convert = async (e) => {
    e.preventDefault();
    if (convText.trim()) await conv.run("converter_unidades", { text: convText.trim() });
  };
  const clipAct = async (acao) => {
    setClipOut("");
    const r = await clip.run("area_de_transferencia_ia", { args: { acao } }, acao);
    setClipOut(cardText(r));
  };
  const makeDossier = async (e, again = false) => {
    e?.preventDefault?.();
    if (!topic.trim()) return;
    let r = await dossier.run("deep_brief", { args: { tema: topic.trim(), ...(again ? { uma_vez: true } : {}) } }, "dossie");
    if (r.pending && !again && window.confirm(r.speech)) {
      r = await dossier.run("deep_brief", { args: { tema: topic.trim(), uma_vez: true } }, "dossie");
    }
    const d = deepCard(r);
    if (d) { setLastDeep(d); openPanel(d); loadDossies(); }
  };
  const readDossier = async (tema) => {
    const r = await dossier.run("ler_dossie", { args: { tema } }, `ler-${tema}`);
    openPanel(deepCard(r));
  };

  return (
    <div className="dkt-grid">
      <Card title="Conversor" icon="📏">
        <form className="dk-add" onSubmit={convert}>
          <input value={convText} onChange={(e) => setConvText(e.target.value)} placeholder="5 milhas em km · 350 F em C · 2 xícaras em ml" aria-label="O que converter" />
        </form>
        <p className="dkt-big">{conv.status.text || "Medidas, peso, cozinha, temperatura, velocidade e dados. Na hora, sem internet."}</p>
      </Card>
      <Card title="Senha forte" icon="🔑">
        <p className="dk-muted">Escolha o tamanho (caracteres). A senha vai direto para a área de transferência: não aparece na tela nem é falada.</p>
        <div className="dk-row">
          {[16, 20, 32].map((n) => (
            <button type="button" key={n} className="dk-btn" title={`Senha de ${n} caracteres`} disabled={!!pass.busy}
              onClick={() => pass.run("gerar_senha", { args: { tamanho: n } }, `s${n}`)}>🔑 {n}</button>
          ))}
        </div>
        <Status {...pass.status} />
      </Card>
      <Card title="Texto copiado" icon="📋" className="dk-span2">
        <p className="dk-muted">Copie um texto (Ctrl+C) e escolha. Tradução e correção voltam para a área de transferência: é só colar.</p>
        <div className="dk-row">
          {[["resumir", "📝 RESUMIR"], ["explicar", "💡 EXPLICAR"], ["traduzir", "🌐 TRADUZIR"], ["corrigir", "✍ CORRIGIR"]].map(([acao, label]) => (
            <button type="button" key={acao} className="dk-btn" disabled={!!clip.busy} onClick={() => clipAct(acao)}>{clip.busy === acao ? "Trabalhando…" : label}</button>
          ))}
        </div>
        <Status {...clip.status} />
        {clipOut && <pre className="dkt-out">{clipOut}</pre>}
      </Card>
      <Card title="Dossiê" icon="🔎" className="dk-span2">
        <p className="dk-muted">Pesquisa um tema a fundo (vários ângulos ao mesmo tempo), fala um resumo e guarda o dossiê com as fontes. Leva de 20 s a 1 min.</p>
        <form className="dk-add" onSubmit={makeDossier}>
          <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Tema (ex.: carros elétricos no Brasil) e Enter" aria-label="Tema do dossiê" disabled={!!dossier.busy} />
        </form>
        {dossier.busy === "dossie" && <p className="dk-muted">🔎 Pesquisando… acompanhe o andamento no aviso da tela.</p>}
        <Status {...dossier.status} />
        {lastDeep && <button type="button" className="dk-btn" onClick={() => openPanel(lastDeep)}>◫ ABRIR O ÚLTIMO DOSSIÊ</button>}
        {dossies.length > 0 && (
          <>
            <small className="dk-label">SALVOS</small>
            <ul className="dk-list">
              {dossies.map((d) => (
                <li key={`${d.tema}-${d.criado}`}>
                  <span className="dkt-win"><b>{d.titulo || d.tema}</b><small>{String(d.criado || "").slice(0, 10)} · {d.fontes} fontes</small></span>
                  <button type="button" className="dk-btn is-sm" disabled={!!dossier.busy} onClick={() => readDossier(d.tema)}>▶ LER</button>
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>
    </div>
  );
}
