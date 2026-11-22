import { useCallback, useEffect, useState } from "react";
import { PERMISSIONS, groupSkills, statsText, summary, titleOf } from "../utils/skillsCatalog.js";

// V8.11: aba ⚡ HABILIDADES da Central de Agentes. Lista as Skills (backend/skills/) por grupo, com o nível de
// permissão, liga/desliga, números de uso e os exemplos (um toque manda a frase para o JARVIS).

export default function SkillsPanel({ api, onSend }) {
  const [data, setData] = useState({ items: [], errors: [] });
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(() => {
    api("/api/skills")
      .then((d) => { setData({ items: d.items || [], errors: d.errors || [] }); setError(""); })
      .catch((err) => setError(err.message || "Não consegui carregar as habilidades."))
      .finally(() => setLoaded(true));
  }, [api]);

  useEffect(() => {
    load();
    const id = setInterval(load, 15_000); // números de uso e pausas atualizados enquanto a aba está aberta
    return () => clearInterval(id);
  }, [load]);

  const toggle = async (item) => {
    setBusy(item.name);
    try {
      await api(`/api/skills/${encodeURIComponent(item.name)}/toggle`, { method: "POST", body: JSON.stringify({ enabled: !item.enabled }) });
      setData((d) => ({ ...d, items: d.items.map((i) => (i.name === item.name ? { ...i, enabled: !item.enabled } : i)) }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  };

  const groups = groupSkills(data.items, query);

  return (
    <div className="skp" aria-label="Habilidades do JARVIS">
      <div className="skp-top">
        <div>
          <b>⚡ HABILIDADES</b>
          <small>{loaded ? summary(data.items) : "carregando…"} · fale do seu jeito: a IA também usa cada uma</small>
        </div>
        <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar (janela, reunião, dossiê…)" aria-label="Buscar habilidade" />
      </div>

      <ul className="skp-legend" aria-label="Níveis de permissão">
        {Object.entries(PERMISSIONS).map(([k, p]) => (
          <li key={k}><span className={`skp-perm ${p.cls}`}>{p.label}</span> {p.hint}</li>
        ))}
      </ul>

      {error && <p className="agh-error" role="alert">{error}</p>}
      {loaded && !groups.length && <p className="agh-muted">{query ? "Nenhuma habilidade com esse nome." : "Nenhuma habilidade instalada."}</p>}

      <div className="skp-groups">
        {groups.map((g) => (
          <section key={g.key} className="skp-group">
            <h4><span aria-hidden="true">{g.icon}</span> {g.label}</h4>
            {g.items.map((item) => {
              const perm = PERMISSIONS[item.permission] || PERMISSIONS.read;
              return (
                <article key={item.name} className={`skp-item${item.enabled ? "" : " is-off"}${item.paused_s ? " is-paused" : ""}`}>
                  <header>
                    <strong>{titleOf(item)}</strong>
                    <span className={`skp-perm ${perm.cls}`} title={perm.hint}>{perm.label}</span>
                    {item.public && <span className="skp-tag" title="Funciona com a central bloqueada">🔓 BLOQUEIO</span>}
                    <button
                      type="button"
                      role="switch"
                      aria-checked={!!item.enabled}
                      aria-label={`${item.enabled ? "Desligar" : "Ligar"} ${titleOf(item)}`}
                      className={`skp-switch${item.enabled ? " is-on" : ""}`}
                      disabled={busy === item.name}
                      onClick={() => toggle(item)}
                    ><i /></button>
                  </header>
                  <p>{item.description}</p>
                  {(item.examples || []).length > 0 && (
                    <div className="skp-examples">
                      {item.examples.map((ex) => (
                        <button key={ex} type="button" disabled={!item.enabled} onClick={() => onSend?.(ex)} title="Mandar para o JARVIS">“{ex}”</button>
                      ))}
                    </div>
                  )}
                  <small className="skp-stats" title={item.last_error || ""}>{statsText(item)}{item.last_error ? " · ⚠ último erro no log" : ""}</small>
                </article>
              );
            })}
          </section>
        ))}
      </div>

      {data.errors.length > 0 && (
        <details className="skp-errors">
          <summary>⚠ {data.errors.length} habilidade(s) não carregaram</summary>
          <ul>{data.errors.map((e) => <li key={e}><code>{e}</code></li>)}</ul>
        </details>
      )}
    </div>
  );
}
