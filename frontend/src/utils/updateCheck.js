export const AUTO_CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;

const LAST_AUTO_CHECK_KEY = "jarvis.updateCheck.lastAutoCheck";
const LAST_RESULT_KEY = "jarvis.updateCheck.lastResult";
const VERSION_PATTERN = /^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/;

function versionParts(value) {
  const match = String(value || "").trim().match(VERSION_PATTERN);
  if (!match) throw new Error("A versão recebida não está no formato esperado.");
  return {
    numbers: match.slice(1, 4).map(Number),
    prerelease: match[4] ? match[4].split(".") : null,
  };
}

export function compareVersions(left, right) {
  const leftVersion = versionParts(left);
  const rightVersion = versionParts(right);
  for (let index = 0; index < leftVersion.numbers.length; index += 1) {
    if (leftVersion.numbers[index] !== rightVersion.numbers[index]) {
      return leftVersion.numbers[index] > rightVersion.numbers[index] ? 1 : -1;
    }
  }
  if (leftVersion.prerelease === null && rightVersion.prerelease !== null) return 1;
  if (leftVersion.prerelease !== null && rightVersion.prerelease === null) return -1;
  if (leftVersion.prerelease === null) return 0;
  for (let index = 0; index < Math.max(leftVersion.prerelease.length, rightVersion.prerelease.length); index += 1) {
    const leftPart = leftVersion.prerelease[index];
    const rightPart = rightVersion.prerelease[index];
    if (leftPart === undefined) return -1;
    if (rightPart === undefined) return 1;
    if (leftPart === rightPart) continue;
    const leftNumber = /^\d+$/.test(leftPart) ? Number(leftPart) : null;
    const rightNumber = /^\d+$/.test(rightPart) ? Number(rightPart) : null;
    if (leftNumber !== null && rightNumber !== null) return leftNumber > rightNumber ? 1 : -1;
    if (leftNumber !== null) return -1;
    if (rightNumber !== null) return 1;
    return leftPart > rightPart ? 1 : -1;
  }
  return 0;
}

// V6.7.4: confere a MESMA fonte do botão ATUALIZAR (a branch do GitHub, pelo PC: git fetch), não as Releases
// do GitHub, que o projeto não usa (por isso a conferência antiga nunca acusava nada).
export async function checkForUpdate(api) {
  const data = await api("/api/system/update/status?force=true", { timeout: 60_000 });
  if (!data || typeof data.available !== "boolean") throw new Error("Não consegui conferir as atualizações.");
  if (!data.available && data.message && /n[aã]o consegui|sem git/i.test(data.message)) throw new Error(data.message);
  return {
    currentVersion: data.current || "",
    latestVersion: data.latest || data.current || "",
    updateAvailable: data.available,
    count: data.count || 0,
    notes: (data.notes || []).join("\n"),
  };
}

export function saveUpdateResult(result) {
  try {
    localStorage.setItem(LAST_RESULT_KEY, JSON.stringify(result));
  } catch {
    // O aviso manual continua disponível mesmo se o navegador bloquear o armazenamento local.
  }
}

export function readUpdateResult() {
  try {
    const value = localStorage.getItem(LAST_RESULT_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

export function scheduleDailyUpdateCheck(api) {
  let timer;
  const run = async () => {
    let result;
    try {
      result = await checkForUpdate(api);
    } catch {
      result = { error: "Não foi possível verificar atualizações agora. Confira sua conexão." };
    }
    saveUpdateResult(result);
    try {
      localStorage.setItem(LAST_AUTO_CHECK_KEY, String(Date.now()));
    } catch {
      // Sem armazenamento local, o próximo ciclo começa 24 h após esta tentativa.
    }
    window.dispatchEvent(new CustomEvent("jarvis-update-check", { detail: result }));
    timer = setTimeout(run, AUTO_CHECK_INTERVAL_MS);
  };

  let lastCheck = 0;
  try {
    lastCheck = Number(localStorage.getItem(LAST_AUTO_CHECK_KEY)) || 0;
  } catch {
    // O primeiro ciclo ocorre após 24 h mesmo sem armazenamento local.
  }
  const delay = lastCheck
    ? Math.max(60_000, AUTO_CHECK_INTERVAL_MS - (Date.now() - lastCheck))
    : AUTO_CHECK_INTERVAL_MS;
  timer = setTimeout(run, delay);
  return () => clearTimeout(timer);
}
