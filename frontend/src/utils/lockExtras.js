// V9.4: ajudantes da tela de bloqueio e da central (puros, testados em tests/lockExtras.test.js).

// ---------------------------------------------------------------- clima animado
// Códigos WMO do Open-Meteo (o mesmo que o /api/weather manda em "code").
const RAIN = new Set([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]);
const SNOW = new Set([71, 73, 75, 77, 85, 86]);
const STORM = new Set([95, 96, 99]);
const FOG = new Set([45, 48]);

const toMin = (hm) => {
  const m = /^(\d{1,2}):(\d{2})/.exec(String(hm || ""));
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
};

/** É noite agora? Pelo nascer e pôr do sol do dia (sem eles, entre 18h e 6h). */
export function isNight(now, sunrise, sunset) {
  const minutes = now.getHours() * 60 + now.getMinutes();
  const up = toMin(sunrise);
  const down = toMin(sunset);
  if (up == null || down == null) return minutes >= 18 * 60 || minutes < 6 * 60;
  return minutes < up || minutes >= down;
}

/** A cena da animação: "sun" | "night" | "partly" | "partly-night" | "cloud" | "fog" | "rain" | "storm" | "snow".
 *  Sem o código (versão antiga do PC), tenta pela descrição em português. */
export function weatherScene(weather, now = new Date()) {
  if (!weather) return "cloud";
  const night = isNight(now, weather.sunrise, weather.sunset);
  let code = Number.isFinite(Number(weather.code)) && weather.code !== null && weather.code !== "" ? Number(weather.code) : null;
  if (code == null) {
    const d = String(weather.description || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    if (/trovo|tempestade|raio/.test(d)) code = 95;
    else if (/neve/.test(d)) code = 71;
    else if (/chuv|garoa|pancada/.test(d)) code = 61;
    else if (/nevoa|neblina/.test(d)) code = 45;
    else if (/parcial|poucas nuvens|nublado em parte/.test(d)) code = 2;
    else if (/nublado|encoberto|nuvens/.test(d)) code = 3;
    else code = 0;
  }
  if (STORM.has(code)) return "storm";
  if (SNOW.has(code)) return "snow";
  if (RAIN.has(code)) return "rain";
  if (FOG.has(code)) return "fog";
  if (code === 3) return "cloud";
  if (code === 1 || code === 2) return night ? "partly-night" : "partly";
  return night ? "night" : "sun";
}

// ---------------------------------------------------------------- tecla de acesso
const NOT_KEYS = new Set(["Space", "Enter", "NumpadEnter", "Escape", "Tab", "KeyP", "CapsLock", "ContextMenu",
  "ShiftLeft", "ShiftRight", "ControlLeft", "ControlRight", "AltLeft", "AltRight", "MetaLeft", "MetaRight", "OSLeft", "OSRight",
  "NumLock", "Backspace", "Delete", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "PrintScreen", "Fn"]);

/** A tecla pode ser a de acesso? (o mesmo que o PC aceita em modules/lock_key.py) */
export function isLockKeyCandidate(code) {
  if (!code || NOT_KEYS.has(code)) return false;
  return /^(Key[A-OQ-Z]|Digit[0-9]|Numpad[0-9]|F([1-9]|1[0-9]|2[0-4])|Insert|Home|End|PageUp|PageDown|Pause|ScrollLock|Backquote|Minus|Equal|BracketLeft|BracketRight|Backslash|Semicolon|Quote|Comma|Period|Slash|IntlBackslash|IntlRo)$/.test(code);
}

/** Conta como tecla apertada no bloqueio? (com Ctrl/Alt/Win é atalho do sistema; digitando num campo, também não) */
export function lockKeyPress(e) {
  if (!e || e.repeat || e.ctrlKey || e.altKey || e.metaKey) return null;
  const tag = e.target?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || e.target?.isContentEditable) return null;
  return isLockKeyCandidate(e.code) ? e.code : null;
}

/** Nome amigável ("KeyJ" -> "J", "Digit7" -> "7", "Numpad3" -> "3 (numérico)"). */
export function keyLabel(code) {
  const c = String(code || "");
  if (/^Key[A-Z]$/.test(c)) return c.slice(3);
  if (/^Digit\d$/.test(c)) return c.slice(5);
  if (/^Numpad\d$/.test(c)) return `${c.slice(6)} (numérico)`;
  return c;
}

// ---------------------------------------------------------------- Ctrl+V com imagem
/** O arquivo de imagem colado (ou null). items: DataTransferItemList ou array de { kind, type, getAsFile }. */
export function pastedImage(items) {
  for (const it of Array.from(items || [])) {
    if (it && it.kind === "file" && /^image\/(png|jpe?g|webp|gif|bmp)$/i.test(it.type || "")) {
      const f = it.getAsFile?.();
      if (f) return f;
    }
  }
  return null;
}

// ---------------------------------------------------------------- modo gravar
/** Texto do selo ⏺ GRAVANDO. rec: { active, label, steps, max } (evento "recording" do PC). */
export function recordingText(rec) {
  if (!rec?.active) return "";
  const name = rec.label ? ` · ${String(rec.label).toUpperCase()}` : "";
  const n = Number(rec.steps) || 0;
  const steps = n === 0 ? "faça os pedidos" : `${n} ${n === 1 ? "passo" : "passos"}${rec.max && n >= rec.max ? " (cheio)" : ""}`;
  return `GRAVANDO${name} · ${steps}`;
}
