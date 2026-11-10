// Controles reaproveitados pelas abas novas de Configurações (mesmo visual do SettingsPanel).

export function Toggle({ checked, onChange, label, hint, disabled = false }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <div className="min-w-0">
        <div className="text-xs font-['Orbitron'] text-cyan-200">{label}</div>
        {hint && <div className="text-[10px] text-cyan-400/60 leading-snug">{hint}</div>}
      </div>
      <label className={`relative inline-flex items-center shrink-0 ${disabled ? "opacity-40" : "cursor-pointer"}`}>
        <input
          type="checkbox"
          className="sr-only peer"
          checked={Boolean(checked)}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          aria-label={label}
        />
        <div className="w-9 h-5 bg-black/60 border border-cyan-500/40 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-cyan-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500/30" />
      </label>
    </div>
  );
}

export function Section({ title, children, tone = "cyan" }) {
  const border = tone === "amber" ? "border-amber-500/30" : "border-cyan-500/25";
  return (
    <div className={`rounded border ${border} bg-black/40 p-3 space-y-1`}>
      <div className="text-[11px] font-['Orbitron'] tracking-wider text-cyan-300 font-semibold mb-1">{title}</div>
      {children}
    </div>
  );
}

export function Note({ children, tone = "info" }) {
  const cls = tone === "warn" ? "text-amber-300/80" : "text-cyan-300/60";
  return <p className={`text-[10px] leading-snug ${cls}`}>{children}</p>;
}

export function SelectRow({ label, value, onChange, options }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-xs font-['Orbitron'] text-cyan-200">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-cyan-500/30 bg-black/60 p-1.5 text-xs text-cyan-100"
      >
        {options.map(([v, l]) => <option key={String(v)} value={v}>{l}</option>)}
      </select>
    </div>
  );
}

export function SaveStatus({ status }) {
  if (!status) return null;
  return (
    <div className={`text-[11px] font-['Orbitron'] ${status.error ? "text-rose-400" : "text-emerald-300"}`} role="status">
      {status.error || status.ok}
    </div>
  );
}
