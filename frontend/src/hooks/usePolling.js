import { useEffect, useRef } from "react";
import { startPolling } from "../utils/polling.js";

export { startPolling };

// Versão hook de startPolling (utils/polling.js): `usePolling(load, 60000, { enabled })`.
// `fn` pode mudar a cada render: sempre a versão mais recente é chamada.
export default function usePolling(fn, ms, { enabled = true, immediate = true } = {}) {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!enabled || !ms) return undefined;
    return startPolling(() => fnRef.current?.(), ms, { immediate });
  }, [enabled, ms, immediate]);
}
