import { useState, useEffect } from "react";

/**
 * Widget de Lista de Tarefas (Produtividade - Fase 2).
 * Exibe tarefas pendentes, permite marcar como feita, adicionar e excluir.
 */
export default function TodoWidget({ api, onSend }) {
  const [tasks, setTasks] = useState([]);
  const [newText, setNewText] = useState("");
  const [loading, setLoading] = useState(false);

  const loadTasks = async () => {
    try {
      const data = await api("/api/tasks?include_completed=true");
      setTasks(data.tasks ?? []);
    } catch {
      /* ignora erro silencioso */
    }
  };

  useEffect(() => {
    loadTasks();
    let interval = setInterval(loadTasks, 20000);
    const onVisibility = () => {
      clearInterval(interval);
      if (!document.hidden) interval = setInterval(loadTasks, 20000);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    const txt = newText.trim();
    if (!txt) return;
    setLoading(true);
    try {
      await api("/api/tasks", {
        method: "POST",
        body: JSON.stringify({ texto: txt }),
      });
      setNewText("");
      await loadTasks();
    } catch {
      /* ignora */
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (taskId) => {
    try {
      await api(`/api/tasks/${taskId}/complete`, { method: "PATCH" });
      await loadTasks();
    } catch {
      /* ignora */
    }
  };

  const handleDelete = async (taskId) => {
    try {
      await api(`/api/tasks/${taskId}`, { method: "DELETE" });
      await loadTasks();
    } catch {
      /* ignora */
    }
  };

  const pending = tasks.filter((t) => !t.concluida);
  const completed = tasks.filter((t) => t.concluida);

  return (
    <section className="hud-panel p-4" aria-label="Tarefas">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-sm tracking-wide text-arc-200">
          Tarefas ({pending.length})
        </h2>
        <span className="text-xs text-arc-300/60">
          {pending.length === 0 ? "Tudo feito" : `${pending.length} pendente(s)`}
        </span>
      </div>

      {/* Formulário rápido */}
      <form onSubmit={handleAdd} className="mb-3 flex gap-2">
        <input
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
          placeholder="Nova tarefa..."
          className="flex-1 rounded border border-arc-700 bg-void/60 px-3 py-1.5 text-xs text-arc-100 placeholder:text-arc-300/40 focus:border-arc-300 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !newText.trim()}
          className="rounded border border-arc-400/60 bg-arc-500/15 px-3 py-1 font-display text-xs text-arc-200 hover:bg-arc-500/30 disabled:opacity-40"
        >
          +
        </button>
      </form>

      {/* Lista de tarefas pendentes */}
      <ul className="max-h-48 space-y-2 overflow-y-auto pr-1">
        {pending.length === 0 && completed.length === 0 && (
          <p className="text-xs text-arc-300/50">
            Nenhuma tarefa cadastrada. Peça por voz: <span className="text-arc-200">"adiciona comprar pão"</span>
          </p>
        )}

        {pending.map((t) => (
          <li
            key={t.id}
            className="flex items-center justify-between gap-2 rounded border border-arc-700/60 bg-void/30 px-2.5 py-1.5 text-xs text-arc-100 transition hover:border-arc-500/50"
          >
            <label className="flex flex-1 cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={false}
                onChange={() => handleToggle(t.id)}
                className="h-3.5 w-3.5 accent-arc-400"
              />
              <span className="truncate">{t.texto}</span>
            </label>
            <button
              type="button"
              onClick={() => handleDelete(t.id)}
              className="text-arc-300/40 hover:text-red-400"
              title="Excluir tarefa"
            >
              ×
            </button>
          </li>
        ))}

        {/* Concluídas recentemente */}
        {completed.slice(-2).map((t) => (
          <li
            key={t.id}
            className="flex items-center justify-between gap-2 px-2.5 py-1 text-xs text-arc-300/40 line-through"
          >
            <span className="truncate">{t.texto}</span>
            <button
              type="button"
              onClick={() => handleDelete(t.id)}
              className="hover:text-red-400"
              title="Excluir"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
