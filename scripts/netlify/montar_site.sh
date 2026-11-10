#!/usr/bin/env bash
# Monta o site de apresentação do JARVIS em _site/ (usado pelo Netlify; também roda no Git Bash).
# Junta: site/ (páginas), imagens de docs/linkedin/img, a marca de frontend/public/brand e o
# Branding Book ilustrado (docs/branding-book.html) e a central do JARVIS (frontend/, em _site/app/). A versão vem de backend/version.py.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/_site"

VERSAO="$(sed -n 's/^VERSION *= *"\([^"]*\)".*/\1/p' "$ROOT/backend/version.py")"
if [ -z "$VERSAO" ]; then
  echo "Não consegui ler VERSION em backend/version.py." >&2
  exit 1
fi

rm -rf "$OUT"
mkdir -p "$OUT/assets/brand" "$OUT/assets/img"

# Páginas, com a versão no lugar de {{VERSAO}}
for page in "$ROOT"/site/*.html; do
  sed "s/{{VERSAO}}/$VERSAO/g" "$page" > "$OUT/$(basename "$page")"
done

# Marca e capturas de tela
cp "$ROOT/frontend/public/brand/avatar.svg" \
   "$ROOT/frontend/public/brand/avatar-512.png" \
   "$ROOT/frontend/public/brand/share-1200x630.png" "$OUT/assets/brand/"
cp "$ROOT/docs/linkedin/img/planta-bloqueio-real.webp" \
   "$ROOT/docs/linkedin/img/jogo-real-4x0.webp" \
   "$ROOT/docs/linkedin/img/sentinela-celular.png" \
   "$ROOT/docs/linkedin/img/nova-pessoa.png" "$OUT/assets/img/"

# Branding Book ilustrado (arquivo único, com as imagens embutidas)
cp "$ROOT/docs/branding-book.html" "$OUT/branding-book.html"

# A central do JARVIS (o mesmo frontend do PC) em /app/, falando com o backend do próprio PC
# (http://127.0.0.1:8000). Pule com PULAR_CENTRAL=1 se só quiser mexer nas páginas.
if [ "${PULAR_CENTRAL:-0}" != "1" ]; then
  (
    cd "$ROOT/frontend"
    if [ ! -d node_modules ]; then npm ci --no-audit --no-fund; fi
    # MSYS_NO_PATHCONV: no Git Bash do Windows, "/app/" não pode virar caminho de disco
    MSYS_NO_PATHCONV=1 VITE_API_URL="http://127.0.0.1:8000" npx vite build --base=/app/ --outDir ../_site/app --emptyOutDir
  )
fi

echo "Site montado em _site/ (JARVIS v$VERSAO)."
