import { useState } from "react";

export default function Onboarding({ aiName, onDone, api }) {
  const [step, setStep] = useState(1);

  // Estados dos formulários (Vídeo 2)
  const [profileData, setProfileData] = useState({
    name: "Patrick",
    treatment: "Senhor", // Senhor / Senhora
    city: "São Paulo",
    gymComment: true,
    gymTime: "18:00",
    gymDays: ["Seg", "Ter", "Qua", "Qui", "Sex"],
  });

  const [provider, setProvider] = useState("gemini"); // gemini | openai | anthropic

  const speak = (text) => {
    if (api) {
      api("/api/speak", { method: "POST", body: JSON.stringify({ text }) }).catch(() => {});
    }
  };

  const nextStep = () => {
    if (step === 1) {
      speak("Configurando o seu perfil, senhor. Como devo te chamar e qual a sua rotina?");
    } else if (step === 2) {
      speak("Excelente. Agora selecione o cérebro de inteligência artificial do JARVIS.");
    } else if (step === 3) {
      speak("Configuração assistida finalizada com sucesso. Protocolos Stark operacionais.");
      onDone();
      return;
    }
    setStep(step + 1);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-6 select-none animate-fadeIn">
      <div className="relative w-full max-w-2xl rounded-xl border border-cyan-500/40 bg-gradient-to-b from-[#082037]/95 via-[#031124]/95 to-[#020813]/98 p-8 shadow-[0_0_50px_rgba(31,194,245,0.3)]">
        {/* Cantos Táticos */}
        <div className="absolute top-2 left-2 w-3.5 h-3.5 border-t-2 border-l-2 border-cyan-400 pointer-events-none" />
        <div className="absolute top-2 right-2 w-3.5 h-3.5 border-t-2 border-r-2 border-cyan-400 pointer-events-none" />
        <div className="absolute bottom-2 left-2 w-3.5 h-3.5 border-b-2 border-l-2 border-cyan-400 pointer-events-none" />
        <div className="absolute bottom-2 right-2 w-3.5 h-3.5 border-b-2 border-r-2 border-cyan-400 pointer-events-none" />

        {/* Topo do Onboarding do Vídeo 2 */}
        <header className="mb-6 border-b border-cyan-500/20 pb-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h1 className="font-['Orbitron'] text-xl font-bold tracking-widest text-white leading-tight">
                {aiName || "JARVIS"} <span className="text-xs text-cyan-400 font-normal">· ASSISTENTE DE IA</span>
              </h1>
              <span className="text-[10px] text-cyan-300/70 font-['Orbitron'] tracking-[0.2em]">
                CONFIGURAÇÃO ASSISTIDA · ETAPA {step} / 3
              </span>
            </div>
            <span className="text-xs text-[#5eead4] font-['Orbitron'] border border-[#5eead4]/30 px-2 py-1 rounded">
              PRIMEIROS PASSOS
            </span>
          </div>

          {/* Barra de Progresso Futurista */}
          <div className="w-full h-1.5 bg-cyan-950 rounded-full overflow-hidden border border-cyan-500/30">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-[#5eead4] transition-all duration-500 shadow-[0_0_8px_#5eead4]"
              style={{ width: `${(step / 3) * 100}%` }}
            />
          </div>
        </header>

        {/* ETAPA 1: Boas-Vindas */}
        {step === 1 && (
          <div className="text-center py-6 space-y-4">
            <div className="h-20 w-20 mx-auto rounded-full border border-cyan-400/50 bg-cyan-950/40 flex items-center justify-center shadow-[0_0_25px_rgba(31,194,245,0.3)]">
              <span className="text-3xl text-cyan-300 animate-pulse">◈</span>
            </div>
            <h2 className="font-['Orbitron'] text-xl font-bold text-white tracking-wider">
              BEM-VINDO AO J.A.R.V.I.S.
            </h2>
            <p className="text-xs text-cyan-100/70 max-w-md mx-auto leading-relaxed">
              Sistema autônomo baseado em Stark OS com síntese de voz, telemetria biomédica, suporte a multi-telas e integração com modelos de inteligência artificial de ponta.
            </p>
          </div>
        )}

        {/* ETAPA 2: Quem é Você / Perfil e Rotina (Vídeo 2) */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-['Orbitron'] tracking-wider text-cyan-300 block mb-1">
                  COMO DEVO CHAMAR VOCÊ?
                </label>
                <input
                  type="text"
                  value={profileData.name}
                  onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                  className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100 focus:border-cyan-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] font-['Orbitron'] tracking-wider text-cyan-300 block mb-1">
                  TRATAMENTO PREFERIDO
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {["Senhor", "Senhora"].map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setProfileData({ ...profileData, treatment: t })}
                      className={`p-2 rounded border text-xs font-['Orbitron'] ${
                        profileData.treatment === t
                          ? "border-cyan-400 bg-cyan-500/30 text-white shadow-[0_0_8px_rgba(31,194,245,0.3)]"
                          : "border-cyan-500/20 bg-black/40 text-cyan-300/60"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <label className="text-[10px] font-['Orbitron'] tracking-wider text-cyan-300 block mb-1">
                SUA CIDADE (PARA SENSORES E CLIMA)
              </label>
              <input
                type="text"
                value={profileData.city}
                onChange={(e) => setProfileData({ ...profileData, city: e.target.value })}
                className="w-full rounded border border-cyan-500/30 bg-black/50 p-2 text-xs text-cyan-100 focus:border-cyan-400 focus:outline-none"
              />
            </div>

            {/* Rotina de Treino e Academia do Vídeo 2 */}
            <div className="p-3.5 rounded border border-cyan-500/20 bg-black/40 space-y-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-cyan-100 font-semibold">
                <input
                  type="checkbox"
                  checked={profileData.gymComment}
                  onChange={(e) => setProfileData({ ...profileData, gymComment: e.target.checked })}
                  className="accent-cyan-400"
                />
                Comentar sobre meu treino e academia ao voltar da rotina
              </label>

              <div className="flex items-center justify-between text-xs text-cyan-200/70 pt-2 border-t border-cyan-500/15">
                <span>Horário médio de retorno:</span>
                <input
                  type="time"
                  value={profileData.gymTime}
                  onChange={(e) => setProfileData({ ...profileData, gymTime: e.target.value })}
                  className="rounded border border-cyan-500/30 bg-black/60 px-2 py-0.5 text-xs text-cyan-100"
                />
              </div>
            </div>
          </div>
        )}

        {/* ETAPA 3: Cérebro da IA (Vídeo 2) */}
        {step === 3 && (
          <div className="space-y-3">
            <span className="text-xs font-['Orbitron'] tracking-wider text-cyan-300 block">
              SELEÇÃO DO CÉREBRO DE INTELIGÊNCIA ARTIFICIAL
            </span>

            {[
              { id: "gemini", name: "Google Gemini 2.5 Flash", desc: "Conversa em tempo real, visão computacional e velocidade extrema (Ativo)" },
              { id: "openai", name: "OpenAI GPT-4o", desc: "Raciocínio complexo, multitarefas e voz natural" },
              { id: "deepseek", name: "DeepSeek Chat", desc: "Modelo econômico para códigos e conversas diretas" },
            ].map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setProvider(m.id)}
                className={`w-full p-3 rounded-lg border text-left flex justify-between items-center transition ${
                  provider === m.id
                    ? "border-cyan-400 bg-cyan-950/60 shadow-[0_0_15px_rgba(31,194,245,0.3)]"
                    : "border-cyan-500/20 bg-black/40 hover:border-cyan-400/50"
                }`}
              >
                <div>
                  <strong className="block text-xs font-['Orbitron'] text-white">{m.name}</strong>
                  <p className="text-[11px] text-cyan-200/60 mt-0.5">{m.desc}</p>
                </div>
                <span className={`text-[10px] font-['Orbitron'] px-2 py-0.5 rounded border ${
                  provider === m.id ? "border-[#5eead4] text-[#5eead4] bg-emerald-950/40" : "border-cyan-500/20 text-cyan-400/40"
                }`}>
                  {provider === m.id ? "SELECIONADO" : "ESCOLHER"}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Botão de Avançar */}
        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={nextStep}
            className="px-6 py-2 rounded border border-cyan-400/80 bg-cyan-500/20 font-['Orbitron'] text-xs font-bold tracking-widest text-white shadow-[0_0_15px_rgba(31,194,245,0.3)] hover:bg-cyan-500/30 transition"
          >
            {step === 3 ? "FINALIZAR CONFIGURAÇÃO" : "CONTINUAR →"}
          </button>
        </div>
      </div>
    </div>
  );
}
