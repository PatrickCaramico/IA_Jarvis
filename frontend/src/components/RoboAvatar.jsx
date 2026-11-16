import { useEffect, useId, useRef, useState } from "react";
import { ANTENNA_HATS, DEFAULT_AVATAR, lookAt, WARDROBE, withTheme } from "../utils/desk.js";
import { isLite } from "../utils/lite.js";

// V8.0: o avatar do MODO DESK: robô JARVIS (cabeça arredondada, visor escuro e olhos de luz em forma de arco-reator).
// Cores, expressão e acessório vêm de Personalizar. O estado do JARVIS manda na expressão quando ele está
// ouvindo, pensando ou falando; parado, fica a expressão escolhida (e ele pisca sozinho).
// V8.1 (ideia 7): guarda-roupa (chapéu, rosto, roupa, forma dos olhos, efeito) e temas das datas por cima.
// V8.2 (ideia 8): visual mais fofo (bochechas, olhos maiores com brilho, reflexo no visor e sombra), 7 expressões
// novas, acessórios novos, antena liga/desliga e os olhos que seguem o mouse.
// V8.4.0 (ideia 10): BRINCADEIRAS quando parado (depois de um tempo sem mexer no PC ele olha em volta, dá uma
// piscadinha, boceja e, bem depois, cochila com "zzz"; acorda quando você mexe) e o PISCAR liga/desliga.
// No modo leve não tem brincadeira.

export const EXPRESSIONS = [
  ["repouso", "Repouso"], ["ouvindo", "Ouvindo"], ["pensando", "Pensando"], ["falando", "Falando"], ["feliz", "Feliz"],
  ["rindo", "Rindo"], ["carinho", "Carinho"], ["descolado", "Descolado"], ["surpreso", "Surpreso"], ["bravo", "Bravo"],
  ["chorando", "Chorando"], ["dormindo", "Dormindo"], ["conseguiu", "Conseguiu"], ["piscando", "Piscando"],
];
export { DEFAULT_AVATAR, WARDROBE, withTheme };

/** Expressão que aparece agora: o estado do JARVIS (ouvindo, pensando, falando) vence a escolhida. */
export function faceFor(state, chosen = "feliz") {
  if (state === "listening") return "ouvindo";
  if (state === "processing") return "pensando";
  if (state === "speaking") return "falando";
  return chosen || "feliz";
}

function Eye({ cx, cy, r, color, shape = "reator" }) {
  if (shape === "coracao") {
    const k = r / 7;
    return (
      <g className="ra-eye">
        <path d={`M${cx} ${cy + 7 * k} C${cx - 11 * k} ${cy - 1 * k} ${cx - 6 * k} ${cy - 9 * k} ${cx} ${cy - 3 * k} C${cx + 6 * k} ${cy - 9 * k} ${cx + 11 * k} ${cy - 1 * k} ${cx} ${cy + 7 * k} Z`} fill={color} />
        <circle cx={cx - 3 * k} cy={cy - 3 * k} r={1.4 * k} fill="#fff" opacity="0.85" />
      </g>
    );
  }
  if (shape === "estrela") {
    const pts = Array.from({ length: 10 }, (_, i) => {
      const ang = (Math.PI / 5) * i - Math.PI / 2;
      const rr = i % 2 ? r * 0.48 : r * 1.25;
      return `${(cx + rr * Math.cos(ang)).toFixed(1)},${(cy + rr * Math.sin(ang)).toFixed(1)}`;
    }).join(" ");
    return <g className="ra-eye"><polygon points={pts} fill={color} /></g>;
  }
  if (shape === "pixel") {
    const q = r * 0.62;
    return (
      <g className="ra-eye" fill={color}>
        <rect x={cx - q * 1.5} y={cy - q * 1.5} width={q * 3} height={q * 3} opacity="0.25" />
        <rect x={cx - q} y={cy - q * 1.5} width={q * 2} height={q * 3} /><rect x={cx - q * 1.5} y={cy - q} width={q * 3} height={q * 2} />
        <rect x={cx - q} y={cy - q} width={q * 0.8} height={q * 0.8} fill="#fff" />
      </g>
    );
  }
  return (
    <g className="ra-eye">
      <circle cx={cx} cy={cy} r={r + 3} fill={color} opacity="0.18" />
      <circle cx={cx} cy={cy} r={r} fill={color} />
      <circle cx={cx} cy={cy} r={r * 0.55} fill="none" stroke="#fff" strokeOpacity="0.75" strokeWidth="1.2" />
      <circle cx={cx - r * 0.3} cy={cy - r * 0.3} r={r * 0.22} fill="#fff" opacity="0.9" />
    </g>
  );
}

