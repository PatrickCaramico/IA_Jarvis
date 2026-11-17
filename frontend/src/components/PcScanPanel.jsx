import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import { barTone } from "../utils/pcScan.js";

// V8.10.0 (ideia 13): VARREDURA DO PC LENTO. Abre quando você diz "meu note está lento" (o PC já manda o
// resultado) ou pelo botão. Mostra barras (CPU, memória, disco), os programas mais pesados e o que encontrou.
// CORREÇÕES SÓ COM CONFIRMAÇÃO: cada botão pede um "sim" antes de fechar programas, limpar ou esvaziar.

const ICON = { ok: "✓", warn: "!", fail: "✕" };
const CONFIRM = {
  fechar: (n) => `Fechar ${n} ${n === 1 ? "programa" : "programas"}? O que não estiver salvo nele pode ser perdido.`,
  temporarios: () => "Apagar os arquivos temporários com mais de 1 dia? Os que estão em uso são pulados.",
  lixeira: () => "Esvaziar a lixeira? Os arquivos dela somem de vez.",
};

function Bar({ label, percent, detail }) {
  const tone = barTone(percent);
  return (
    <div className={`pcs-bar is-${tone}`}>
      <span>{label}</span>
      <div className="pcs-track"><i style={{ transform: `scaleX(${Math.min(100, percent ?? 0) / 100})` }} /></div>
      <b>{percent == null ? "—" : `${Math.round(percent)}%`}</b>
      {detail && <small>{detail}</small>}
    </div>
  );
}

export default function PcScanPanel({ api, initial = null, onClose }) {
  const [data, setData] = useState(initial);
  const [busy, setBusy] = useState(!initial);
  const [error, setError] = useState("");
  const [picked, setPicked] = useState([]);
  const [ask, setAsk] = useState(null); // a correção esperando o "sim"
  const [done, setDone] = useState([]);
  useEscape(() => (ask ? setAsk(null) : onClose()));

  const run = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      setData(await api("/api/pc/scan", { timeout: 30_000 }));
      setPicked([]);
    } catch (e) {
      setError(e.message || "Não consegui rodar a varredura (o JARVIS está ligado no PC?).");
    } finally {
      setBusy(false);
    }
  }, [api]);
  useEffect(() => {
    if (!initial) run();
  }, [initial, run]);

  const fix = async (acao) => {
    setAsk(null);
    setBusy(true);
    try {
      const r = await api("/api/pc/fix", { method: "POST", body: JSON.stringify({ acao, nomes: acao === "fechar" ? picked : [] }), timeout: 60_000 });
      const msg = acao === "fechar"
        ? (r.closed?.length ? `Fechei: ${r.closed.map((c) => c.label).join(", ")}.` : "Nenhum programa foi fechado.")
        : acao === "temporarios" ? `Temporários limpos: ${r.freed} liberados (${r.removed} arquivos${r.skipped ? `, ${r.skipped} em uso pulados` : ""}).`
          : r.message;
      setDone((d) => [...d, msg]);
    } catch (e) {
      setDone((d) => [...d, e.message || "A correção não funcionou."]);
    }
    await run();
  };

  const toggle = (name) => setPicked((p) => (p.includes(name) ? p.filter((n) => n !== name) : [...p, name]));
  const fixes = data?.fixes || [];
  const tone = busy && !data ? "run" : data?.verdict || "ok";
  const verdict = busy ? "ANALISANDO O PC…" : !data ? "SEM RESULTADO" : tone === "fail" ? "ENCONTREI O QUE ESTÁ PESANDO" : tone === "warn" ? "ALGUNS PONTOS DE ATENÇÃO" : "PC TRANQUILO AGORA";

  return createPortal(
    <div className="dg-overlay" role="dialog" aria-modal="true" aria-label="Varredura do PC" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dg pcs">
        <header className="dg-head">
          <span>🔎 VARREDURA DO PC</span>
          <small>{data?.at ? `às ${data.at}` : ""}</small>
          <button type="button" className="dg-x" onClick={onClose} aria-label="Fechar">✕</button>
        </header>
        <div className={`dg-verdict is-${tone === "run" ? "run" : tone}`}>
          <i aria-hidden="true">{busy ? <span className="dg-spin" /> : ICON[tone] || "✓"}</i>
          <div>
            <strong>{verdict}</strong>
            <small>{busy ? "Medindo processador, memória, disco e programas…" : error || data?.speech}</small>
          </div>
        </div>
        {data && (
          <div className="pcs-body">
            <Bar label="Processador" percent={data.cpu_percent} />
            <Bar label="Memória" percent={data.ram_percent} detail={data.ram_total_gb ? `${String(data.ram_used_gb).replace(".", ",")} de ${String(data.ram_total_gb).replace(".", ",")} GB` : ""} />
            <Bar label="Disco" percent={data.disk_percent} detail={data.disk_free_gb != null ? `${String(data.disk_free_gb).replace(".", ",")} GB livres` : ""} />
            {data.findings?.length > 0 && (
              <ul className="dg-list">
                {data.findings.map((f) => (
                  <li key={f.id} className={`is-${f.level}`}><i aria-hidden="true">{ICON[f.level]}</i><div><span>{f.text}</span></div></li>
                ))}
              </ul>
            )}
            {data.top?.length > 0 && (
              <div className="pcs-top">
                <h4>Programas que mais pesam {fixes.includes("fechar") && <small>marque os que quer fechar</small>}</h4>
                {data.top.map((p) => (
                  <label key={p.name} className={picked.includes(p.name) ? "is-on" : ""}>
                    {fixes.includes("fechar") && <input type="checkbox" checked={picked.includes(p.name)} onChange={() => toggle(p.name)} disabled={busy} />}
                    <b>{p.label}{p.count > 1 ? <small> ×{p.count}</small> : null}</b>
                    <span>{p.mem_mb >= 1024 ? `${(p.mem_mb / 1024).toFixed(1).replace(".", ",")} GB` : `${p.mem_mb} MB`}</span>
                    <span>{Math.round(p.cpu_percent)}% CPU</span>
                  </label>
                ))}
              </div>
            )}
            {done.length > 0 && <ul className="pcs-done">{done.map((d, i) => <li key={i}>✓ {d}</li>)}</ul>}
          </div>
        )}
        {ask ? (
          <div className="pcs-ask" role="alertdialog" aria-label="Confirmar correção">
            <p>{CONFIRM[ask](picked.length)}</p>
            <div className="dg-actions">
              <button type="button" className="is-yes" onClick={() => fix(ask)}>✓ SIM, PODE</button>
              <button type="button" onClick={() => setAsk(null)}>CANCELAR</button>
            </div>
          </div>
        ) : (
          <div className="dg-actions">
            {fixes.includes("fechar") && <button type="button" onClick={() => setAsk("fechar")} disabled={busy || !picked.length}>✕ FECHAR {picked.length ? `(${picked.length})` : "SELECIONADOS"}</button>}
            {fixes.includes("temporarios") && <button type="button" onClick={() => setAsk("temporarios")} disabled={busy}>🧹 LIMPAR TEMPORÁRIOS</button>}
            {fixes.includes("lixeira") && <button type="button" onClick={() => setAsk("lixeira")} disabled={busy}>🗑 ESVAZIAR LIXEIRA</button>}
            <button type="button" onClick={run} disabled={busy}>↻ VARRER DE NOVO</button>
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
