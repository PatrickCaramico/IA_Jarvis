import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { chartGeometry, fmtNum } from "../utils/holoVisual.js";
import "../quickcard.css";

// V7.14: cartão animado das perguntas rápidas ("quanto está o dólar?", "quem ganhou o jogo?"). Aparece no canto,
// some sozinho em 18 s (para enquanto o mouse está em cima) e tem "▶ VER NO HOLOGRAMA" para a apresentação inteira.

function useWikiThumb(term) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    if (!term) return undefined;
    let alive = true;
    fetch(`https://pt.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(term.replace(/ /g, "_"))}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const s = d?.thumbnail?.source || d?.originalimage?.source;
        if (alive && s && !/\.svg/i.test(s)) setSrc(s);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [term]);
  return src;
}

function Spark({ serie }) {
  const g = chartGeometry(serie, "linha");
  return (
    <svg className="qc-spark" viewBox={`0 0 ${g.w} ${g.h}`} aria-hidden="true">
      <path d={g.area} className="hv-area" />
      <path d={g.line} className="hv-line" pathLength="1" />
    </svg>
  );
}

export default function QuickCard({ card, onClose, onHolo }) {
  const [hover, setHover] = useState(false);
  const thumb = useWikiThumb(card.tipo === "foto" ? card.wiki : "");
  useEffect(() => {
    if (hover) return undefined;
    const t = setTimeout(onClose, 18_000);
    return () => clearTimeout(t);
  }, [hover, onClose]);

  let body = null;
  if (card.tipo === "numero") {
    body = (
      <>
        <div className="qc-num"><small>{card.prefixo}</small><b>{fmtNum(card.valor)}</b><small>{card.unidade}</small></div>
        {card.rotulo && <p>{card.rotulo}</p>}
        {Array.isArray(card.serie) && card.serie.length > 1 && <Spark serie={card.serie} />}
      </>
    );
  } else if (card.tipo === "placar") {
    body = (
      <>
        <div className="qc-score">
          <span>{card.time1}</span><b>{card.gols1}</b><i>×</i><b>{card.gols2}</b><span>{card.time2}</span>
        </div>
        {card.rotulo && <p>{card.rotulo}</p>}
      </>
    );
  } else if (card.tipo === "foto") {
    body = (
      <>
        {thumb && <img className="qc-img" src={thumb} alt={card.titulo} />}
        {card.fato && <p>{card.fato}</p>}
        {thumb && <small className="qc-credit">Foto: Wikipédia</small>}
      </>
    );
  } else if (card.tipo === "lista") {
    body = <ol className="qc-list">{card.itens.map((it, i) => <li key={it} style={{ animationDelay: `${0.15 + i * 0.12}s` }}>{it}</li>)}</ol>;
  }
  if (!body) return null;

  return createPortal(
    <aside className={`qc qc-${card.tipo}`} role="status" aria-label={card.titulo || "Resposta rápida"} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      <header>
        <strong>{card.titulo}</strong>
        <button type="button" onClick={onClose} aria-label="Fechar o cartão">✕</button>
      </header>
      {body}
      <footer>
        {card.fonte && <small>{card.fonte}</small>}
        <button type="button" onClick={onHolo}>▶ VER NO HOLOGRAMA</button>
      </footer>
      <i className="qc-timer" aria-hidden="true" style={{ animationPlayState: hover ? "paused" : "running" }} />
    </aside>,
    document.body,
  );
}
