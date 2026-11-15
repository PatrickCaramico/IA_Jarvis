import { lazy, Suspense } from "react";
import { chartGeometry, fmtNum } from "../utils/holoVisual.js";

// V7.13: a animação de cada cena do Holograma (ideia 5): gráfico, linha do tempo, mapa (globo do Olho de Deus)
// ou um diagrama de ciência animado. Tudo em SVG/CSS (o mapa carrega o globo só quando a cena pede).

const MiniGlobe = lazy(() => import("../godseye/MiniGlobe.jsx"));

function Chart({ v }) {
  const g = chartGeometry(v.dados, v.estilo);
  return (
    <figure className={`hv-chart is-${v.estilo}`}>
      {v.titulo && <figcaption>{v.titulo}{v.unidade ? <small> · {v.unidade}</small> : null}</figcaption>}
      <svg viewBox={`0 0 ${g.w} ${g.h}`} role="img" aria-label={`${v.titulo || "Gráfico"}: ${v.dados.map((d) => `${d.rotulo} ${fmtNum(d.valor)}`).join(", ")}`}>
        <line x1={g.left} x2={g.w - 8} y1={g.base} y2={g.base} className="hv-axis" />
        {v.estilo === "linha" ? (
          <>
            <path d={g.area} className="hv-area" />
            <path d={g.line} className="hv-line" pathLength="1" />
            {g.points.map((p, i) => (
              <g key={p.rotulo} className="hv-pt" style={{ animationDelay: `${0.4 + (i / g.points.length) * 1.4}s` }}>
                <circle cx={p.x} cy={p.y} r="4" />
                <text x={p.x} y={p.y - 10} textAnchor="middle" className="hv-val">{fmtNum(p.valor)}</text>
              </g>
            ))}
          </>
        ) : (
          g.points.map((p, i) => (
            <g key={p.rotulo} className="hv-bar" style={{ animationDelay: `${0.2 + i * 0.18}s` }}>
              <rect x={p.x - p.bw / 2} y={p.y} width={p.bw} height={Math.max(1, g.base - p.y)} rx="3" />
              <text x={p.x} y={p.y - 6} textAnchor="middle" className="hv-val">{fmtNum(p.valor)}</text>
            </g>
          ))
        )}
        {g.points.map((p) => <text key={`l-${p.rotulo}`} x={p.x} y={g.h - 4} textAnchor="middle" className="hv-lbl">{p.rotulo}</text>)}
      </svg>
    </figure>
  );
}

function Timeline({ v }) {
  return (
    <ol className="hv-timeline" style={{ "--n": v.marcos.length }}>
      <i className="hv-tl-line" aria-hidden="true" />
      {v.marcos.map((m, i) => (
        <li key={`${m.data}-${i}`} style={{ animationDelay: `${0.3 + i * 0.7}s` }}>
          <b>{m.data}</b>
          <span>{m.texto}</span>
        </li>
      ))}
    </ol>
  );
}

const SCIENCE_LABEL = {
  sistema_solar: "Sistema Solar", atomo: "Átomo", ciclo_agua: "Ciclo da água", coracao: "Coração",
  terra_camadas: "Camadas da Terra", dna: "DNA", celula: "Célula",
};

