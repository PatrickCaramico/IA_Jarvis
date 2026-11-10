// Busca periódica que pausa com a aba oculta ou minimizada (otimização 4.2).
// - roda `fn` logo ao começar (immediate);
// - repete a cada `ms` enquanto a página está visível;
// - ao voltar para a aba, atualiza na hora se o último dado já passou do intervalo.
// Uso dentro de um useEffect: `return startPolling(load, 60000);` (devolve a função que para).
// `doc` só existe para os testes (padrão: document do navegador).
export function startPolling(fn, ms, { immediate = true, doc = globalThis.document } = {}) {
  let timer = null;
  let lastRun = 0;
  const run = () => {
    lastRun = Date.now();
    try {
      const result = fn();
      if (result && typeof result.catch === "function") result.catch(() => {});
    } catch {
      /* a busca trata os próprios erros */
    }
  };
  const start = () => {
    clearInterval(timer);
    timer = setInterval(run, ms);
  };
  const onVisibility = () => {
    if (doc.hidden) {
      clearInterval(timer);
      timer = null;
      return;
    }
    if (Date.now() - lastRun >= ms) run();
    start();
  };
  if (immediate) run();
  else lastRun = Date.now();
  if (!doc.hidden) start();
  doc.addEventListener("visibilitychange", onVisibility);
  return () => {
    clearInterval(timer);
    doc.removeEventListener("visibilitychange", onVisibility);
  };
}
