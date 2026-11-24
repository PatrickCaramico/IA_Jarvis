"""V9.4: AVATAR HOLOGRÁFICO da tela de bloqueio, feito a partir da foto do rosto cadastrada.

O senhor pediu um avatar novo no bloqueio com o próprio rosto. Em vez de mostrar a foto crua para quem passa na
frente do PC (antes, a foto só aparecia depois do rosto reconhecido, por privacidade), o JARVIS gera uma versão
"holograma": o rosto recortado, em tons de ciano, com linhas de varredura e as bordas sumindo num círculo. Fica
salvo em data/avatar_holo.png e é refeito sozinho quando a foto do rosto muda. Desligado por padrão: liga em
Configurações > Bloqueio ou por voz ("coloca meu avatar na tela de bloqueio").

Tudo local (OpenCV); a foto nunca sai do PC.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from config import settings

log = logging.getLogger("jarvis.holo_avatar")

_PATH: Path = settings.DATA_DIR / "avatar_holo.png"
SIZE = 360
_lock = threading.Lock()


def _face_box(img) -> Optional[tuple[int, int, int, int]]:
    """Maior rosto da foto (x, y, w, h) pelo mesmo detector do desbloqueio; None se não achar."""
    try:
        from modules import face

        face._load_models()  # noqa: SLF001
        faces = face._detect(img)  # noqa: SLF001 - mesmo detector do desbloqueio
    except Exception:  # noqa: BLE001 - sem os modelos baixados: recorte no centro
        log.debug("Avatar: detector indisponível, recortando no centro", exc_info=True)
        return None
    if not faces:
        return None
    best = max(faces, key=lambda f: float(f[2]) * float(f[3]))
    return int(best[0]), int(best[1]), int(best[2]), int(best[3])


def crop_square(w: int, h: int, box: Optional[tuple[int, int, int, int]]) -> tuple[int, int, int]:
    """Quadrado (x, y, lado) em volta do rosto com folga para cabelo e queixo; sem rosto, o centro da foto."""
    if box:
        x, y, bw, bh = box
        cx, cy = x + bw / 2, y + bh / 2 - bh * 0.08  # um pouco acima: entra o cabelo
        side = max(bw, bh) * 1.9
    else:
        cx, cy, side = w / 2, h * 0.45, min(w, h) * 0.9
    side = int(min(side, w, h))
    x0 = int(min(max(0, cx - side / 2), w - side))
    y0 = int(min(max(0, cy - side / 2), h - side))
    return x0, y0, side


def render(jpeg_bytes: bytes) -> bytes:
    """Foto (JPG/PNG) -> PNG do holograma (RGBA, SIZE x SIZE). Lança ValueError se a imagem não abrir."""
    import cv2
    import numpy as np

    img = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Não consegui ler a foto do rosto.")
    h, w = img.shape[:2]
    x0, y0, side = crop_square(w, h, _face_box(img))
    face_img = cv2.resize(img[y0:y0 + side, x0:x0 + side], (SIZE, SIZE), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(6, 6)).apply(gray)  # contraste uniforme (luz de lado)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 60, 140)  # contorno "desenhado a laser"
    lum = gray.astype(np.float32) / 255.0
    lum = np.clip((lum - 0.12) / 0.8, 0, 1) ** 0.9

    # Ciano do JARVIS (#4fdcff) com o brilho da foto; o contorno sai quase branco
    b = 255 * np.clip(lum * 1.0 + 0.05, 0, 1)
    g = 220 * np.clip(lum * 1.0 + 0.04, 0, 1)
    r = 79 * lum
    rgb = np.dstack([r, g, b])
    edge = (edges > 0)[..., None]
    rgb = np.where(edge, np.array([200, 250, 255], np.float32), rgb)

    # Linhas de varredura (1 a cada 3 px um pouco mais escura) e vinheta circular que some nas bordas
    scan = np.ones((SIZE, 1), np.float32)
    scan[::3] = 0.72
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    dist = np.sqrt((xx - SIZE / 2) ** 2 + (yy - SIZE / 2) ** 2) / (SIZE / 2)
    fade = np.clip((1.0 - dist) / 0.28, 0, 1)
    alpha = np.clip((0.18 + lum * 0.82) * fade * scan, 0, 1)
    alpha = np.where(edge[..., 0], np.maximum(alpha, 0.9 * fade), alpha)

    rgba = np.dstack([rgb[..., 2], rgb[..., 1], rgb[..., 0], alpha * 255]).astype(np.uint8)  # BGRA para o OpenCV
    ok, buf = cv2.imencode(".png", rgba)
    if not ok:
        raise ValueError("Não consegui gerar o avatar.")
    return buf.tobytes()


def _source() -> Path:
    from modules import face

    return face.PHOTO_PATH


def ensure() -> Optional[Path]:
    """Caminho do avatar pronto (refeito se a foto do rosto for mais nova). None sem foto cadastrada."""
    src = _source()
    if not src.exists():
        return None
    with _lock:
        try:
            if _PATH.exists() and _PATH.stat().st_mtime >= src.stat().st_mtime:
                return _PATH
            data = render(src.read_bytes())
            _PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = _PATH.with_suffix(".tmp")
            tmp.write_bytes(data)
            from core.safe_io import replace_file

            replace_file(tmp, _PATH)
            log.info("Avatar holográfico gerado a partir da foto do rosto.")
            return _PATH
        except Exception:  # noqa: BLE001
            log.exception("Não consegui gerar o avatar holográfico")
            return _PATH if _PATH.exists() else None


def clear() -> None:
    try:
        _PATH.unlink()
    except OSError:
        pass