function Science({ modelo }) {
  let art = null;
  if (modelo === "sistema_solar") {
    art = (
      <>
        <circle cx="160" cy="110" r="16" className="hv-sun" />
        {[34, 50, 66, 84, 102].map((r, i) => (
          <g key={r}>
            <circle cx="160" cy="110" r={r} className="hv-orbit-path" />
            <g className="hv-spin" style={{ animationDuration: `${4 + i * 3}s` }}>
              <circle cx={160 + r} cy="110" r={[3, 4.5, 5, 3.5, 8][i]} className={`hv-planet p${i}`} />
            </g>
          </g>
        ))}
      </>
    );
  } else if (modelo === "atomo") {
    art = (
      <>
        <circle cx="160" cy="110" r="12" className="hv-nucleus" />
        {[0, 60, 120].map((rot, i) => (
          <g key={rot} transform={`rotate(${rot} 160 110)`}>
            <ellipse cx="160" cy="110" rx="90" ry="30" className="hv-orbit-path" />
            <circle r="5" className="hv-electron">
              <animateMotion dur={`${1.6 + i * 0.5}s`} repeatCount="indefinite" path="M250 110 A90 30 0 1 1 70 110 A90 30 0 1 1 250 110" />
            </circle>
          </g>
        ))}
      </>
    );
  } else if (modelo === "ciclo_agua") {
    art = (
      <>
        <circle cx="50" cy="40" r="18" className="hv-sun" />
        <path d="M0 190 Q40 180 80 190 T160 190 T240 190 T320 190 V220 H0Z" className="hv-sea" />
        <path d="M200 190 L250 95 L300 190Z" className="hv-mountain" />
        {[70, 100, 130].map((x, i) => <path key={x} d={`M${x} 180 Q${x + 8} 150 ${x} 120`} className="hv-vapor" style={{ animationDelay: `${i * 0.4}s` }} />)}
        <g className="hv-cloud"><ellipse cx="190" cy="50" rx="40" ry="16" /><ellipse cx="170" cy="42" rx="22" ry="14" /><ellipse cx="210" cy="40" rx="20" ry="14" /></g>
        {[175, 190, 205, 220].map((x, i) => <line key={x} x1={x} y1="70" x2={x - 4} y2="82" className="hv-drop" style={{ animationDelay: `${i * 0.25}s` }} />)}
        <text x="100" y="112" className="hv-lbl">evaporação</text><text x="160" y="22" className="hv-lbl">condensação</text><text x="232" y="88" className="hv-lbl">chuva</text>
      </>
    );
  } else if (modelo === "coracao") {
    art = (
      <>
        <path className="hv-heart" d="M160 190 C 60 120 80 40 140 55 C 152 58 158 66 160 74 C 162 66 168 58 180 55 C 240 40 260 120 160 190Z" />
        <path className="hv-ecg" pathLength="1" d="M0 110 H90 L100 90 L110 130 L122 60 L134 150 L146 110 H320" />
      </>
    );
  } else if (modelo === "terra_camadas") {
    const layers = [["crosta", 95, "#3b82f6"], ["manto", 82, "#f97316"], ["núcleo externo", 52, "#f59e0b"], ["núcleo interno", 26, "#fde047"]];
    art = (
      <>
        {layers.map(([name, r, color], i) => (
          <g key={name} className="hv-layer" style={{ animationDelay: `${i * 0.5}s` }}>
            <path d={`M${160 - r} 120 A${r} ${r} 0 0 1 ${160 + r} 120 Z`} fill={color} />
            <text x={160 + r + 6} y={120 - i * 2} className="hv-lbl" transform={`rotate(-${30 + i * 12} 160 120)`}>{name}</text>
          </g>
        ))}
      </>
    );
  } else if (modelo === "dna") {
    art = Array.from({ length: 16 }, (_, i) => (
      <g key={i} transform={`translate(${20 + i * 18} 110)`}>
        <g className="hv-rung" style={{ animationDelay: `${-i * 0.18}s` }}>
          <line x1="0" y1="-50" x2="0" y2="50" />
          <circle cy="-50" r="5" className="a" />
          <circle cy="50" r="5" className="b" />
        </g>
      </g>
    ));
  } else if (modelo === "celula") {
    art = (
      <>
        <ellipse cx="160" cy="110" rx="130" ry="88" className="hv-membrane" />
        <circle cx="150" cy="105" r="34" className="hv-nucleus" />
        <circle cx="150" cy="105" r="12" className="hv-nucleolus" />
        {[[60, 80], [235, 140], [220, 70], [90, 150]].map(([x, y], i) => (
          <g key={i} transform={`rotate(${i * 40} ${x} ${y})`}>
            <ellipse cx={x} cy={y} rx="18" ry="8" className="hv-mito" style={{ animationDelay: `${i * 0.6}s` }} />
          </g>
        ))}
        {Array.from({ length: 14 }, (_, i) => <circle key={i} cx={60 + ((i * 37) % 200)} cy={50 + ((i * 53) % 120)} r="2" className="hv-ribo" style={{ animationDelay: `${i * 0.2}s` }} />)}
        <text x="150" y="150" textAnchor="middle" className="hv-lbl">núcleo</text>
      </>
    );
  }
  if (!art) return null;
  return (
    <figure className={`hv-science is-${modelo}`}>
      <svg viewBox="0 0 320 220" role="img" aria-label={SCIENCE_LABEL[modelo]}>{art}</svg>
      <figcaption>{SCIENCE_LABEL[modelo]}</figcaption>
    </figure>
  );
}

export default function HoloVisual({ visual, lite = false }) {
  if (!visual) return null;
  if (visual.tipo === "grafico") return <Chart v={visual} />;
  if (visual.tipo === "linha_do_tempo") return <Timeline v={visual} />;
  if (visual.tipo === "ciencia") return <Science modelo={visual.modelo} />;
  if (visual.tipo === "mapa") {
    return (
      <Suspense fallback={<div className="holo-map is-loading" />}>
        <MiniGlobe lugares={visual.lugares} rota={visual.rota} lite={lite} />
      </Suspense>
    );
  }
  return null;
}
