import { weatherScene } from "../utils/lockExtras.js";
import useNow from "../hooks/useNow.js";

// V9.4: a animação do clima no cartão da tela de bloqueio ("deixa o clima sempre aparecer na tela de bloqueio").
// Sol girando, lua e estrelas, nuvens passando, chuva, raio, neblina ou neve, conforme o tempo de agora.
// Tudo em CSS com transform/opacity (nada de redesenho pesado); com "reduzir movimento", fica parado.
const DROPS = [0, 1, 2, 3, 4, 5, 6, 7];

export default function WeatherScene({ weather }) {
  const now = useNow(true);
  const scene = weatherScene(weather, now);
  const sun = scene === "sun" || scene === "partly";
  const moon = scene === "night" || scene === "partly-night";
  const clouds = scene !== "sun" && scene !== "night";
  const drops = scene === "rain" || scene === "storm" || scene === "snow";
  return (
    <div className={`ws-scene is-${scene}`} aria-hidden="true">
      {sun && <span className="ws-sun"><i /></span>}
      {moon && <span className="ws-moon" />}
      {moon && <span className="ws-stars"><i /><i /><i /><i /></span>}
      {clouds && <span className="ws-cloud ws-cloud-1" />}
      {clouds && scene !== "partly" && scene !== "partly-night" && <span className="ws-cloud ws-cloud-2" />}
      {drops && (
        <span className={scene === "snow" ? "ws-snow" : "ws-rain"}>
          {DROPS.map((i) => <i key={i} style={{ "--i": i }} />)}
        </span>
      )}
      {scene === "storm" && <span className="ws-flash" />}
      {scene === "fog" && <span className="ws-fog"><i /><i /><i /></span>}
    </div>
  );
}
