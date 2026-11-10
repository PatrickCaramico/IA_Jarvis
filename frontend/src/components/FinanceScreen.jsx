import { useEffect, useState } from "react";
import { Skeleton } from "./ui/Skeleton.jsx";

export default function FinanceScreen({ api }) {
  const [rates, setRates] = useState({});
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(true);

  useEffect(() => {
    let active = true;
    api("/api/finance")
      .then((data) => {
        if (active) {
          setRates(data.rates || {});
          setLive(data.live !== false);
          setLoading(false);
        }
      })
      .catch(() => active && setLoading(false));
    return () => { active = false; };
  }, [api]);

  const cards = [
    { key: "USDBRL", label: "DÓLAR COMERCIAL", symbol: "USD", prefix: "R$" },
    { key: "EURBRL", label: "EURO COMERCIAL",  symbol: "EUR", prefix: "R$" },
    { key: "BTCBRL", label: "BITCOIN",         symbol: "BTC", prefix: "R$" },
  ];

  return (
    <div className="hs-stack">
      {!loading && !live && (
        <p className="hs-empty" role="status">Sem conexão com a cotação: valores de referência, não atualizados.</p>
      )}
      {loading && <Skeleton block lines={2} label="Buscando cotações" />}
      {/* Cotações em destaque */}
      {!loading && <div className="hs-stats">
        {cards.map((c) => {
          const item = rates[c.key] || {};
          const val = Number(item.bid || 0);
          const pct = Number(item.pctChange || 0);
          const formatted = val >= 1000 ? val.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : val.toFixed(2);

          return (
            <div key={c.key} className="hs-stat">
              <b>{c.prefix} {formatted}</b>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
                <span>{c.label}</span>
                <span style={{ color: pct >= 0 ? "#5eead4" : "#f87171", fontWeight: "600" }}>
                  {pct >= 0 ? `+${pct.toFixed(2)}%` : `${pct.toFixed(2)}%`}
                </span>
              </div>
            </div>
          );
        })}
      </div>}

      <ExpensesPanel api={api} />
    </div>
  );
}

// V4.5: seus gastos (sem banco): o que você conta por voz ("gastei 45 no mercado") ou digita aqui.
const money = (v) => `R$ ${Number(v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function ExpensesPanel({ api }) {
  const [period, setPeriod] = useState("month");
  const [data, setData] = useState(null);
  const [amount, setAmount] = useState("");
  const [desc, setDesc] = useState("");
  const [kind, setKind] = useState("out");
  const [error, setError] = useState("");

  const load = () => api(`/api/finance/expenses?period=${period}`).then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [period]); // eslint-disable-line react-hooks/exhaustive-deps

  const add = async (e) => {
    e.preventDefault();
    const value = Number(String(amount).replace(",", "."));
    if (!value || value <= 0) { setError("Digite um valor."); return; }
    setError("");
    try {
      await api("/api/finance/expenses", { method: "POST", body: JSON.stringify({ kind, amount: value, desc }) });
      setAmount(""); setDesc("");
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const cats = Object.entries(data?.by_category || {});
  const maxCat = Math.max(1, ...cats.map(([, v]) => v));

  return (
    <div className="hs-grid hs-grid-system">
      <section className="hl-panel">
        <header className="hl-panel-head">
          <span>SEUS GASTOS</span>
          <em>
            <select value={period} onChange={(e) => setPeriod(e.target.value)} aria-label="Período"
              style={{ background: "transparent", color: "inherit", border: "none", font: "inherit" }}>
              <option value="today">HOJE</option>
              <option value="week">ESTA SEMANA</option>
              <option value="month">ESTE MÊS</option>
            </select>
          </em>
        </header>
        <div className="hl-panel-body">
          <ul className="hs-kv">
            <li><span>GASTOS</span><b>{money(data?.spent)}</b></li>
            <li><span>ENTRADAS</span><b className="ok">{money(data?.earned)}</b></li>
            <li><span>SALDO</span><b style={{ color: (data?.balance || 0) < 0 ? "#f87171" : "#5eead4" }}>{money(data?.balance)}</b></li>
          </ul>
          {cats.length > 0 && (
            <ul className="hs-kv" style={{ marginTop: 8 }}>
              {cats.slice(0, 6).map(([cat, v]) => (
                <li key={cat} style={{ position: "relative" }}>
                  <span>{cat.toUpperCase()}</span><b>{money(v)}</b>
                  <i aria-hidden="true" style={{ position: "absolute", left: 0, bottom: 0, height: 2, width: `${(v / maxCat) * 100}%`, background: "#22d3ee", opacity: 0.6 }} />
                </li>
              ))}
            </ul>
          )}
          {data && !data.items.length && (
            <p className="hs-empty">Nenhum lançamento. Diga “gastei 30 reais no mercado” ou anote ao lado.</p>
          )}
        </div>
      </section>

      <section className="hl-panel">
        <header className="hl-panel-head">
          <span>ANOTAR</span>
          <em>SEM BANCO · SÓ NESTE PC</em>
        </header>
        <form className="hl-panel-body" onSubmit={add} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", gap: 6 }}>
            {[["out", "Gasto"], ["in", "Entrada"]].map(([k, l]) => (
              <button key={k} type="button" onClick={() => setKind(k)} aria-pressed={kind === k}
                className={`hl-btn${kind === k ? " is-active" : ""}`} style={{ flex: 1 }}>{l}</button>
            ))}
          </div>
          <input value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" placeholder="Valor (ex.: 45,90)"
            className="np-input" aria-label="Valor" />
          <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Onde / o quê (ex.: mercado, uber)"
            className="np-input" aria-label="Descrição" />
          <button type="submit" className="np-btn">ANOTAR</button>
          {error && <p className="hs-empty" role="alert" style={{ color: "#fca5a5" }}>{error}</p>}
          {data?.items?.length > 0 && (
            <ul className="hs-kv" style={{ marginTop: 4 }}>
              {data.items.slice(-5).reverse().map((it, i) => (
                <li key={`${it.at}-${i}`}><span>{it.desc}</span><b className={it.kind === "in" ? "ok" : ""}>{it.kind === "in" ? "+" : "−"} {money(it.amount)}</b></li>
              ))}
            </ul>
          )}
        </form>
      </section>
    </div>
  );
}
