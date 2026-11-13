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
import lazyComponent, { PieceBoundary } from "./utils/lazyComponent.jsx";
import { initialAccessibility, initialBackground } from "./utils/theme.js";
import { IS_JARVIS_APP, markDevice } from "./utils/device.js";
import NetworkNotice from "./components/NetworkNotice.jsx";
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

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {/* V6.7.6: um erro na tela vira um aviso com RECARREGAR, nunca mais a tela preta */}
    <PieceBoundary fullscreen>{isPopout ? <ScreensPopout /> : <App />}</PieceBoundary>
    {IS_JARVIS_APP && !isPopout && <NetworkNotice />}
  </React.StrictMode>
);
