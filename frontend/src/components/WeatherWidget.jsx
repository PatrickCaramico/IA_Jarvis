import { Skeleton } from "./ui/Skeleton.jsx";
import { useCallback, useEffect, useRef, useState } from "react";

export default function WeatherWidget({ api, city, onWeatherLoaded }) {
  const [weather, setWeather] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const lastAnnouncedWeather = useRef("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api(`/api/weather${city ? `?city=${encodeURIComponent(city)}` : ""}`);
      setWeather(data);
      const signature = [
        data.place,
        data.temperature,
        data.apparent_temperature,
        data.description,
        data.maximum,
        data.minimum,
        data.rain_probability,
      ].join("|");
      if (signature !== lastAnnouncedWeather.current) {
        lastAnnouncedWeather.current = signature;
        onWeatherLoaded?.(data);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [api, city, onWeatherLoaded]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <section className="hud-panel p-4" aria-label="Clima"><Skeleton block lines={3} label="Consultando o clima" /></section>;
  if (error) return <section className="hud-panel p-4 text-sm text-red-300">{error}</section>;
  if (!weather) return null;

  return (
    <section className="hud-panel p-4" aria-label="Clima">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="font-display text-xs tracking-widest text-arc-300/70">CLIMA AGORA</p>
          <h2 className="font-display text-lg text-arc-100">{weather.place}</h2>
        </div>
        <button type="button" onClick={load} className="text-xs text-arc-300/70 hover:text-arc-100">Atualizar</button>
      </div>
      <div className="flex items-end gap-3">
        <strong className="font-display text-4xl text-arc-100">{weather.temperature}°</strong>
        <div className="pb-1 text-xs text-arc-300/80">
          <p>{weather.description}</p>
          <p>Sensação de {weather.apparent_temperature}°</p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-arc-300/80">
        <span>Máx. {weather.maximum}°</span>
        <span>Mín. {weather.minimum}°</span>
        <span>Chuva {weather.rain_probability ?? "--"}%</span>
      </div>
    </section>
  );
}
