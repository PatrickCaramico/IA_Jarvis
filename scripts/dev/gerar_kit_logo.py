"""Gera o kit de logo do JARVIS (V4.2.2) em frontend/public/brand/.

Peças (SVG, e PNG quando o Playwright está instalado):
- avatar.svg / avatar-512.png / avatar-1024.png  -> foto de perfil (quadrado; aguenta recorte redondo)
- banner.svg / banner-1500x500.png              -> capa de perfil (X, YouTube usa a área central)
- share.svg / share-1200x630.png                -> imagem de compartilhamento de link (Open Graph)
- wordmark.svg                                  -> só o nome "JARVIS", em traço, para usar em vídeos

O nome é desenhado em traços geométricos (sem fonte), então fica igual em qualquer computador.
Rodar: python scripts/dev/gerar_kit_logo.py   (na raiz do projeto)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "public" / "brand"

CORE = "#22D3EE"
DEEP = "#0E7490"
ABYSS = "#05070D"
PANEL = "#0B1220"
MUTED = "#7FA7B5"
TEXT = "#E6F7FB"

# ---------------------------------------------------------------- letras (grade 56 x 72, traço 9)
LETTER_W, LETTER_H, STROKE, GAP = 56, 72, 9, 18
LETTERS = {
    "J": (56, ["M51.5 4.5 V58 L42 67.5 H14 L4.5 58 V50"]),
    "A": (56, ["M4.5 67.5 V18 L18 4.5 H38 L51.5 18 V67.5", "M4.5 42 H51.5"]),
    "R": (56, ["M4.5 67.5 V4.5 H40 L51.5 16 V30 L40 41.5 H4.5", "M32 41.5 L51.5 67.5"]),
    "V": (56, ["M4.5 4.5 V40 L28 67.5 L51.5 40 V4.5"]),
    "I": (9, ["M4.5 4.5 V67.5"]),
    "S": (56, ["M51.5 4.5 H16 L4.5 16 V25 L15.5 36 H40.5 L51.5 47 V56 L40 67.5 H4.5"]),
}


def wordmark(text: str = "JARVIS") -> tuple[str, int]:
    """Grupo SVG com o nome em traços (origem no canto superior esquerdo) e a largura total."""
    parts, x = [], 0
    for ch in text:
        width, paths = LETTERS[ch]
        for d in paths:
            parts.append(f'<path transform="translate({x} 0)" d="{d}"/>')
        x += width + GAP
    total = x - GAP
    group = (f'<g fill="none" stroke="currentColor" stroke-width="{STROKE}" stroke-linecap="square" '
             f'stroke-linejoin="miter">{"".join(parts)}</g>')
    return group, total


def nucleo(color: str = CORE) -> str:
    """O logo Núcleo na grade 64 x 64 (mesmas medidas do Branding Book)."""
    return (
        f'<circle cx="32" cy="32" r="8" fill="{color}"/>'
        f'<circle cx="32" cy="32" r="8" fill="none" stroke="{color}" stroke-opacity="0.35" stroke-width="6"/>'
        f'<circle cx="32" cy="32" r="17" fill="none" stroke="{color}" stroke-width="3.5" stroke-dasharray="22.6 13" '
        f'stroke-linecap="round" transform="rotate(-90 32 32)"/>'
        f'<circle cx="32" cy="32" r="26" fill="none" stroke="{color}" stroke-width="2.5" stroke-opacity="0.8" '
        f'stroke-dasharray="30.8 10" stroke-linecap="round" transform="rotate(-45 32 32)"/>'
    )


DEFS = f"""<defs>
  <radialGradient id="glow" cx="50%" cy="50%" r="50%">
    <stop offset="0" stop-color="{CORE}" stop-opacity="0.28"/>
    <stop offset="0.55" stop-color="{DEEP}" stop-opacity="0.10"/>
    <stop offset="1" stop-color="{ABYSS}" stop-opacity="0"/>
  </radialGradient>
  <filter id="soft" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="1.6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M40 0 H0 V40" fill="none" stroke="{CORE}" stroke-opacity="0.05" stroke-width="1"/>
  </pattern>
