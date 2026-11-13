import { useEffect, useRef } from "react";

// V7.4: Esc fecha a janela DE CIMA (Agentes, Branding, Notas, Otimizar, Holograma, Câmera…).
// Antes cada janela ouvia o Esc por conta própria e o "cancelar" do App redesenhava a tela no meio do
// evento: a janela perdia o aviso e não fechava (e ainda aparecia "Ação cancelada.").
// Agora: uma pilha; só a janela mais recente fecha, e o Esc não segue para o "cancelar".
const stack = [];
let installed = false;

function onKey(e) {
  if (e.key !== "Escape" || !stack.length) return;
  e.stopImmediatePropagation();
  e.preventDefault();
  stack[stack.length - 1].current?.();
}

export default function useEscape(onClose, enabled = true) {
  const ref = useRef(onClose);
  ref.current = onClose;
  useEffect(() => {
    if (!enabled) return undefined;
    if (!installed) {
      window.addEventListener("keydown", onKey, true); // captura: antes dos outros atalhos
      installed = true;
    }
    stack.push(ref);
    return () => {
      const i = stack.lastIndexOf(ref);
      if (i >= 0) stack.splice(i, 1);
    };
  }, [enabled]);
}
