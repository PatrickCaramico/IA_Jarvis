import { useState } from "react";
import { Note, SaveStatus, Section } from "./SettingsControls.jsx";

const emptyForm = { name: "", url: "", apelidos: "", janela_app: false };

function normalizeUrl(url) {
  const text = (url || "").trim();
  if (!text) return "";
  if (/^https?:\/\//i.test(text)) return text;
  return `https://${text}`;
}

export default function SitesSettings({ api, sites = [], setSites }) {
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  const saveSite = async (event) => {
    event.preventDefault();
    const name = form.name.trim();
    const url = normalizeUrl(form.url);
    if (!name) {
      setError("Dê um nome para o site.");
      return;
    }
    if (!/^https?:\/\//i.test(url)) {
      setError("Use uma URL com http:// ou https://.");
      return;
    }
    const apelidos = form.apelidos.split(",").map((item) => item.trim()).filter(Boolean);
    try {
      const payload = { name, url, apelidos, janela_app: form.janela_app };
      const path = editing ? `/api/sites/${encodeURIComponent(editing)}` : "/api/sites";
      const method = editing ? "PUT" : "POST";
      const result = await api(path, { method, body: JSON.stringify(payload) });
      setSites(result.sites ?? []);
      setStatus({ ok: editing ? "Site atualizado." : "Site adicionado." });
      setError("");
      setEditing(null);
      setForm(emptyForm);
    } catch (err) {
      setStatus({ error: err.message || "Não foi possível salvar o site." });
      setError(err.message || "Não foi possível salvar o site.");
    }
  };

  const removeSite = async (site) => {
    if (!window.confirm(`Remover o site “${site.name}”?`)) return;
    try {
      const result = await api(`/api/sites/${encodeURIComponent(site.name)}`, { method: "DELETE" });
      setSites(result.sites ?? []);
      setStatus({ ok: `Site “${site.name}” removido.` });
      if (editing === site.name) {
        setEditing(null);
        setForm(emptyForm);
      }
    } catch (err) {
      setStatus({ error: err.message || "Não foi possível remover o site." });
    }
  };

  const startEdit = (site) => {
    setEditing(site.name);
    setForm({
      name: site.name,
      url: site.url,
      apelidos: (site.apelidos || []).join(", "),
      janela_app: Boolean(site.janela_app),
    });
    setError("");
  };

  return (
    <Section title="MEUS SITES">
      <form className="space-y-2" onSubmit={saveSite}>
        <input
          value={form.name}
          onChange={(event) => setForm({ ...form, name: event.target.value })}
          placeholder="Nome do site"
          className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100"
        />
        <input
          value={form.url}
          onChange={(event) => setForm({ ...form, url: event.target.value })}
          placeholder="https://mail.google.com"
          className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100"
        />
        <input
          value={form.apelidos}
          onChange={(event) => setForm({ ...form, apelidos: event.target.value })}
          placeholder="Apelidos separados por vírgula"
          className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100"
        />
        <label className="flex items-center gap-2 text-[11px] text-cyan-200/80">
          <input
            type="checkbox"
            checked={form.janela_app}
            onChange={(event) => setForm({ ...form, janela_app: event.target.checked })}
            className="rounded border-cyan-500/40 bg-black text-cyan-500"
          />
          Abrir como aplicativo (Chrome)
        </label>
        {error && <p className="text-xs text-rose-400">{error}</p>}
        <div className="flex gap-2">
          <button type="submit" className="rounded border border-cyan-500/50 bg-cyan-500/20 px-3 py-2 text-[11px] font-['Orbitron'] text-cyan-100">
            {editing ? "SALVAR SITE" : "ADICIONAR SITE"}
          </button>
          {editing && (
            <button type="button" onClick={() => { setEditing(null); setForm(emptyForm); setError(""); }} className="rounded border border-cyan-500/30 px-3 py-2 text-[11px] text-cyan-200">
              CANCELAR
            </button>
          )}
        </div>
      </form>

      <SaveStatus status={status} />

      <div className="mt-3 space-y-2">
        {sites.length === 0 && (
          <Note>Nenhum site cadastrado ainda. Use os campos acima para adicionar o primeiro.</Note>
        )}
        {sites.map((site) => {
          let hostname = "";
          try { hostname = new URL(site.url).hostname; } catch { hostname = site.name || "site"; }
          const favicon = `https://www.google.com/s2/favicons?domain=${hostname}&sz=64`;

          return (
            <div key={site.name} className="rounded border border-cyan-500/25 bg-black/30 p-2">
              <div className="flex items-start gap-3">
                <img src={favicon} alt="" className="h-8 w-8 rounded bg-black/60 object-cover" onError={(e) => { e.currentTarget.style.display = "none"; }} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-['Orbitron'] text-[11px] text-cyan-100">{site.name}</div>
                    <div className="text-[9px] text-cyan-400/70">{site.janela_app ? "Chrome app" : "Navegador"}</div>
                  </div>
                  <div className="mt-1 text-[10px] text-cyan-300/70">
                    {site.apelidos?.length ? `Apelidos: ${site.apelidos.join(", ")}` : "Sem apelidos"}
                  </div>
                  <div className="mt-1 truncate text-[10px] text-cyan-300/50">{site.url}</div>
                </div>
              </div>
              <div className="mt-2 flex gap-2">
                <button type="button" onClick={() => window.open(site.url, "_blank", "noopener,noreferrer")} className="rounded border border-cyan-500/35 bg-black/40 px-2 py-1.5 text-[10px] text-cyan-100">Testar</button>
                <button type="button" onClick={() => startEdit(site)} className="rounded border border-cyan-500/35 bg-black/40 px-2 py-1.5 text-[10px] text-cyan-100">Editar</button>
                <button type="button" onClick={() => removeSite(site)} className="rounded border border-rose-500/35 bg-black/40 px-2 py-1.5 text-[10px] text-rose-200">Remover</button>
              </div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
