// V6.4: texto do aviso de rede do app (Wi-Fi ou dados móveis). Função pura, testada em networkNotice.test.js.
const NAMES = {
  wifi: { short: "📶 Wi-Fi", speech: "no Wi-Fi" },
  cellular: { short: "📱 Dados móveis", speech: "nos dados móveis" },
  ethernet: { short: "🔌 Cabo", speech: "na rede cabeada" },
};

/**
 * @param {string} type  rede de agora ("wifi" | "cellular" | "ethernet" | "none" | "other")
 * @param {string} prev  rede da última vez que a central viu ("" na primeira vez)
 * @param {"open"|"change"} reason  abriu o app ou a rede mudou com ele aberto
 * @returns {{text: string, speech: string} | null}
 */
export function networkMessage(type, prev, reason) {
  const now = NAMES[type];
  if (!now) return null; // sem rede ou desconhecida: a tela de "reconectando" já avisa
  if (prev && prev !== type && NAMES[prev]) {
    return {
      text: `Mudança de rede: agora no ${now.short}`,
      speech: `Mudança de rede, senhor. Agora o senhor está ${now.speech}.`,
    };
  }
  if (type === "cellular" && reason === "open") {
    return {
      text: `Conectado pelos ${now.short}`,
      speech: "O senhor está conectado pela rede de dados móveis.",
    };
  }
  return null;
}
