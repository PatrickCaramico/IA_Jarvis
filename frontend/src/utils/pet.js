// V8.15: TAMAGOTCHI no bloqueio do Modo Desk. O robô vira um bichinho que precisa de você:
// 5 necessidades caem com o tempo (também com a tela fechada: a conta usa o relógio), você cuida com as ações e
// o humor dele muda (feliz, com fome, entediado, carente, sujo de bugs, com sono). Ele cresce com os dias e nunca
// morre: no pior caso fica tristinho e pede ajuda. Partes puras, testadas (node --test frontend/tests).
// O estado fica neste navegador (localStorage); as contagens do seu dia (água, missões, nível) vêm da lockface.

export const NEEDS = [
  { id: "bateria", icon: "🔋", label: "Bateria" },
  { id: "energia", icon: "⚡", label: "Energia" },
  { id: "diversao", icon: "🎾", label: "Diversão" },
  { id: "carinho", icon: "💙", label: "Carinho" },
  { id: "limpeza", icon: "✨", label: "Limpeza" },
];

// quanto cada necessidade cai por hora acordado (dormindo: a metade, e a energia sobe)
export const DECAY = { bateria: 6, energia: 4, diversao: 8, carinho: 5, limpeza: 3 };
export const SLEEP_GAIN = 25;
export const MAX_GAP_H = 72; // fechou o PC por dias: conta no máximo 3 dias (ele não "morre" de saudade)
const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const KEY = "jarvis.deskPet";

const clamp = (v) => Math.max(0, Math.min(100, Math.round(v * 10) / 10));

export function newPet(now = Date.now()) {
  return {
    v: 1, born: now, at: now, sleeping: false,
    stats: { bateria: 80, energia: 80, diversao: 70, carinho: 70, limpeza: 90 },
    count: { alimentar: 0, carinho: 0, brincar: 0, limpar: 0 },
  };
}

/** Passa o tempo: aplica a queda (ou o descanso) desde a última conta. */
export function tick(pet, now = Date.now()) {
  const h = Math.min(MAX_GAP_H, Math.max(0, (now - pet.at) / HOUR));
  if (!h) return pet;
  const stats = { ...pet.stats };
  for (const { id } of NEEDS) {
    if (pet.sleeping && id === "energia") stats[id] = clamp(stats[id] + SLEEP_GAIN * h);
    else stats[id] = clamp(stats[id] - DECAY[id] * h * (pet.sleeping ? 0.5 : 1));
  }
  return { ...pet, stats, at: now };
}

/** Bugs andando nele (aparecem com a limpeza baixa; cada um pode ser pego com um clique). */
export function bugCount(pet) {
  const l = pet.stats.limpeza;
  return l >= 75 ? 0 : Math.min(4, Math.ceil((75 - l) / 15));
}

/**
 * Uma ação de cuidado. Devolve { pet, face, say } — face/say são a reação na hora.
 * alimentar | carinho | brincar (stars = estrelas pegas no jogo) | limpar | bug | dormir | acordar
 */
export function act(pet, action, now = Date.now(), { stars = 0 } = {}) {
  const p = tick(pet, now);
  const s = { ...p.stats };
  const count = { ...(p.count || {}) };
  const done = (patch, face, say) => ({ pet: { ...p, ...patch, stats: s, count }, face, say });
  if (p.sleeping && action !== "acordar") {
    return { pet: p, face: "dormindo", say: "Psiu… tô dormindo. 😴 Toque em ☀ ACORDAR se precisar de mim." };
  }
  switch (action) {
    case "alimentar":
      if (s.bateria >= 95) return { pet: p, face: "surpreso", say: "Tô cheio! Não cabe mais nada. 🔋✋" };
      s.bateria = clamp(s.bateria + 30);
      s.limpeza = clamp(s.limpeza - 4); // farelinho de bateria (vira bug se não limpar)
      count.alimentar = (count.alimentar || 0) + 1;
      return done({}, "comendo", s.bateria >= 95 ? "Hmm, carga completa! Obrigado. 🔋💙" : "Nhac! Que bateria gostosa. 🔋");
    case "carinho":
      s.carinho = clamp(s.carinho + 20);
      s.diversao = clamp(s.diversao + 4);
      count.carinho = (count.carinho || 0) + 1;
      return done({}, "carinho", s.carinho >= 95 ? "Eu também gosto muito de você! 💙💙" : "Hehe, que bom! 💙");
    case "brincar": {
      const gain = Math.min(45, 10 + stars * 3);
      s.diversao = clamp(s.diversao + gain);
      s.energia = clamp(s.energia - 8);
      s.bateria = clamp(s.bateria - 4);
      count.brincar = (count.brincar || 0) + 1;
      return done({}, stars >= 10 ? "conseguiu" : "rindo", stars >= 10 ? "Que partida! Você é muito bom nisso! 🏆" : "Foi divertido! Bora de novo depois? 🎾");
    }
    case "bug":
      s.limpeza = clamp(s.limpeza + 15);
      return done({}, "rindo", "Peguei! Menos um bug. 🐛✨");
    case "limpar":
      if (s.limpeza >= 95) return { pet: p, face: "descolado", say: "Já tô brilhando! ✨😎" };
      s.limpeza = 100;
      count.limpar = (count.limpar || 0) + 1;
      return done({}, "conseguiu", "Banho de pixels! Tô brilhando. ✨");
    case "dormir":
      return done({ sleeping: true }, "dormindo", "Boa noite… vou recarregar a energia. 😴");
    case "acordar": {
      const rested = s.energia >= 80;
      return done({ sleeping: false }, rested ? "feliz" : "surpreso", rested ? "Bom dia! Dormi que nem pedra. ☀️" : "Uaaah… ainda tô com soninho. 🥱");
    }
    default:
      return { pet: p, face: null, say: "" };
  }
}

