import { useId } from "react";

// V8.0: o avatar do MODO DESK: robô JARVIS (cabeça arredondada, visor escuro e olhos de luz em forma de arco-reator).
// Cores, expressão e acessório vêm de Personalizar. O estado do JARVIS manda na expressão quando ele está
// ouvindo, pensando ou falando; parado, fica a expressão escolhida (e ele pisca sozinho).

export const EXPRESSIONS = [
  ["feliz", "Feliz"], ["pensando", "Pensando"], ["falando", "Falando"], ["ouvindo", "Ouvindo"],
  ["dormindo", "Dormindo"], ["surpreso", "Surpreso"], ["piscando", "Piscando"],
];
export const ACCESSORIES = [["nenhum", "Nenhum"], ["fone", "Fone"], ["oculos", "Óculos"], ["gorro", "Gorro de Natal"], ["coroa", "Coroa"]];
export const DEFAULT_AVATAR = { corpo: "#e8f4ff", visor: "#0b1220", olhos: "#22d3ee", expressao: "feliz", acessorio: "nenhum" };

/** Expressão que aparece agora: o estado do JARVIS (ouvindo, pensando, falando) vence a escolhida. */
export function faceFor(state, chosen = "feliz") {
  if (state === "listening") return "ouvindo";
  if (state === "processing") return "pensando";
  if (state === "speaking") return "falando";
  return chosen || "feliz";
}

function Eye({ cx, cy, r, color }) {
  return (
    <g className="ra-eye">
      <circle cx={cx} cy={cy} r={r + 3} fill={color} opacity="0.18" />
      <circle cx={cx} cy={cy} r={r} fill={color} />
      <circle cx={cx} cy={cy} r={r * 0.55} fill="none" stroke="#fff" strokeOpacity="0.75" strokeWidth="1.2" />
      <circle cx={cx - r * 0.3} cy={cy - r * 0.3} r={r * 0.22} fill="#fff" opacity="0.9" />
    </g>
  );
}

function Face({ face, color }) {
  const arc = (x) => <path d={`M${x - 8} 66 Q${x} 54 ${x + 8} 66`} fill="none" stroke={color} strokeWidth="4.5" strokeLinecap="round" />;
  switch (face) {
    case "feliz":
      return <g className="ra-glow">{arc(44)}{arc(76)}</g>;
    case "piscando":
      return <g className="ra-glow"><Eye cx={44} cy={62} r={7} color={color} />{arc(76)}</g>;
    case "pensando":
      return (
        <g className="ra-glow">
          <Eye cx={47} cy={57} r={6} color={color} /><Eye cx={79} cy={57} r={6} color={color} />
          <g className="ra-dots" fill={color}><circle cx="52" cy="76" r="2" /><circle cx="60" cy="76" r="2" /><circle cx="68" cy="76" r="2" /></g>
        </g>
      );
    case "falando":
      return (
        <g className="ra-glow">
          <Eye cx={44} cy={58} r={7} color={color} /><Eye cx={76} cy={58} r={7} color={color} />
          <g className="ra-talk" fill={color}>
            {[48, 54, 60, 66, 72].map((x, i) => <rect key={x} x={x - 1.5} y="72" width="3" height="8" rx="1.5" style={{ animationDelay: `${i * 0.09}s` }} />)}
          </g>
        </g>
      );
    case "ouvindo":
      return (
        <g className="ra-glow">
          <Eye cx={44} cy={62} r={8} color={color} /><Eye cx={76} cy={62} r={8} color={color} />
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
    case "surpreso":
      return (
        <g className="ra-glow">
          <circle cx="44" cy="60" r="9" fill="none" stroke={color} strokeWidth="4" /><circle cx="76" cy="60" r="9" fill="none" stroke={color} strokeWidth="4" />
          <circle cx="60" cy="77" r="3.5" fill="none" stroke={color} strokeWidth="2.5" />
        </g>
      );
    default:
      return <g className="ra-glow ra-blink"><Eye cx={44} cy={62} r={7} color={color} /><Eye cx={76} cy={62} r={7} color={color} /></g>;
  }
}

function Accessory({ kind, accent }) {
  if (kind === "fone") {
    return (
      <g>
        <path d="M14 58 C14 14 106 14 106 58" fill="none" stroke="#1f2937" strokeWidth="6" strokeLinecap="round" />
        <rect x="2" y="50" width="16" height="28" rx="7" fill="#111827" stroke={accent} strokeWidth="2" />
        <rect x="102" y="50" width="16" height="28" rx="7" fill="#111827" stroke={accent} strokeWidth="2" />
      </g>
    );
  }
  if (kind === "oculos") {
    return (
      <g fill="none" stroke="#f8fafc" strokeWidth="3">
        <rect x="31" y="51" width="26" height="21" rx="9" /><rect x="63" y="51" width="26" height="21" rx="9" />
        <path d="M57 60 H63" />
      </g>
    );
  }
  if (kind === "gorro") {
    return (
      <g>
        <path d="M24 30 C34 4 78 -2 100 18 L104 30 Z" fill="#dc2626" />
        <rect x="18" y="24" width="88" height="12" rx="6" fill="#f8fafc" />
        <circle cx="104" cy="16" r="8" fill="#f8fafc" />
      </g>
    );
  }
  if (kind === "coroa") {
    return <path d="M34 26 L40 6 L52 20 L60 2 L68 20 L80 6 L86 26 Z" fill="#facc15" stroke="#a16207" strokeWidth="1.5" />;
  }
  return null;
}

export default function RoboAvatar({ avatar = DEFAULT_AVATAR, state = "idle", size = 64, className = "" }) {
  const a = { ...DEFAULT_AVATAR, ...(avatar || {}) };
  const face = faceFor(state, a.expressao);
  const gid = useId().replace(/:/g, "");
  const shade = `ra-shade-${gid}`;
  return (
    <svg className={`ra ra-${face} ${className}`} width={size} height={size} viewBox="0 0 120 120" role="img" aria-label={`Avatar do JARVIS: ${face}`}>
      <defs>
        <linearGradient id={shade} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.55" />
          <stop offset="0.6" stopColor="#fff" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.18" />
        </linearGradient>
      </defs>
      {a.acessorio !== "gorro" && a.acessorio !== "coroa" && (
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
      <rect x="26" y="41" width="40" height="7" rx="3.5" fill="#fff" opacity="0.08" />
      <Face face={face} color={a.olhos} />
      <Accessory kind={a.acessorio} accent={a.olhos} />
    </svg>
  );
}
