import { useEffect, useState } from "react";

function Metric({ label, value, suffix = "" }) {
  return (
    <div className="rounded border border-arc-700/70 bg-void/30 px-2 py-1.5">
      <p className="text-[10px] text-arc-300/60">{label}</p>
      <p className="font-display text-sm text-arc-100">{value ?? "—"}{value !== null && value !== undefined && value !== "Indisponível" ? suffix : ""}</p>
    </div>
  );
}

export default function SystemMonitorWidget({ api }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let timer;
    const load = () => api("/api/system").then((value) => active && setData(value)).catch((err) => active && setError(err.message));
    const start = () => {
      if (document.hidden) return;
      load();
      timer = setInterval(load, 15000);
    };
    const onVisibility = () => {
      clearInterval(timer);
      if (!document.hidden) start();
    };
    start();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      active = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [api]);

  return (
    <section className="hud-panel p-3.5" aria-label="Monitoramento do sistema">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-display text-xs tracking-wide text-arc-200">Monitoramento</h2>
        <span className="text-[10px] text-arc-300/60">{data?.platform ?? "Sistema"}</span>
      </div>
      {error ? <p className="text-xs text-red-400">{error}</p> : (
        <div className="grid grid-cols-2 gap-1.5">
          <Metric label="CPU" value={data?.cpu_percent} suffix="%" />
          <Metric label="RAM" value={data?.ram_percent} suffix="%" />
          <Metric label="Processos" value={data?.processes} />
          <Metric label="Disco livre" value={data?.disk_free_gb} suffix=" GB" />
          <Metric label="Rede" value={data?.network} />
          <Metric label="Temperatura" value={data?.temperature} suffix=" °C" />
        </div>
      )}
    </section>
  );
}
