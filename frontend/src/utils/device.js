// V4.5: onde o JARVIS está aberto. O app Android acrescenta "JarvisApp/x.y" ao user agent.
export const IS_JARVIS_APP = typeof navigator !== "undefined" && /JarvisApp\//.test(navigator.userAgent);

export function markDevice() {
  if (typeof document === "undefined") return;
  if (IS_JARVIS_APP) document.documentElement.dataset.app = "android";
}

// Avisos no celular (só dentro do app)
export function appNotificationsEnabled() {
  try {
    return Boolean(window.JarvisApp?.notificationsEnabled?.());
  } catch {
    return false;
  }
}

export function setAppNotifications(on) {
  try {
    window.JarvisApp?.setNotifications?.(Boolean(on));
  } catch {
    /* fora do app: nada a fazer */
  }
}

// V8.0: dentro do JARVIS.exe (app para Windows com a ilha). A janela não tem o reconhecimento de voz do navegador:
// para falar, "Jarvis, …" (ouvido do PC) ou a tecla de atalho, que leva ao campo de texto.
export const IS_DESKTOP_APP = typeof navigator !== "undefined" && /JarvisDesktop\//.test(navigator.userAgent || "");
