// V9.0: PALETA DE COMANDOS (Ctrl+K). Acha telas, ações, frases das Skills, a memória e os copiados;
// Enter executa, setas escolhem, Esc fecha. O que não bate com nada vira pergunta para o JARVIS.
import { useEffect, useMemo, useRef, useState } from "react";
import { memoryItems, move, rank, skillItems } from "../utils/palette.js";

const KIND_LABEL = { acao: "AÇÃO", skill: "HABILIDADE", memoria: "MEMÓRIA", copiado: "COPIADO", perguntar: "PERGUNTAR" };

export default function CommandPalette({ api, actions, onClose, onSend, onAction }) {
  const [query, setQuery] = useState("");
  const [skills, setSkills] = useState([]);
  const [memory, setMemory] = useState([]);
  const [index, setIndex] = useState(0);
  const [toast, setToast] = useState("");
  const inputRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
    let alive = true;
    api("/api/skills", { timeout: 8000 })
      .then((d) => alive && setSkills(skillItems(d.items)))
      .catch(() => {}); // sem backend: a paleta segue com as ações da tela
    return () => { alive = false; };
  }, [api]);

  useEffect(() => { // memória: busca no PC com uma pausa curta enquanto digita
    const q = query.trim();
    if (q.length < 2) { setMemory([]); return undefined; }
    let alive = true;
    const t = setTimeout(() => {
      api(`/api/search/local?q=${encodeURIComponent(q)}&limit=5`, { timeout: 6000 })
        .then((d) => alive && setMemory(memoryItems(d.items)))
        .catch(() => alive && setMemory([]));
    }, 220);
    return () => { alive = false; clearTimeout(t); };
  }, [api, query]);

  const items = useMemo(() => rank([...actions, ...skills], query, memory), [actions, skills, query, memory]);
  useEffect(() => setIndex(0), [query]);
  useEffect(() => {
    listRef.current?.querySelector(`[data-idx="${index}"]`)?.scrollIntoView({ block: "nearest" });
  }, [index]);

  const run = async (item) => {
    if (!item) return;
    if (item.run.type === "copy") {
      try {
        await navigator.clipboard.writeText(item.run.text);
        setToast("Copiado ✓");
        setTimeout(onClose, 500);
      } catch {
        setToast("Não deu para copiar aqui; selecione o texto.");
      }
      return;
    }
    onClose();
    if (item.run.type === "send") onSend(item.run.text);
    else onAction(item.run.id);
  };

  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setIndex((i) => move(i, 1, items.length)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setIndex((i) => move(i, -1, items.length)); }
    else if (e.key === "Enter") { e.preventDefault(); run(items[index]); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onClose(); }
  };

  return (
    <div className="cmdk-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="cmdk" role="dialog" aria-modal="true" aria-label="Paleta de comandos">
        <div className="cmdk-head">
          <span className="cmdk-k">CTRL K</span>
          <input
            ref={inputRef}
            className="cmdk-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKey}
            placeholder="Procure uma tela, uma habilidade, algo que você falou ou copiou… ou pergunte"
            aria-label="Comando"
            spellCheck={false}
          />
        </div>
        <ul className="cmdk-list" ref={listRef} role="listbox">
          {items.map((it, i) => (
            <li key={it.id} data-idx={i} role="option" aria-selected={i === index}
              className={`cmdk-item${i === index ? " is-on" : ""} is-${it.kind}`}
              onMouseEnter={() => setIndex(i)} onClick={() => run(it)}>
              <span className="cmdk-icon" aria-hidden="true">{it.icon}</span>
              <span className="cmdk-text">
                <span className="cmdk-label">{it.label}</span>
                {it.hint && <span className="cmdk-hint">{it.hint}</span>}
              </span>
              <span className="cmdk-kind">{KIND_LABEL[it.kind] || ""}</span>
            </li>
          ))}
          {!items.length && <li className="cmdk-empty">Digite para procurar.</li>}
        </ul>
        <div className="cmdk-foot">
          {toast || <><kbd>↑</kbd><kbd>↓</kbd> escolher · <kbd>Enter</kbd> executar · <kbd>Esc</kbd> fechar</>}
        </div>
      </div>
    </div>
  );
}
