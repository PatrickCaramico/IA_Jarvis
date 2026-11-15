import { useEffect, useRef, useState } from "react";
import RoboAvatar from "./RoboAvatar.jsx";
import { api } from "../utils/api.js";
import { hexToRgb } from "../utils/desk.js";
import "../island.css";

// V8.0: a ILHA do JARVIS.exe: barrinha preta no topo da tela, sempre visível (como a "ilha" dos celulares).
// Em repouso: o avatar e a hora. Com música: a música tocando. Quando o JARVIS responde: a resposta, que some sozinha.
// Tocar nela mostra a janela do JARVIS. Esta página é aberta só pelo JARVIS.exe (?ilha=1).
export default function IslandApp() {
  const [st, setSt] = useState(null);
  const [track, setTrack] = useState(null);
  const lastOpen = useRef(false);

  useEffect(() => {
    document.documentElement.classList.add("is-island");
    let alive = true;
    const tick = () => api("/api/desk/island").then((d) => alive && setSt(d)).catch(() => alive && setSt((s) => s && { ...s, offline: true }));
    const music = () => api("/api/integrations/spotify/track").then((d) => alive && setTrack(d || null)).catch(() => {});
    tick();
    music();
    const a = setInterval(tick, 1200);
    const b = setInterval(music, 5000);
    return () => {
      alive = false;
      clearInterval(a);
      clearInterval(b);
    };
  }, []);

  const open = Boolean(st?.resposta);
  useEffect(() => {
    if (open !== lastOpen.current) {
      lastOpen.current = open;
      window.pywebview?.api?.island_expand?.(open);
    }
  }, [open]);

  const playing = track && track.state === "playing" && track.title;
  const estado = st?.offline ? "offline" : st?.estado || "idle";
  const face = estado === "speaking" ? "speaking" : estado === "processing" ? "processing" : "idle";
  return (
    <button type="button" className={`il il-${estado}${open ? " is-open" : ""}`} style={{ "--il-accent": st?.cor || "#22d3ee", "--il-rgb": hexToRgb(st?.cor) }}
      onClick={() => window.pywebview?.api?.show_main?.()} title="Abrir o JARVIS">
      <span className="il-row">
        <RoboAvatar avatar={st?.avatar} state={face} size={open ? 30 : 24} />
        <i className="il-dot" />
        {estado === "offline" ? <span className="il-txt">JARVIS desligado</span>
          : playing ? <span className="il-txt il-music"><b className="il-eq"><i /><i /><i /></b>{track.title}{track.artist ? ` · ${track.artist}` : ""}</span>
            : <span className="il-txt">{estado === "speaking" ? "Falando…" : estado === "processing" ? "Pensando…" : st?.hora || ""}</span>}
      </span>
      {open && <span className="il-reply">{st.resposta}</span>}
    </button>
  );
}
