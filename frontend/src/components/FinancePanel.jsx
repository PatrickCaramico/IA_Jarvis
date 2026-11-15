import { useCallback, useEffect, useState } from "react";

// V7.10: PAINEL DE FINANÇAS (aba 💰 da Central de Agentes). Total devido, o que vence, dívidas com progresso,
// contas do mês, faturas, orçamento, metas e o PLANO para quitar (comparando os dois jeitos, com valor extra).
// Os botões PAGO/PAGAR usam a mesma ação do agente (conferida no PC). Fora de casa: só o resumo.
export const brl = (v) => `R$ ${Number(v || 0).toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, ".")}`;
const dm = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}` : "");
const TIPO = { divida: "💳", conta: "🧾", fatura: "💳" };

function Bar({ pct, tone = "" }) {
  return <div className={`fp-bar ${tone}`}><b style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} /></div>;
}

export default function FinancePanel({ api, refreshKey = 0, onAsk }) {
  const [d, setD] = useState(null);
  const [extra, setExtra] = useState(0);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(() => {
    api(`/api/finance/dashboard?extra=${encodeURIComponent(extra || 0)}`).then(setD).catch((err) => setMsg(err.message));
  }, [api, extra]);
  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const act = async (acao, key) => {
    setBusy(key);
    setMsg("");
    try {
      const r = await api("/api/agents/chat/confirm", { method: "POST", body: JSON.stringify({ agent: "financas", acao }) });
      setMsg(r.text);
      load();
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy("");
    }
  };

  if (!d) return <p className="agh-muted">{msg || "Carregando as finanças…"}</p>;
  const vazio = !d.cloud && !d.dividas?.length && !d.contas?.length && !d.cartoes?.length && !d.metas?.length && !d.orcamento?.length;
  const p = d.plano || {};
  const atrasados = d.cloud ? d.atrasados_qtd : (d.atrasados || []).length;

  return (
    <div className="fp">
      <div className="fp-kpis">
        <div><small>TOTAL DEVIDO</small><b>{brl(d.total_devido)}</b></div>
        <div><small>PARCELAS/MÊS</small><b>{brl(d.parcelas_mes)}</b></div>
        <div><small>A PAGAR NO MÊS</small><b>{brl(d.a_pagar_mes)}</b></div>
        <div className={atrasados ? "is-bad" : ""}><small>ATRASADOS</small><b>{atrasados || 0}</b></div>
      </div>
      {d.cloud && <p className="agh-muted">Fora de casa: só o resumo. Os detalhes e o plano aparecem com o PC ligado.</p>}
      {vazio && (
        <div className="fp-empty">
          <b>Vamos montar o seu controle?</b>
          <p>Conte ao agente, do seu jeito. Exemplos:</p>
          {["tenho uma dívida de R$ 5.000 no banco, parcela de 450 em 12x, já paguei 3, vence dia 10, juros de 2,5% ao mês",
            "minha conta de luz é uns 180 reais e vence dia 15",
            "meu cartão Nubank fecha dia 3 e vence dia 10",
            "quero gastar no máximo 800 de mercado por mês"].map((t) => (
            <button key={t} type="button" onClick={() => onAsk?.(t)}>“{t}”</button>
          ))}
        </div>
      )}

      {(d.proximos || []).length > 0 && (
        <section className="fp-sec">
          <h4>PRÓXIMOS VENCIMENTOS</h4>
          <ul className="fp-list">
            {d.proximos.map((v, i) => (
              <li key={`${v.tipo}-${v.nome}-${v.data}-${i}`} className={v.atrasada ? "is-late" : ""}>
                <span className="fp-date">{dm(v.data)}</span>
                <span className="fp-name">{TIPO[v.tipo]} {v.nome}{v.atrasada && <em>ATRASADA</em>}</span>
                <b>{brl(v.valor)}</b>
                {!d.cloud && (
                  <button type="button" disabled={busy === `p${i}`} onClick={() => act(
                    v.tipo === "divida" ? { tipo: "divida_pagar", nome: v.nome } : v.tipo === "conta" ? { tipo: "conta_pagar", nome: v.nome }
                      : { tipo: "fatura_pagar", nome: v.nome.replace(/^Fatura /, "") }, `p${i}`)}>✓ PAGO</button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {(d.dividas || []).filter((x) => !x.quitada).length > 0 && (
        <section className="fp-sec">
          <h4>DÍVIDAS</h4>
          {d.dividas.filter((x) => !x.quitada).map((x) => {
            const pct = x.total_parcelas ? (100 * x.pagas) / x.total_parcelas : x.saldo_inicial ? 100 * (1 - x.saldo / x.saldo_inicial) : 0;
            return (
              <div className="fp-debt" key={x.id}>
                <div className="fp-row"><b>{x.nome}</b><span>{brl(x.saldo)}</span></div>
                <Bar pct={pct} tone="is-debt" />
                <div className="fp-row fp-sub">
                  <span>{x.total_parcelas ? `${x.pagas} de ${x.total_parcelas} parcelas` : `${Math.round(pct)}% pago`} · {brl(x.parcela)}/mês · dia {x.dia}{x.juros_mes ? ` · ${String(x.juros_mes).replace(".", ",")}% a.m.` : ""}</span>
                  <button type="button" disabled={busy === x.id} onClick={() => act({ tipo: "divida_pagar", nome: x.nome }, x.id)}>PAGAR PARCELA</button>
                </div>
              </div>
            );
          })}
          {d.dividas.some((x) => x.quitada) && <p className="fp-win">🎉 Quitadas: {d.dividas.filter((x) => x.quitada).map((x) => x.nome).join(", ")}</p>}
        </section>
      )}

      {(d.contas || []).length > 0 && (
        <section className="fp-sec">
          <h4>CONTAS FIXAS DO MÊS</h4>
          <ul className="fp-list">
            {d.contas.map((c) => (
              <li key={c.id} className={c.paga_mes ? "is-paid" : ""}>
                <span className="fp-date">dia {c.dia}</span><span className="fp-name">🧾 {c.nome}</span><b>{brl(c.valor)}</b>
                {c.paga_mes ? <span className="fp-ok">✓ PAGA</span> : (
                  <button type="button" disabled={busy === c.id} onClick={() => act({ tipo: "conta_pagar", nome: c.nome }, c.id)}>PAGAR</button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {(d.cartoes || []).length > 0 && (
        <section className="fp-sec">
          <h4>CARTÕES</h4>
          {d.cartoes.map((k) => (
            <div className="fp-card" key={k.id}>
              <b>💳 {k.nome}</b><small>fecha dia {k.fechamento} · vence dia {k.vencimento}</small>
              <div className="fp-invoices">
                {k.faturas.map((f) => (
                  <span key={f.vencimento} className={f.paga ? "is-paid" : ""}><small>{dm(f.vencimento)}</small>{brl(f.valor)}{f.paga ? " ✓" : ""}</span>
                ))}
              </div>
              {k.limite > 0 && <Bar pct={(100 * (k.faturas[0]?.valor || 0)) / k.limite} />}
            </div>
          ))}
        </section>
      )}

      {(d.orcamento || []).length > 0 && (
        <section className="fp-sec">
          <h4>ORÇAMENTO DO MÊS</h4>
          {d.orcamento.map((o) => (
            <div key={o.categoria} className="fp-budget">
              <div className="fp-row"><span>{o.categoria}</span><span>{o.limite ? `${brl(o.gasto)} de ${brl(o.limite)}` : `${o.pct}%`}</span></div>
              <Bar pct={o.pct} tone={o.pct >= 100 ? "is-bad" : o.pct >= 80 ? "is-warn" : ""} />
            </div>
          ))}
        </section>
      )}

      {(d.metas || []).length > 0 && (
        <section className="fp-sec">
          <h4>METAS</h4>
          {d.metas.map((m) => (
            <div key={m.id || m.nome} className="fp-budget">
              <div className="fp-row"><span>🎯 {m.nome}</span><span>{m.alvo ? `${brl(m.guardado)} de ${brl(m.alvo)}` : `${m.pct}%`}</span></div>
              <Bar pct={m.pct} tone="is-goal" />
            </div>
          ))}
        </section>
      )}

      {p.tem_dividas && (
        <section className="fp-sec fp-plan">
          <h4>PLANO PARA QUITAR</h4>
          <label className="fp-extra">
            Posso pagar a mais por mês: <b>{brl(extra)}</b>
            <input type="range" min="0" max="2000" step="50" value={extra} onChange={(e) => setExtra(Number(e.target.value))} aria-label="Valor extra por mês" />
          </label>
          <div className="fp-compare">
            {[["bola_de_neve", "Menor dívida primeiro", "motiva: as dívidas vão sumindo"], ["avalanche", "Maior juros primeiro", "paga menos juros no total"]].map(([k, t, sub]) => (
              <div key={k} className={p.recomendado === k ? "is-best" : ""}>
                {p.recomendado === k && <em>RECOMENDADO</em>}
                <b>{t}</b><small>{sub}</small>
                <span><strong>{p[k].completo ? `${p[k].meses} meses` : "mais de 50 anos"}</strong>{p[k].completo && ` (${(p[k].meses / 12).toFixed(1).replace(".", ",")} anos)`}</span>
                <span>Juros: <strong>{brl(p[k].juros)}</strong></span>
                <span className="fp-order">1º: {p[k].foco?.[0]}</span>
              </div>
            ))}
          </div>
          <p className="fp-why">{p.motivo}</p>
        </section>
      )}
      {msg && <p className="fp-msg" role="status">{msg}</p>}
    </div>
  );
}
