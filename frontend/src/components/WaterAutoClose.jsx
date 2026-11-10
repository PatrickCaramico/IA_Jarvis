import { useCallback, useEffect, useRef, useState } from "react";

// Painel de água aberto por pedido ou voz: fecha sozinho após ~6 s sem interação, a menos que fixado.
export default function WaterAutoClose({ pinned, onTimeout, children }) {
  const [stamp, setStamp] = useState(0);
  const timeoutRef = useRef(onTimeout);
  timeoutRef.current = onTimeout;
  useEffect(() => {
    if (pinned) return undefined;
    const t = setTimeout(() => timeoutRef.current(), 6000);
    return () => clearTimeout(t);
  }, [pinned, stamp]);
  const touch = useCallback(() => setStamp((n) => n + 1), []);
  return (
    <div onPointerDown={touch} onKeyDown={touch} onWheel={touch}>
      {children(touch)}
    </div>
  );
}
