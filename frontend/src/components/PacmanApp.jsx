import { useEffect, useState } from "react";
import RoboAvatar from "./RoboAvatar.jsx";
import { api } from "../utils/api.js";
import "../desk.css";
import "../island.css";

// V8.6.0: MODO PAC-MAN. Uma janelinha transparente (só o avatar), que o app do Windows move atrás do mouse.
// O app avisa a fase por window.__pac(fase, direção): "corre" (boca abrindo e fechando, bravo), "mastiga" (pegou o
// mouse: mastiga rápido), "feliz" (devolveu o mouse) e "parado". Página aberta só pelo app (?pacman=1).
const FACE = { corre: "comendo", mastiga: "comendo", feliz: "rindo", parado: "bravo" };

export default function PacmanApp() {
  const [avatar, setAvatar] = useState(null);
  const [phase, setPhase] = useState("parado");
  const [left, setLeft] = useState(false);
  useEffect(() => {
    document.documentElement.classList.add("is-pacman");
    api("/api/desk/island").then((d) => setAvatar(d.avatar)).catch(() => {});
    window.__pac = (p, dir) => {
      if (p) setPhase(p);
      if (dir === "left" || dir === "right") setLeft(dir === "left");
      if (p === "corre") api("/api/desk/island").then((d) => setAvatar(d.avatar)).catch(() => {});
    };
    return () => { delete window.__pac; };
  }, []);
  return (
    <div className={`pac pac-${phase}${phase === "mastiga" ? " is-chewing" : ""}${left ? " is-left" : ""}`}>
      {phase === "mastiga" && <span className="pac-crumbs" aria-hidden="true"><i /><i /><i /></span>}
      <RoboAvatar avatar={avatar ? { ...avatar, expressao: FACE[phase] || "bravo" } : undefined} size={104} still />
      {phase === "mastiga" && <b className="pac-nhac">nhac nhac!</b>}
    </div>
  );
}
