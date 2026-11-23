// V8.13: copiar a resposta do JARVIS (botão 📋 no chat). Sem permissão da área de transferência, usa o jeito antigo.
export async function copyText(text, nav = typeof navigator !== "undefined" ? navigator : null, doc = typeof document !== "undefined" ? document : null) {
  const value = String(text || "");
  if (!value) return false;
  try {
    if (nav?.clipboard?.writeText) {
      await nav.clipboard.writeText(value);
      return true;
    }
  } catch {
    /* sem permissão: tenta o jeito antigo */
  }
  try {
    if (!doc) return false;
    const area = doc.createElement("textarea");
    area.value = value;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    doc.body.appendChild(area);
    area.select();
    const ok = doc.execCommand("copy");
    area.remove();
    return Boolean(ok);
  } catch {
    return false;
  }
}
