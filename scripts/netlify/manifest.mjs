// V8.2.2: files.json da interface pronta para o PC (_site/pc): versão, impressão digital do código da interface
// (a MESMA conta de scripts/prebuilt.py: arquivos em ordem, CRLF -> LF) e o sha256 de cada arquivo montado.
// Uso: node scripts/netlify/manifest.mjs <pasta-do-frontend> <pasta-montada> <versao>
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync, writeFileSync, existsSync } from "node:fs";
import { join, relative, sep } from "node:path";

export const SOURCES = ["src", "public", "index.html", "package.json", "package-lock.json", "vite.config.js",
  "tailwind.config.js", "postcss.config.js"];

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (!name.startsWith(".") && name !== "Thumbs.db") out.push(p);
  }
  return out;
}

const posix = (root, p) => relative(root, p).split(sep).join("/");

export function sourceHash(frontend) {
  const files = [];
  for (const name of SOURCES) {
    const p = join(frontend, name);
    if (!existsSync(p)) continue;
    if (statSync(p).isDirectory()) files.push(...walk(p));
    else files.push(p);
  }
  files.sort((a, b) => (posix(frontend, a) < posix(frontend, b) ? -1 : posix(frontend, a) > posix(frontend, b) ? 1 : 0));
  const h = createHash("sha256");
  for (const f of files) {
    h.update(Buffer.concat([Buffer.from(posix(frontend, f), "utf8"), Buffer.from([0])]));
    const data = readFileSync(f);
    const norm = Buffer.from(data.toString("latin1").replace(/\r\n/g, "\n"), "latin1");
    h.update(Buffer.concat([norm, Buffer.from([0])]));
  }
  return h.digest("hex");
}

export function manifest(frontend, built, versao) {
  const arquivos = walk(built).map((f) => ({ p: posix(built, f), sha256: createHash("sha256").update(readFileSync(f)).digest("hex") }))
    .filter((a) => a.p !== "files.json");
  // V8.3.1: o commit que o Netlify montou (o PC aceita a interface pronta se estiver no mesmo commit)
  return { versao, commit: process.env.COMMIT_REF || "", source_hash: sourceHash(frontend), arquivos };
}

if (process.argv[1] && process.argv[1].endsWith("manifest.mjs") && process.argv.length >= 5) {
  const [frontend, built, versao] = process.argv.slice(2);
  writeFileSync(join(built, "files.json"), JSON.stringify(manifest(frontend, built, versao)));
  console.log(`files.json da interface pronta (${versao}) gravado.`);
}
