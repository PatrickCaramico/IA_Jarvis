import { useEffect, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";

// JARVIS no celular. V4.5: duas abas — "App" (pareamento do app Android, recomendado) e
// "Navegador" (abre a central no navegador do celular, como antes).
export default function NetworkQrModal({ api, initialUrl = "", onClose }) {
  const [data, setData] = useState(initialUrl ? { url: initialUrl } : null);
  const [tab, setTab] = useState("app");
  const [status, setStatus] = useState("Descobrindo o endereço da rede…");

  useEffect(() => {
    api("/api/network-access")
      .then((d) => {
        if (!d.url) throw new Error("Não foi possível descobrir o endereço local.");
        setData(d);
        setStatus("");
      })
      .catch((error) => setStatus(
        error.message === "Not Found"
          ? "Reinicie o JARVIS para atualizar o backend e tente novamente."
          : error.message,
      ));
  }, [api]);

  const value = tab === "app" ? data?.app_pair_url || "" : data?.url || "";
  const offline = data && data.network_mode === false;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-void/85 p-4 backdrop-blur-sm">
      <section className="hud-panel w-full max-w-sm p-6 text-center shadow-arc" role="dialog" aria-modal="true" aria-label="Abrir JARVIS no celular">
        <div className="mb-4 flex items-start justify-between text-left">
          <div>
            <h2 className="font-display text-sm tracking-widest text-arc-100">JARVIS NO CELULAR</h2>
            <p className="mt-1 text-xs text-arc-300/70">Somente dispositivos na mesma rede Wi-Fi.</p>
          </div>
          <button type="button" onClick={onClose} className="text-arc-300/70 hover:text-arc-100" aria-label="Fechar">✕</button>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-1.5 rounded border border-cyan-500/20 bg-black/40 p-1" role="tablist">
          {[["app", "App Android"], ["browser", "Navegador"]].map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`rounded py-1.5 font-display text-[11px] tracking-wider ${tab === key ? "border border-cyan-400/60 bg-cyan-500/30 text-white" : "text-cyan-300/60 hover:text-cyan-200"}`}
            >
              {label}
            </button>
          ))}
        </div>

        {offline && (
          <p className="mb-3 rounded border border-amber-400/50 bg-amber-500/10 p-2 text-xs text-amber-200">
            O modo rede está desligado: o celular não alcança o PC. Abra o JARVIS pelo Iniciar-JARVIS-Rede.bat.
          </p>
        )}

        {value ? (
          <>
            <div className="mx-auto flex w-fit rounded bg-white p-3">
              <QRCodeCanvas value={value} size={220} includeMargin />
            </div>
            {tab === "app" ? (
              <ol className="mt-4 space-y-1 text-left text-xs leading-relaxed text-arc-200">
                <li>1. Ainda não tem o app? Escaneie o QR pequeno da tela de bloqueio e instale o JARVIS.apk.</li>
                <li>2. Escaneie este QR com a câmera e toque em <b>Abrir no app JARVIS</b>.</li>
                <li>3. Pronto: o app guarda a conexão e abre a central em tela cheia.</li>
              </ol>
            ) : (
              <p className="mt-4 break-all text-xs text-arc-200">{value}</p>
            )}
            <p className="mt-3 text-[11px] text-amber-200/80">Este QR tem a chave de acesso: mostre só para o seu celular.</p>
          </>
        ) : (
          <p className="py-12 text-sm text-arc-300/70">{status}</p>
        )}

        <p className="mt-5 text-xs leading-relaxed text-arc-300/60">
          O computador precisa manter o JARVIS aberto. O acesso não é publicado na internet.
        </p>
        <button type="button" onClick={onClose} className="mt-5 w-full rounded border border-arc-400/60 px-4 py-2 font-display text-xs tracking-widest text-arc-200 hover:bg-arc-500/20">
          Fechar
        </button>
      </section>
    </div>
  );
}
