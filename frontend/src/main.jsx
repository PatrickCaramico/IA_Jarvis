import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";
import "./fan-mode.css";
import "./lock-extras.css";
import "./brand.css";
import "./feedback.css";
import "./briefing.css";
import "./blueprint.css";
import "./profiles.css";
import "./accessibility.css";
import "./alarm.css";
import "./v9.css";
import lazyComponent, { PieceBoundary } from "./utils/lazyComponent.jsx";
import { initialAccessibility, initialBackground } from "./utils/theme.js";
import { IS_JARVIS_APP, markDevice } from "./utils/device.js";
import NetworkNotice from "./components/NetworkNotice.jsx";
import SecurityLayer from "./components/SecurityLayer.jsx";
import "./mobile.css";
import "./cloud.css";

initialBackground(); // V4.4: fundo blueprint/clássico antes do primeiro desenho
initialAccessibility(); // V4.5: texto maior, alto contraste e menos movimento já na primeira tela
markDevice(); // V4.5: <html data-app="android"> dentro do app do celular
// V6.5.12: no site do Netlify aparece o selo "Powered by Netlify" no canto inferior direito;
// os botões do rodapé do bloqueio se afastam dele (ver blueprint.css)
if (/\.netlify\.app$/i.test(window.location.hostname)) document.documentElement.dataset.netlify = "1";

// Carregados sob demanda (otimização 4.2: pacote inicial menor)
const ScreensPopout = lazyComponent(() => import("./components/ScreensPopout.jsx"));

const isPopout = window.location.pathname.endsWith("/display") || window.location.search.includes("display=secondary");
// V8.0: a ilha do JARVIS.exe (barrinha no topo da tela) é uma página só dela, leve
const isIsland = new URLSearchParams(window.location.search).get("ilha") === "1";
const IslandApp = lazyComponent(() => import("./components/IslandApp.jsx"));
// V8.6.0: o avatar que corre atrás do mouse (modo Pac-Man do app do Windows)
const isPacman = new URLSearchParams(window.location.search).get("pacman") === "1";
const PacmanApp = lazyComponent(() => import("./components/PacmanApp.jsx"));

ReactDOM.createRoot(document.getElementById("root")).render(isPacman ? <PacmanApp /> : isIsland ? <IslandApp /> : (
  <React.StrictMode>
    {/* V6.7.6: um erro na tela vira um aviso com RECARREGAR, nunca mais a tela preta */}
    <PieceBoundary fullscreen>{isPopout ? <ScreensPopout /> : <App />}</PieceBoundary>
    {IS_JARVIS_APP && !isPopout && <NetworkNotice />}
    {/* V7.6: chave por aparelho e aprovação de aparelho novo, por cima de qualquer tela */}
    {!isPopout && <SecurityLayer />}
  </React.StrictMode>
));