function Face({ face, color, shape }) {
  const arc = (x) => <path d={`M${x - 8} 66 Q${x} 54 ${x + 8} 66`} fill="none" stroke={color} strokeWidth="4.5" strokeLinecap="round" />;
  switch (face) {
    case "feliz":
      if (shape && shape !== "reator") return <g className="ra-glow ra-blink"><Eye cx={44} cy={62} r={7} color={color} shape={shape} /><Eye cx={76} cy={62} r={7} color={color} shape={shape} /></g>;
      return <g className="ra-glow">{arc(44)}{arc(76)}</g>;
    case "piscando":
      return <g className="ra-glow"><Eye cx={44} cy={62} r={7} color={color} shape={shape} />{arc(76)}</g>;
    case "pensando":
      return (
        <g className="ra-glow">
          <Eye cx={47} cy={57} r={6} color={color} shape={shape} /><Eye cx={79} cy={57} r={6} color={color} shape={shape} />
          <g className="ra-dots" fill={color}><circle cx="52" cy="76" r="2" /><circle cx="60" cy="76" r="2" /><circle cx="68" cy="76" r="2" /></g>
        </g>
      );
    case "falando":
      return (
        <g className="ra-glow">
          <Eye cx={44} cy={58} r={7} color={color} shape={shape} /><Eye cx={76} cy={58} r={7} color={color} shape={shape} />
          <g className="ra-talk" fill={color}>
            {[48, 54, 60, 66, 72].map((x, i) => <rect key={x} x={x - 1.5} y="72" width="3" height="8" rx="1.5" style={{ animationDelay: `${i * 0.09}s` }} />)}
          </g>
        </g>
      );
    case "ouvindo":
      return (
        <g className="ra-glow">
          <Eye cx={44} cy={62} r={8} color={color} shape={shape} /><Eye cx={76} cy={62} r={8} color={color} shape={shape} />
          <circle className="ra-listen" cx="44" cy="62" r="11" fill="none" stroke={color} strokeWidth="1.5" />
          <circle className="ra-listen" cx="76" cy="62" r="11" fill="none" stroke={color} strokeWidth="1.5" />
        </g>
      );
    case "dormindo":
      return (
        <g className="ra-glow">
          <path d="M36 64 H52 M68 64 H84" stroke={color} strokeWidth="4" strokeLinecap="round" />
          <text className="ra-z" x="92" y="30" fill={color} fontSize="14" fontWeight="700">z</text>
          <text className="ra-z is-2" x="100" y="20" fill={color} fontSize="10" fontWeight="700">z</text>
        </g>
      );
    case "bocejo": // V8.4.0: brincadeira quando parado
      return (
        <g className="ra-glow">
          {[44, 76].map((x) => <path key={x} d={`M${x - 8} 62 Q${x} 57 ${x + 8} 62`} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" />)}
          <ellipse className="ra-yawn" cx="60" cy="77" rx="5" ry="6" fill={color} />
        </g>
      );
    case "repouso":
      return <g className="ra-glow">{[44, 76].map((x) => <path key={x} d={`M${x - 8} 61 Q${x} 69 ${x + 8} 61`} fill="none" stroke={color} strokeWidth="4.5" strokeLinecap="round" />)}</g>;
    case "rindo":
      return (
        <g className="ra-glow">
          {arc(44)}{arc(76)}
          <path className="ra-laugh" d="M48 72 Q60 90 72 72 Z" fill={color} />
          <path d="M53 76 Q60 84 67 76" fill="#fb7185" opacity="0.7" />
        </g>
      );
    case "carinho":
      return (
        <g className="ra-glow">
          {arc(44)}{arc(76)}
          <path d="M54 76 Q60 81 66 76" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" />
          <path className="ra-heart" d="M98 24 C92 18 88 26 98 32 C108 26 104 18 98 24 Z" fill="#fb7185" />
        </g>
      );
    case "descolado":
      return (
        <g className="ra-glow">
          <rect x="35" y="60" width="18" height="6" rx="3" fill={color} /><rect x="67" y="60" width="18" height="6" rx="3" fill={color} />
          <path d="M52 78 Q63 82 71 73" fill="none" stroke={color} strokeWidth="3.5" strokeLinecap="round" />
        </g>
      );
    case "bravo":
      return (
        <g className="ra-glow">
          <path d="M34 52 L52 58 M86 52 L68 58" stroke={color} strokeWidth="4" strokeLinecap="round" />
          <Eye cx={45} cy={65} r={5.5} color={color} shape={shape} /><Eye cx={75} cy={65} r={5.5} color={color} shape={shape} />
          <path d="M52 81 Q60 76 68 81" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" />
        </g>
      );
    case "chorando":
      return (
        <g className="ra-glow">
          <path d="M35 55 L50 51 M85 55 L70 51" stroke={color} strokeWidth="3.5" strokeLinecap="round" />
          <Eye cx={44} cy={63} r={6} color={color} shape={shape} /><Eye cx={76} cy={63} r={6} color={color} shape={shape} />
          <path d="M52 82 Q60 75 68 82" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" />
          <g className="ra-tears" fill="#7dd3fc">
            <path d="M40 72 Q38 77 40 79 Q42 77 40 72 Z" /><path d="M80 72 Q78 77 80 79 Q82 77 80 72 Z" style={{ animationDelay: "0.6s" }} />
          </g>
        </g>
      );
    case "conseguiu":
      return (
        <g className="ra-glow">
          <Eye cx={44} cy={60} r={7.5} color={color} shape="estrela" /><Eye cx={76} cy={60} r={7.5} color={color} shape="estrela" />
          <path d="M47 74 Q60 87 73 74" fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" />
          <g className="ra-fx-spark" fill="#facc15">
            {[[18, 30], [104, 40], [100, 12]].map(([x, y], i) => <path key={i} d={`M${x} ${y - 5} L${x + 1.4} ${y - 1.4} L${x + 5} ${y} L${x + 1.4} ${y + 1.4} L${x} ${y + 5} L${x - 1.4} ${y + 1.4} L${x - 5} ${y} L${x - 1.4} ${y - 1.4} Z`} style={{ animationDelay: `${i * 0.3}s` }} />)}
          </g>
        </g>
      );
    case "surpreso":
      return (
        <g className="ra-glow">
          <circle cx="44" cy="60" r="9" fill="none" stroke={color} strokeWidth="4" /><circle cx="76" cy="60" r="9" fill="none" stroke={color} strokeWidth="4" />
          <circle cx="60" cy="77" r="3.5" fill="none" stroke={color} strokeWidth="2.5" />
        </g>
      );
    default:
      return <g className="ra-glow ra-blink"><Eye cx={44} cy={62} r={8} color={color} shape={shape} /><Eye cx={76} cy={62} r={8} color={color} shape={shape} /></g>;
  }
}

function Hat({ kind, accent }) {
  switch (kind) {
    case "fone":
      return (
        <g>
          <path d="M14 58 C14 14 106 14 106 58" fill="none" stroke="#1f2937" strokeWidth="6" strokeLinecap="round" />
          <rect x="2" y="50" width="16" height="28" rx="7" fill="#111827" stroke={accent} strokeWidth="2" />
          <rect x="102" y="50" width="16" height="28" rx="7" fill="#111827" stroke={accent} strokeWidth="2" />
        </g>
      );
    case "headset":
      return (
        <g>
          <path d="M14 58 C14 12 106 12 106 58" fill="none" stroke="#111827" strokeWidth="7" strokeLinecap="round" />
          <path d="M14 58 C14 12 106 12 106 58" fill="none" stroke={accent} strokeWidth="1.5" strokeLinecap="round" opacity="0.8" />
          <rect x="0" y="48" width="18" height="32" rx="8" fill="#111827" stroke={accent} strokeWidth="2.5" />
          <rect x="102" y="48" width="18" height="32" rx="8" fill="#111827" stroke={accent} strokeWidth="2.5" />
          <path d="M10 78 Q14 98 40 96" fill="none" stroke="#111827" strokeWidth="3" strokeLinecap="round" />
          <circle cx="42" cy="96" r="4" fill={accent} />
        </g>
      );
    case "gorro":
      return (
        <g>
          <path d="M24 30 C34 4 78 -2 100 18 L104 30 Z" fill="#dc2626" />
          <rect x="18" y="24" width="88" height="12" rx="6" fill="#f8fafc" />
          <circle cx="104" cy="16" r="8" fill="#f8fafc" />
        </g>
      );
    case "coroa":
      return <path d="M34 26 L40 6 L52 20 L60 2 L68 20 L80 6 L86 26 Z" fill="#facc15" stroke="#a16207" strokeWidth="1.5" />;
    case "cartola":
      return (
        <g>
          <rect x="36" y="-2" width="48" height="28" rx="3" fill="#111827" />
          <rect x="36" y="16" width="48" height="6" fill="#b91c1c" />
          <rect x="22" y="22" width="76" height="8" rx="4" fill="#0b0f19" />
        </g>
      );
    case "bone":
      return (
        <g>
          <path d="M22 32 C24 8 96 8 98 32 Z" fill="#2563eb" />
          <path d="M60 10 V32" stroke="#1d4ed8" strokeWidth="1.5" />
          <path d="M70 30 C86 28 108 30 114 36 C104 38 84 37 70 34 Z" fill="#1e40af" />
          <circle cx="60" cy="10" r="3" fill="#1e3a8a" />
        </g>
      );
    case "bruxa":
      return (
        <g>
          <path d="M34 28 L62 -6 Q66 -8 66 -2 L78 28 Z" fill="#4c1d95" />
          <rect x="38" y="20" width="44" height="6" fill="#a3e635" />
          <ellipse cx="60" cy="29" rx="48" ry="6" fill="#3b0764" />
        </g>
      );
    case "gatinho":
      return (
        <g>
          <path d="M22 30 Q60 10 98 30" fill="none" stroke="#f472b6" strokeWidth="4" strokeLinecap="round" />
          <path d="M28 26 L30 6 L46 18 Z" fill="#f472b6" /><path d="M32 22 L33 12 L41 18 Z" fill="#fce7f3" />
          <path d="M92 26 L90 6 L74 18 Z" fill="#f472b6" /><path d="M88 22 L87 12 L79 18 Z" fill="#fce7f3" />
        </g>
      );
    case "abobora": // tema de Halloween
      return (
        <g>
          <ellipse cx="60" cy="14" rx="30" ry="15" fill="#f97316" />
          <path d="M44 3 Q40 14 44 27 M60 0 V28 M76 3 Q80 14 76 27" fill="none" stroke="#c2410c" strokeWidth="2" />
          <path d="M60 0 Q62 -8 68 -9" fill="none" stroke="#15803d" strokeWidth="4" strokeLinecap="round" />
          <path d="M50 12 L54 8 L56 13 Z M70 12 L66 8 L64 13 Z" fill="#1c1917" />
        </g>
      );
    case "aureola":
      return (
        <g className="ra-halo">
          <ellipse cx="60" cy="4" rx="26" ry="6" fill="none" stroke="#fde047" strokeWidth="4" />
          <ellipse cx="60" cy="4" rx="26" ry="6" fill="none" stroke="#fff" strokeWidth="1" opacity="0.7" />
          <circle cx="86" cy="5" r="3" fill="#bef264" />
        </g>
      );
    case "chifrinhos":
      return (
        <g fill="#ef4444" stroke="#991b1b" strokeWidth="1.2">
          <path d="M30 30 Q24 12 36 6 Q34 18 42 26 Z" /><path d="M90 30 Q96 12 84 6 Q86 18 78 26 Z" />
        </g>
      );
    case "festa":
      return (
        <g>
          <path d="M44 28 L62 -10 L80 28 Z" fill="#a855f7" />
          <path d="M50 16 L72 16 M47 23 L77 23 M55 6 L68 6" stroke="#fde047" strokeWidth="3" />
          <circle cx="62" cy="-11" r="5" fill="#f472b6" />
        </g>
      );
    case "flor":
      return (
        <g>
          {[0, 72, 144, 216, 288].map((r) => <ellipse key={r} cx="92" cy="18" rx="5" ry="8" fill="#f9a8d4" transform={`rotate(${r} 92 26)`} />)}
          <circle cx="92" cy="26" r="5" fill="#facc15" />
        </g>
      );
    case "bone_time":
      return (
        <g>
          <path d="M22 32 C24 8 96 8 98 32 Z" fill="#15803d" />
          <path d="M22 30 C24 24 96 24 98 30" fill="none" stroke="#f8fafc" strokeWidth="3" />
          <circle cx="60" cy="18" r="5" fill="#f8fafc" /><circle cx="60" cy="18" r="2.5" fill="#15803d" />
          <path d="M70 30 C86 28 108 30 114 36 C104 38 84 37 70 34 Z" fill="#14532d" />
        </g>
      );
    default:
      return null;
  }
}

function FaceItem({ kind }) {
  switch (kind) {
    case "oculos":
      return (
        <g fill="none" stroke="#f8fafc" strokeWidth="3">
          <rect x="31" y="51" width="26" height="21" rx="9" /><rect x="63" y="51" width="26" height="21" rx="9" />
          <path d="M57 60 H63" />
        </g>
      );
    case "oculos_escuros":
      return (
        <g>
          <path d="M28 52 H92 V58 Q90 72 76 72 Q64 72 62 60 H58 Q56 72 44 72 Q30 72 28 58 Z" fill="#020617" stroke="#e2e8f0" strokeWidth="2" />
          <path d="M34 56 L42 56" stroke="#fff" strokeOpacity="0.5" strokeWidth="2" strokeLinecap="round" />
        </g>
      );
    case "bigode":
      return <path d="M60 80 C54 74 42 74 38 82 C44 80 50 84 60 82 C70 84 76 80 82 82 C78 74 66 74 60 80 Z" fill="#7c4a1e" />;
    case "laco":
      return (
        <g>
          <path d="M92 26 L78 16 L80 36 Z M92 26 L106 16 L104 36 Z" fill="#ec4899" />
          <circle cx="92" cy="26" r="4" fill="#be185d" />
        </g>
      );
    default:
      return null;
  }
}

/** Roupas que ficam atrás da cabeça (capa, camisa, armadura). */
function OutfitBack({ kind, accent }) {
  if (kind === "capa") return <path d="M18 92 Q4 118 14 120 H106 Q116 118 102 92 Z" fill="#dc2626" />;
  if (kind === "camisa") {
    return (
      <g>
        <path d="M14 120 Q14 100 34 98 H86 Q106 100 106 120 Z" fill="#15803d" />
        <path d="M48 98 L60 110 L72 98" fill="none" stroke="#f8fafc" strokeWidth="3" />
        <circle cx="84" cy="112" r="3.5" fill="#f8fafc" />
      </g>
    );
  }
  if (kind === "armadura") {
    return (
      <g>
        <path d="M12 120 Q12 98 34 96 H86 Q108 98 108 120 Z" fill="#b91c1c" stroke="#facc15" strokeWidth="2" />
        <circle cx="60" cy="112" r="6" fill={accent} opacity="0.9" />
        <circle cx="60" cy="112" r="9" fill="none" stroke={accent} strokeWidth="1.5" opacity="0.6" />
      </g>
    );
  }
  return null;
}

/** Roupas que ficam na frente (cachecol, gravata). */
function OutfitFront({ kind }) {
  if (kind === "cachecol") {
    return (
      <g>
        <rect x="22" y="96" width="76" height="12" rx="6" fill="#dc2626" />
        <path d="M30 98 V108 M44 98 V108 M58 98 V108 M72 98 V108 M86 98 V108" stroke="#f8fafc" strokeWidth="3" opacity="0.8" />
        <rect x="74" y="104" width="12" height="16" rx="3" fill="#b91c1c" />
      </g>
    );
  }
  if (kind === "gravata") {
    return (
      <g>
        <path d="M60 110 L44 101 L44 119 Z M60 110 L76 101 L76 119 Z" fill="#7c3aed" />
        <rect x="56" y="106" width="8" height="8" rx="2" fill="#5b21b6" />
      </g>
    );
  }
  return null;
}

function Effect({ kind, color }) {
  if (kind === "brilho") return <circle className="ra-fx-glow" cx="60" cy="64" r="56" fill={color} opacity="0.16" />;
  if (kind === "neve") {
    return (
      <g className="ra-fx-snow" fill="#fff">
        {[[8, 0], [26, 1.2], [96, 0.5], [112, 1.8], [18, 2.4], [104, 3]].map(([x, d], i) => <circle key={i} cx={x} cy="0" r={1.6 + (i % 3) * 0.6} style={{ animationDelay: `${d}s` }} />)}
      </g>
    );
  }
  if (kind === "faiscas" || kind === "confete") {
    const colors = kind === "confete" ? ["#f43f5e", "#facc15", "#22c55e", "#3b82f6", "#a855f7", "#f97316"] : [color, "#fff", color, "#facc15", color, "#fff"];
    return (
      <g className={kind === "confete" ? "ra-fx-snow" : "ra-fx-spark"}>
        {[[10, 20], [110, 30], [6, 92], [114, 96], [100, 8], [20, 112]].map(([x, y], i) => (kind === "confete"
          ? <rect key={i} x={x} y="0" width="4" height="7" rx="1" fill={colors[i]} style={{ animationDelay: `${i * 0.5}s` }} />
          : <path key={i} d={`M${x} ${y - 5} L${x + 1.4} ${y - 1.4} L${x + 5} ${y} L${x + 1.4} ${y + 1.4} L${x} ${y + 5} L${x - 1.4} ${y + 1.4} L${x - 5} ${y} L${x - 1.4} ${y - 1.4} Z`} fill={colors[i]} style={{ animationDelay: `${i * 0.35}s` }} />))}
      </g>
    );
  }
  return null;
}

/** V8.2: olhos seguindo o mouse (suave; a velocidade vem de Personalizar). Só nos avatares grandes. */
// V8.4.0: brincadeiras quando parado (só visual, sem som)
export const FUN_AFTER_MS = 90_000; // parado 1 min e meio: começam as brincadeiras
export const SLEEP_AFTER_MS = 6 * 60_000; // parado 6 min: cochila
export const ANTICS = ["olhar", "piscando", "bocejo"];

/** A brincadeira da vez: "dormindo" depois de muito tempo; antes disso, uma das ANTICS (sorteada) ou nada. */
export function pickAntic(idleMs, rnd = Math.random()) {
  if (idleMs >= SLEEP_AFTER_MS) return "dormindo";
  if (idleMs < FUN_AFTER_MS || rnd < 0.4) return null;
  return ANTICS[Math.floor(((rnd - 0.4) / 0.6) * ANTICS.length) % ANTICS.length];
}

function useIdleFun(enabled) {
  const [antic, setAntic] = useState(null);
  useEffect(() => {
    if (!enabled || typeof window === "undefined") {
      setAntic(null);
      return undefined;
    }
    let last = Date.now();
    let next = 0;
    let undo = 0;
    const wake = () => {
      last = Date.now();
      setAntic((a) => (a ? null : a));
    };
    const tick = () => {
      const a = isLite() ? null : pickAntic(Date.now() - last);
      if (a) {
        setAntic(a);
        clearTimeout(undo);
        if (a !== "dormindo") undo = setTimeout(() => setAntic((c) => (c === a ? null : c)), 2600);
      }
      next = setTimeout(tick, 12_000 + Math.random() * 18_000);
    };
    next = setTimeout(tick, 15_000);
    const evs = ["mousemove", "keydown", "pointerdown", "wheel"];
    evs.forEach((e) => window.addEventListener(e, wake, { passive: true }));
    return () => {
      clearTimeout(next);
      clearTimeout(undo);
      evs.forEach((e) => window.removeEventListener(e, wake));
    };
  }, [enabled]);
  return enabled ? antic : null;
}

function useLook(enabled, speed) {
  const ref = useRef(null);
  const [look, setLook] = useState({ x: 0, y: 0 });
  useEffect(() => {
    if (!enabled || typeof window === "undefined" || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return undefined;
    let target = { x: 0, y: 0 };
    let cur = { x: 0, y: 0 };
    let raf = 0;
    const k = Math.min(1, 0.12 * (speed || 1));
    const tick = () => {
      cur = { x: cur.x + (target.x - cur.x) * k, y: cur.y + (target.y - cur.y) * k };
      setLook(cur);
      raf = Math.abs(target.x - cur.x) + Math.abs(target.y - cur.y) > 0.002 ? requestAnimationFrame(tick) : 0;
    };
    const move = (e) => {
      target = lookAt(e.clientX, e.clientY, ref.current?.getBoundingClientRect());
      if (!raf) raf = requestAnimationFrame(tick);
    };
    const leave = () => {
      target = { x: 0, y: 0 };
      if (!raf) raf = requestAnimationFrame(tick);
    };
    window.addEventListener("mousemove", move, { passive: true });
    document.addEventListener("mouseleave", leave);
    return () => {
      window.removeEventListener("mousemove", move);
      document.removeEventListener("mouseleave", leave);
      cancelAnimationFrame(raf);
    };
  }, [enabled, speed]);
  return [ref, enabled ? look : { x: 0, y: 0 }];
}

export default function RoboAvatar({ avatar = DEFAULT_AVATAR, tema = null, state = "idle", size = 64, className = "", still = false }) {
  const a = withTheme(avatar, tema);
  const antic = useIdleFun(!still && a.brincadeiras !== false && state === "idle"); // `still`: miniaturas (guarda-roupa)
  const face = state === "idle" && antic && antic !== "olhar" ? antic : faceFor(state, a.expressao);
  const gid = useId().replace(/:/g, "");
  const shade = `ra-shade-${gid}`;
  const gloss = `ra-gloss-${gid}`;
  const [ref, look] = useLook(size >= 60 && a.olhos_seguem !== false, Number(a.olhos_vel) || 1);
  const eyes = `translate(${(look.x * 6).toFixed(2)} ${(look.y * 4).toFixed(2)})`;
  const showAntenna = a.antena !== false && ANTENNA_HATS.includes(a.chapeu);
  return (
    <svg ref={ref} className={`ra ra-${face}${a.piscar === false ? " ra-noblink" : ""}${antic === "olhar" ? " ra-antic-olhar" : ""} ${className}`} width={size} height={size} viewBox="0 -10 120 132" overflow="visible" role="img" aria-label={`Avatar do JARVIS: ${face}`}>
      <defs>
        <linearGradient id={shade} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.55" />
          <stop offset="0.6" stopColor="#fff" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.18" />
        </linearGradient>
        <linearGradient id={gloss} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.22" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <ellipse className="ra-shadow" cx="60" cy="116" rx="34" ry="5" fill="#000" opacity="0.22" />
      {a.efeito === "brilho" && <Effect kind="brilho" color={a.olhos} />}
      <OutfitBack kind={a.roupa} accent={a.olhos} />
      {showAntenna && (
        <g className="ra-antenna">
          <path d="M60 22 V10" stroke={a.corpo} strokeWidth="4" strokeLinecap="round" />
          <circle cx="60" cy="8" r="5" fill={a.olhos} className="ra-bulb" />
        </g>
      )}
      {/* orelhas com o "arco-reator" */}
      <rect x="4" y="50" width="14" height="28" rx="6" fill={a.corpo} />
      <rect x="102" y="50" width="14" height="28" rx="6" fill={a.corpo} />
      <circle cx="11" cy="64" r="4" fill="none" stroke={a.olhos} strokeWidth="2" />
      <circle cx="109" cy="64" r="4" fill="none" stroke={a.olhos} strokeWidth="2" />
      <rect x="12" y="22" width="96" height="84" rx="36" fill={a.corpo} />
      <rect x="12" y="22" width="96" height="84" rx="36" fill={`url(#${shade})`} />
      <rect x="22" y="38" width="76" height="52" rx="24" fill={a.visor} />
      <path d="M30 44 Q34 40 52 40 L40 62 Q30 60 30 52 Z" fill={`url(#${gloss})`} />
      <rect x="26" y="41" width="40" height="7" rx="3.5" fill="#fff" opacity="0.08" />
      <g transform={eyes} className="ra-eyes">
        <ellipse className="ra-cheek" cx="32" cy="77" rx="6" ry="3.5" fill="#fb7185" opacity="0.5" />
        <ellipse className="ra-cheek" cx="88" cy="77" rx="6" ry="3.5" fill="#fb7185" opacity="0.5" />
        <Face face={face} color={a.olhos} shape={a.olhos_forma} />
      </g>
      <FaceItem kind={a.rosto} />
      <OutfitFront kind={a.roupa} />
      <Hat kind={a.chapeu} accent={a.olhos} />
      {a.efeito !== "brilho" && <Effect kind={a.efeito} color={a.olhos} />}
    </svg>
  );
}
