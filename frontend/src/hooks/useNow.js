import { useEffect, useState } from "react";
import { subscribeNow } from "../utils/clock.js";

export { subscribeNow };

// Data/hora atual atualizada pelo relógio central (utils/clock.js). `enabled=false` não assina.
export default function useNow(enabled = true) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    if (!enabled) return undefined;
    setNow(new Date());
    return subscribeNow(setNow);
  }, [enabled]);
  return now;
}
