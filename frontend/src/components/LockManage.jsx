import { useEffect, useRef, useState } from "react";

// V9.5.0: ⚙ GERENCIAR da tela de bloqueio (estilos Clássico e Sentinela). Antes eram 10 botões em duas fileiras
// embaixo do reator, encostando nos cartões. Agora ficam num menu de vidro que abre para cima; a bolinha mostra
// quantas atualizações esperam.
export default function LockManage({ children, updateCount = 0 }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); setOpen(false); } };
    document.addEventListener("pointerdown", onDown, true);
    window.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("pointerdown", onDown, true);
      window.removeEventListener("keydown", onKey, true);
    };
  }, [open]);
  return (
    <div className="lm" ref={ref} onClick={(e) => e.stopPropagation()} onKeyDown={(e) => { if (e.key === " ") e.stopPropagation(); }}>
      <button type="button" className={`lm-btn${open ? " is-open" : ""}`} aria-expanded={open} aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)} title="Atalhos do bloqueio: perfis, atualizar, Modo Desk, otimizar, diagnóstico…">
        ⚙ GERENCIAR
        {updateCount > 0 && <span className="upd-badge" aria-label={`${updateCount} ${updateCount === 1 ? "atualização disponível" : "atualizações disponíveis"}`}>{updateCount}</span>}
      </button>
      {open && (
        <div className="lm-menu" role="menu" aria-label="Gerenciar">
          <header><b>⚙ GERENCIAR</b><button type="button" onClick={() => setOpen(false)} aria-label="Fechar">✕</button></header>
          {children}
        </div>
      )}
    </div>
  );
}
