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
import lazyComponent from "./utils/lazyComponent.jsx";
import { initialAccessibility, initialBackground } from "./utils/theme.js";
import { IS_JARVIS_APP, markDevice } from "./utils/device.js";
import NetworkNotice from "./components/NetworkNotice.jsx";
import "./mobile.css";

initialBackground(); // V4.4: fundo blueprint/clássico antes do primeiro desenho
initialAccessibility(); // V4.5: texto maior, alto contraste e menos movimento já na primeira tela
markDevice(); // V4.5: <html data-app="android"> dentro do app do celular

// Carregados sob demanda (otimização 4.2: pacote inicial menor)
const ScreensPopout = lazyComponent(() => import("./components/ScreensPopout.jsx"));

const isPopout = window.location.pathname.endsWith("/display") || window.location.search.includes("display=secondary");

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {isPopout ? <ScreensPopout /> : <App />}
    {IS_JARVIS_APP && !isPopout && <NetworkNotice />}
  </React.StrictMode>
);
