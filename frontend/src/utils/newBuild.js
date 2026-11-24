import { reloadAfterUpdate } from "./session.js";

// V8.3.1: o app do Windows (ilha e janela) carrega a interface do PC (frontend/dist). Quando a interface nova
// chega (baixada do site ou montada em segundo plano), a página aberta continuava com a antiga até fechar e
// abrir o app. Agora ela confere de tempos em tempos e se recarrega sozinha, só quando não atrapalha.

/** "/assets/index-AbC123.js" do index.html (ou "" se não achar). */
export function bundleName(html) {
  const m = String(html || "").match(/\/assets\/index-[\w-]+\.js/);
  return m ? m[0] : "";
}

/** O bundle que esta página carregou. */
export function currentBundle(doc = document) {
  for (const s of doc.querySelectorAll("script[src]")) {
    const name = bundleName(s.getAttribute("src"));
    if (name) return name;
  }
  return "";
}

/** Confere a cada `everyMs` se o PC serve uma interface nova; recarrega quando `canReload()` deixar. */
export function watchNewBuild(canReload, everyMs = 60000) {
  const mine = currentBundle();
  if (!mine) return () => {}; // modo de desenvolvimento (vite): nada a fazer
  let pending = false;
  const check = async () => {
    try {
      if (!pending) {
        const r = await fetch(`${window.location.origin}/index.html?t=${Date.now()}`, { cache: "no-store" });
        const served = bundleName(await r.text());
        pending = Boolean(served) && served !== mine;
      }
      if (pending && canReload()) reloadAfterUpdate(); // V9.4.5: sem o escaneamento facial automático depois
    } catch {
      /* JARVIS reiniciando: tenta na próxima */
    }
  };
  const t = setInterval(check, everyMs);
  return () => clearInterval(t);
}
