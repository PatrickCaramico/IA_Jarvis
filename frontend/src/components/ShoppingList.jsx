import { useEffect, useState } from "react";

// V6.0: lista de compras (a mesma do "Jarvis, coloca leite na lista"). Caixinha marca como comprado,
// ✕ tira da lista, o campo adiciona ("leite, pão e ovos" vira três itens). Atualiza ao vivo pelo
// evento "shopping" do WebSocket, então o celular e o PC ficam sempre iguais.
export default function ShoppingList({ api }) {
  const [items, setItems] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api("/api/shopping").then((d) => active && setItems(d.items || [])).catch(() => active && setItems([]));
    const onWs = (e) => {
      if (e.detail?.type === "shopping" && Array.isArray(e.detail.items)) setItems(e.detail.items);
    };
    window.addEventListener("jarvis_ws_event", onWs);
    return () => { active = false; window.removeEventListener("jarvis_ws_event", onWs); };
  }, [api]);

  const run = async (path, options) => {
    setBusy(true);
    try {
      const d = await api(path, options);
      if (d?.items) setItems(d.items);
    } catch {
      /* sem conexão: a lista volta a se acertar no próximo evento */
    } finally {
      setBusy(false);
    }
  };

  const add = (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    setText("");
    run("/api/shopping", { method: "POST", body: JSON.stringify({ texto: t }) });
  };

  if (items === null) return <p className="hl-muted" style={{ margin: 0 }}>Carregando a lista…</p>;
  const pending = items.filter((i) => !i.comprado);
  const bought = items.filter((i) => i.comprado);

  return (
    <div className="shop">
      <form className="shop-add" onSubmit={add}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder='Adicionar (ex.: "leite, pão e ovos")'
          aria-label="Adicionar à lista de compras"
          maxLength={200}
        />
        <button type="submit" disabled={!text.trim() || busy} aria-label="Adicionar">＋</button>
      </form>
      {items.length === 0 ? (
        <p className="shop-empty">Lista vazia. Diga <b>"Jarvis, coloca leite na lista"</b>.</p>
      ) : (
        <ul className="shop-list">
          {[...pending, ...bought].map((i) => (
            <li key={i.id} className={i.comprado ? "is-bought" : ""}>
              <label>
                <input
                  type="checkbox"
                  checked={Boolean(i.comprado)}
                  onChange={(e) => run(`/api/shopping/${i.id}`, { method: "PATCH", body: JSON.stringify({ comprado: e.target.checked }) })}
                />
                <span>{i.texto}</span>
              </label>
              <button type="button" className="shop-x" onClick={() => run(`/api/shopping/${i.id}`, { method: "DELETE" })} aria-label={`Tirar ${i.texto} da lista`}>✕</button>
            </li>
          ))}
        </ul>
      )}
      {bought.length > 0 && (
        <button type="button" className="shop-clear" onClick={() => run("/api/shopping/clear", { method: "POST" })} disabled={busy}>
          Limpar comprados ({bought.length})
        </button>
      )}
    </div>
  );
}
