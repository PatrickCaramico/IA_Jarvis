import { useMemo, useState } from "react";
import { createPortal } from "react-dom";
import useEscape from "../hooks/useEscape.js";
import CHANGELOG from "../../../CHANGELOG.md?raw";
import { inlineParts, matches, parseChangelog } from "../utils/changelog.js";
import { APP_VERSION } from "../utils/version.js";

// V7.3: 📝 NOTAS DA VERSÃO. Cada versão do JARVIS e o que mudou nela (o mesmo CHANGELOG.md do projeto).
// Lista de versões com busca à esquerda; detalhes à direita. No celular, uma coluna só.
// Depois de uma atualização, abre sozinha uma vez mostrando a versão nova.

function Inline({ text }) {
  return inlineParts(text).map((p, i) => (p.t === "bold" ? <b key={i}>{p.v}</b> : p.t === "code" ? <code key={i}>{p.v}</code> : <span key={i}>{p.v}</span>));
}

export default function ReleaseNotes({ onClose, highlight = "" }) {
  const versions = useMemo(() => parseChangelog(CHANGELOG), []);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(highlight || versions[0]?.version || "");
  const [showList, setShowList] = useState(!highlight);
  const list = versions.filter((v) => matches(v, query));
  const current = versions.find((v) => v.version === selected) || list[0];

  useEscape(onClose);

  const pick = (v) => {
    setSelected(v);
    setShowList(false);
  };

  return createPortal(
    <div className="rn-overlay" role="dialog" aria-modal="true" aria-label="Notas da versão" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`rn${showList ? " show-list" : ""}`}>
        <header className="rn-head">
          <span>📝 NOTAS DA VERSÃO</span>
          <small>{versions.length} versões · instalada: {APP_VERSION}</small>
          <button type="button" className="rn-x" onClick={onClose} aria-label="Fechar as notas">✕</button>
        </header>
        <div className="rn-body">
          <aside className="rn-list" aria-label="Versões">
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar (ex.: câmera, trânsito, voz)" aria-label="Buscar nas notas" />
            <ul>
              {list.map((v) => (
                <li key={v.version}>
                  <button type="button" className={v.version === current?.version ? "is-on" : ""} onClick={() => pick(v.version)}>
                    <b>{v.version}</b>
                    {v.version === APP_VERSION && <i className="rn-tag">INSTALADA</i>}
                    <small>{v.date || "—"}</small>
                    <span>{(v.items.find((it) => !it.heading)?.text || "").replace(/\*\*|`/g, "").slice(0, 90)}</span>
                  </button>
                </li>
              ))}
              {list.length === 0 && <li className="rn-empty">Nada encontrado para “{query}”.</li>}
            </ul>
          </aside>
          <article className="rn-detail" key={current?.version}>
            {current ? (
              <>
                <button type="button" className="rn-back" onClick={() => setShowList(true)}>◀ TODAS AS VERSÕES</button>
                <h2>
                  Versão {current.version}
                  {current.version === APP_VERSION && <i className="rn-tag">INSTALADA</i>}
                  {highlight && current.version === highlight && <i className="rn-tag is-new">NOVA</i>}
                </h2>
                {current.date && <p className="rn-date">{current.date}</p>}
                <ul className="rn-items">
                  {current.items.map((it, i) => (it.heading ? (
                    <li key={i} className="rn-group">{it.text}</li>
                  ) : (
                    <li key={i} style={{ animationDelay: `${Math.min(i, 12) * 0.04}s` }}>
                      <Inline text={it.text} />
                      {it.sub.length > 0 && (
                        <ul>{it.sub.map((s, j) => <li key={j}><Inline text={s} /></li>)}</ul>
                      )}
                    </li>
                  )))}
                </ul>
              </>
            ) : <p className="rn-empty">Escolha uma versão.</p>}
          </article>
        </div>
      </div>
    </div>,
    document.body,
  );
}