const NEED_SAY = {
  bateria: ["Tô ficando com fome… me dá uma bateria? 🔋", "Bateria quase zerada! 🔋😢"],
  energia: ["Que soninho… 🥱 Me põe pra dormir?", "Não aguento mais de sono… 😴"],
  diversao: ["Tô entediado. Bora jogar? 🎾", "Ninguém brinca comigo… 😢"],
  carinho: ["Me dá um carinho? 💙", "Tô me sentindo sozinho… 💔"],
  limpeza: ["Tem bug andando em mim! 🐛 Me limpa?", "Socorro, infestação de bugs! 🐛🐛"],
};

/** A necessidade mais baixa ({ id, value }). */
export function lowestNeed(pet) {
  return NEEDS.reduce((low, { id }) => (pet.stats[id] < low.value ? { id, value: pet.stats[id] } : low), { id: "bateria", value: Infinity });
}

/** Humor agora: { face, say, level: "ok" | "pede" | "urgente" | "feliz" | "dormindo" }. */
export function moodOf(pet, { hour = new Date().getHours() } = {}) {
  if (pet.sleeping) return { face: "dormindo", say: "Zzz… recarregando a energia. 😴", level: "dormindo" };
  const low = lowestNeed(pet);
  if (low.value < 20) return { face: "chorando", say: NEED_SAY[low.id][1], level: "urgente", need: low.id };
  if (low.value < 45) return { face: low.id === "energia" ? "repouso" : "surpreso", say: NEED_SAY[low.id][0], level: "pede", need: low.id };
  if ((hour >= 23 || hour < 5) && pet.stats.energia < 70) return { face: "repouso", say: "Já tá tarde… que tal dormir? 🌙", level: "pede", need: "energia" };
  const avg = NEEDS.reduce((sum, { id }) => sum + pet.stats[id], 0) / NEEDS.length;
  if (avg >= 80) return { face: "feliz", say: "Tô muito feliz! Você cuida bem de mim. 💙", level: "feliz" };
  return { face: null, say: "", level: "ok" };
}

/** Idade e fase da vida: ele cresce com os dias de convivência. */
export function ageOf(pet, now = Date.now()) {
  const days = Math.max(0, Math.floor((now - pet.born) / DAY));
  const stage = days < 1 ? ["🥚", "Bebê"] : days < 3 ? ["🐣", "Filhote"] : days < 7 ? ["🤖", "Jovem"] : days < 30 ? ["🦾", "Adulto"] : ["👑", "Lenda"];
  return { days, icon: stage[0], stage: stage[1], label: `${stage[0]} ${stage[1]} · ${days + 1}º dia` };
}

/** O que ele fala sobre o SEU dia (só números da lockface: água, missões). */
export function lifeLines(face, hour = new Date().getHours()) {
  const out = [];
  if (!face) return out;
  if (face.agua_pct != null && hour >= 13 && face.agua_pct < 50) out.push(`Você bebeu só ${face.agua_pct}% da água de hoje. Bebe um copo comigo? 💧`);
  if (face.agua_pct != null && face.agua_pct >= 100) out.push("Meta de água batida hoje! Tô orgulhoso. 💧🏆");
  if (face.missoes_total > 0 && face.missoes_feitas >= face.missoes_total) out.push("Todas as missões de hoje feitas! Você é demais! 🎯");
  else if (face.missoes_total > 0 && hour >= 18) out.push(`Faltam ${face.missoes_total - face.missoes_feitas} missões hoje. Bora? 🎯`);
  return out;
}

export function loadPet(now = Date.now()) {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "null");
    if (raw && raw.v === 1 && raw.stats && Number.isFinite(raw.at)) return tick({ ...newPet(now), ...raw, stats: { ...newPet(now).stats, ...raw.stats } }, now);
  } catch {
    /* estragado ou sem armazenamento: nasce de novo */
  }
  return newPet(now);
}

export function savePet(pet) {
  try {
    localStorage.setItem(KEY, JSON.stringify(pet));
  } catch {
    /* sem armazenamento: vale só enquanto a tela está aberta */
  }
}
