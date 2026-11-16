import { useEffect, useState } from "react";

// V8.4.0 (ideia 10): MODO LEVE. Ligado: menos animações, avatar parado quando não fala, ilha atualizando mais
// devagar. "auto" liga sozinho quando o PC é um notebook na bateria; "sim" sempre; "nao" nunca.

/** O modo leve está ligado? `battery`: { charging } do navegador, ou null (PC de mesa / sem informação). */
export function liteFrom(setting, battery) {
  if (setting === "sim") return true;
  if (setting === "nao") return false;
  return Boolean(battery && battery.charging === false);
}

/** Liga/desliga a classe "is-lite" na página conforme a escolha e a bateria. Devolve se está leve. */
export function useLiteMode(setting = "auto") {
  const [battery, setBattery] = useState(null);
  useEffect(() => {
    if (setting !== "auto" || typeof navigator === "undefined" || !navigator.getBattery) return undefined;
    let bat = null;
    let alive = true;
    const update = () => alive && bat && setBattery({ charging: bat.charging });
    navigator.getBattery().then((b) => {
      bat = b;
      update();
      b.addEventListener("chargingchange", update);
    }).catch(() => {});
    return () => {
      alive = false;
      bat?.removeEventListener?.("chargingchange", update);
    };
  }, [setting]);
  const lite = liteFrom(setting, battery);
  useEffect(() => {
    document.documentElement.classList.toggle("is-lite", lite);
  }, [lite]);
  return lite;
}

export const isLite = () => typeof document !== "undefined" && document.documentElement.classList.contains("is-lite");
