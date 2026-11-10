import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

// V4.5: opção "📱 CELULAR" na Sentinela. Um botão discreto no canto; ao tocar, abre o cartão com o
// QR para baixar o app Android (sem token: o pareamento é feito com a central liberada).
// Sem modo rede, o cartão explica como ligar (o celular não alcança o PC sem ele).
export default function MobileAppQr({ api }) {
  const [info, setInfo] = useState(null);
  const [open, setOpen] = useState(false);
  const cardRef = useRef(null);

  useEffect(() => {
    let active = true;
    const load = () => api("/api/mobile/info").then((d) => active && setInfo(d)).catch(() => active && setInfo(null));
    load();
    const t = setInterval(load, 5 * 60_000);
    return () => { active = false; clearInterval(t); };
  }, [api]);

  // Fecha sozinho depois de 60 s (é uma tela de bloqueio) e com Esc
  useEffect(() => {
    if (!open) return undefined;
    const t = setTimeout(() => setOpen(false), 60_000);
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    cardRef.current?.focus();
    return () => { clearTimeout(t); window.removeEventListener("keydown", onKey); };
  }, [open]);

  if (!info) return null;
  const ready = info.network_mode && info.download_url;

  return (
    <div className="mqr-wrap">
      {open && (
        <div className="mqr-root" ref={cardRef} tabIndex={-1} role="dialog" aria-label="JARVIS no celular" onClick={(e) => e.stopPropagation()}>
          {ready ? (
            <>
              <div className="mqr-code" aria-hidden="true">
                <QRCodeSVG value={info.download_url} size={132} bgColor="#ffffff" fgColor="#0d3170" level="M" />
              </div>
              <div className="mqr-txt">
                <b>JARVIS NO CELULAR</b>
                <span>{info.available ? "Aponte a câmera do celular para baixar o app." : "Gere o app no PC: Gerar-App-Android.bat"}</span>
                <small>ANDROID · v{info.version}{info.size_kb ? ` · ${info.size_kb} KB` : ""} · mesma Wi-Fi</small>
                <span className="mqr-step">
                  Depois de instalar, toque em <b>ABRIR O JARVIS</b> na mesma página e digite o seu PIN.
                  Endereço deste PC: <b>{(() => { try { return new URL(info.download_url).hostname; } catch { return "—"; } })()}</b>
                </span>
              </div>
            </>
          ) : (
            <div className="mqr-txt">
              <b>JARVIS NO CELULAR</b>
              <span>Para usar no celular, abra o JARVIS pelo <b>Iniciar-JARVIS-Rede.bat</b> (o celular precisa da mesma Wi-Fi).</span>
            </div>
          )}
          <button type="button" className="mqr-close" onClick={() => setOpen(false)} aria-label="Fechar">✕</button>
        </div>
      )}
      <button
        type="button"
        className={`mqr-chip ${open ? "is-open" : ""}`}
        aria-expanded={open}
        onClick={(e) => { e.stopPropagation(); e.currentTarget.blur(); setOpen((v) => !v); }}
        title="Usar o JARVIS no celular"
      >
        <span aria-hidden="true">📱</span>
        <span className="mqr-chip-txt"><b>CELULAR</b><small>{ready ? "APP ANDROID" : "MODO REDE DESLIGADO"}</small></span>
      </button>
    </div>
  );
}