</defs>"""


def svg(width: int, height: int, body: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{title}">\n<title>{title}</title>\n'
            f'{DEFS}\n{body}\n</svg>\n')


def logo_at(cx: float, cy: float, size: float) -> str:
    scale = size / 64
    return (f'<g transform="translate({cx - size / 2:.1f} {cy - size / 2:.1f}) scale({scale:.4f})" '
            f'filter="url(#soft)">{nucleo()}</g>')


def word_at(x: float, y: float, height: float, color: str = TEXT) -> tuple[str, float]:
    group, total = wordmark()
    scale = height / LETTER_H
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({scale:.4f})" style="color:{color}">{group}</g>',
            total * scale)


def avatar() -> str:
    s = 512
    body = (f'<rect width="{s}" height="{s}" fill="{ABYSS}"/>'
            f'<circle cx="256" cy="256" r="250" fill="url(#glow)"/>'
            f'{logo_at(256, 256, 300)}')
    return svg(s, s, body, "JARVIS · avatar")


def lockup(width: int, height: int, logo_size: float, word_h: float, tagline: str, tag_size: int,
           title: str) -> str:
    """Logo à esquerda, nome em traço e assinatura, tudo centralizado na peça."""
    gap = logo_size * 0.32
    _, word_w = word_at(0, 0, word_h)
    tag_w = len(tagline) * tag_size * 0.80  # estimativa folgada (maiúsculas + espaçamento)
    total = logo_size + gap + max(word_w, tag_w)
    x0 = (width - total) / 2
    cy = height / 2
    word, _ = word_at(x0 + logo_size + gap, cy - word_h / 2 - tag_size * 0.9, word_h)
    tag_x = x0 + logo_size + gap + 2
    tag_y = cy + word_h / 2 + tag_size * 0.9
    body = (
        f'<rect width="{width}" height="{height}" fill="{ABYSS}"/>'
        f'<rect width="{width}" height="{height}" fill="url(#grid)"/>'
        f'<ellipse cx="{x0 + logo_size / 2:.1f}" cy="{cy}" rx="{logo_size * 1.3:.1f}" ry="{logo_size * 1.3:.1f}" fill="url(#glow)"/>'
        f'{logo_at(x0 + logo_size / 2, cy, logo_size)}'
        f'{word}'
        f'<text x="{tag_x:.1f}" y="{tag_y:.1f}" fill="{MUTED}" font-size="{tag_size}" letter-spacing="{tag_size * 0.12:.1f}" '
        f'font-family="Rajdhani, \'Segoe UI\', Inter, system-ui, sans-serif" font-weight="600">{tagline}</text>'
        f'<rect x="0" y="{height - 4}" width="{width}" height="4" fill="{CORE}" opacity="0.55"/>'
    )
    return svg(width, height, body, title)


def wordmark_only() -> str:
    group, total = wordmark()
    pad = 12
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{total + pad * 2}" height="{LETTER_H + pad * 2}" '
            f'viewBox="{-pad} {-pad} {total + pad * 2} {LETTER_H + pad * 2}" role="img" aria-label="JARVIS">'
            f'<title>JARVIS</title><g style="color:{CORE}">{group}</g></svg>\n')


TAGLINE = "CENTRAL PESSOAL · ROTINA, FOCO E SAÚDE"
PIECES = {
    "avatar.svg": (avatar, [(512, 512, "avatar-512.png"), (1024, 1024, "avatar-1024.png")]),
    "banner.svg": (lambda: lockup(1500, 500, 200, 92, TAGLINE, 24, "JARVIS · banner"),
                   [(1500, 500, "banner-1500x500.png")]),
    "share.svg": (lambda: lockup(1200, 630, 180, 84, TAGLINE, 21, "JARVIS · compartilhamento"),
                  [(1200, 630, "share-1200x630.png")]),
    "wordmark.svg": (wordmark_only, []),
}


def render_png(svg_path: Path, width: int, height: int, out: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        markup = svg_path.read_text(encoding="utf-8")
        page.set_content(f'<html><head><style>svg{{display:block;width:{width}px;height:{height}px}}</style></head>'
                         f'<body style="margin:0;background:{ABYSS}">{markup}</body></html>')
        page.wait_for_timeout(200)
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": width, "height": height})
        browser.close()
    return True


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    png_ok = True
    for name, (build, pngs) in PIECES.items():
        path = OUT / name
        path.write_text(build(), encoding="utf-8")
        print("ok", path.relative_to(ROOT))
        for width, height, png in pngs:
            if png_ok and render_png(path, width, height, OUT / png):
                print("ok", (OUT / png).relative_to(ROOT))
            else:
                png_ok = False
    if not png_ok:
        print("PNG não gerado: instale o Playwright (pip install playwright && playwright install chromium).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
