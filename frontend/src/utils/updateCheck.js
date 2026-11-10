export const LATEST_RELEASE_URL = "https://api.github.com/repos/PatrickCaramico/IA_Jarvis/releases/latest";
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

export async function checkForUpdate(api, fetchImpl = fetch) {
  const health = await api("/api/health");
  const currentVersion = health?.version;
  if (!currentVersion) throw new Error("Não consegui identificar a versão deste JARVIS.");

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  let response;
  try {
    response = await fetchImpl(LATEST_RELEASE_URL, {
      headers: { Accept: "application/vnd.github+json" },
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
  if (!response.ok) throw new Error("O GitHub não respondeu à verificação de atualizações.");

  const release = await response.json();
  const latestVersion = String(release?.tag_name || "").replace(/^v/i, "");
  if (!latestVersion || !release?.html_url) throw new Error("A release mais recente não tem os dados esperados.");

  return {
    currentVersion,
    latestVersion,
    updateAvailable: compareVersions(latestVersion, currentVersion) > 0,
    notes: release.body || "Sem notas de versão.",
    url: release.html_url,
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
