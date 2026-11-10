// Tema de cores e Modo Torcedor aplicados no documento (refatoração 4.2: saíram do App.jsx).

// Aplica o tema de cores dinamicamente via variáveis CSS no :root
export function applyTheme(themeColors) {
  if (!themeColors) return;
  const root = document.documentElement;
  root.style.setProperty("--color-arc-primary", themeColors.primary);
  root.style.setProperty("--color-arc-secondary", themeColors.secondary);
  root.style.setProperty("--color-bg", themeColors.bg);
  document.body.style.backgroundColor = themeColors.bg;
}

// V4.4: fundo da interface ("blueprint" | "classic"). Fica guardado no navegador para a
// próxima abertura já começar com o fundo certo, antes das preferências chegarem do backend.
export const BG_STORAGE_KEY = "jarvis_bg";

export function applyBackground(style) {
  const value = style === "classic" ? "classic" : "blueprint";
  document.documentElement.dataset.bg = value;
  try {
    localStorage.setItem(BG_STORAGE_KEY, value);
  } catch {
    /* navegador sem armazenamento: só não lembra */
  }
}

export function initialBackground() {
  let saved = null;
  try {
    saved = localStorage.getItem(BG_STORAGE_KEY);
  } catch {
    /* ignora */
  }
  document.documentElement.dataset.bg = saved === "classic" ? "classic" : "blueprint";
}

// V4.5: acessibilidade no documento inteiro (vale no bloqueio também).
// data-text="115|130" aumenta o texto; data-contrast="high"; data-motion="reduce".
export const A11Y_STORAGE_KEY = "jarvis_a11y";

export function applyAccessibility(p) {
  if (!p) return;
  const root = document.documentElement;
  const scale = [100, 115, 130].includes(Number(p.a11y_text_scale)) ? Number(p.a11y_text_scale) : 100;
  if (scale === 100) delete root.dataset.text; else root.dataset.text = String(scale);
  if (p.a11y_high_contrast) root.dataset.contrast = "high"; else delete root.dataset.contrast;
  if (p.a11y_reduce_motion) root.dataset.motion = "reduce"; else delete root.dataset.motion;
  try {
    localStorage.setItem(A11Y_STORAGE_KEY, JSON.stringify({
      a11y_text_scale: scale, a11y_high_contrast: Boolean(p.a11y_high_contrast), a11y_reduce_motion: Boolean(p.a11y_reduce_motion),
    }));
  } catch {
    /* ignora */
  }
}

export function initialAccessibility() {
  try {
    applyAccessibility(JSON.parse(localStorage.getItem(A11Y_STORAGE_KEY) || "null"));
  } catch {
    /* ignora */
  }
}

// Aplica o Modo Torcedor (Glassmorphism) no nível do documento
export function applyFanMode(enabled, team = "palmeiras") {
  const root = document.documentElement;
  if (enabled) {
    root.dataset.mode = "fan";
    root.dataset.team = team;
  } else {
    delete root.dataset.mode;
    delete root.dataset.team;
  }
}
