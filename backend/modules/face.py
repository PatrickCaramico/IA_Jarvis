"""Reconhecimento facial 100% local (OpenCV: detector YuNet + reconhecedor SFace).

Nenhuma imagem do rosto é enviada para a internet: a foto de perfil e a comparação
com a webcam acontecem no seu computador. Só o download inicial dos modelos usa a rede.
"""
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np
import requests

from config import settings
from modules.vision import open_camera

log = logging.getLogger("jarvis.face")

# O OpenCV no Windows não abre arquivos em caminhos com acento (ex.: "Área de Trabalho").
# Por isso os modelos vão para a primeira pasta cujo caminho seja só ASCII.
def _models_dir() -> Path:
    candidates = [
        settings.DATA_DIR / "models",
        Path.home() / ".jarvis" / "models",
        Path(tempfile.gettempdir()) / "jarvis_models",
    ]
    for c in candidates:
        if str(c).isascii():
            return c
    return candidates[0]


PHOTO_PATH = settings.DATA_DIR / "profile.jpg"
META_PATH = settings.DATA_DIR / "profile.json"

_MODELS = {
    "detector": (
        "face_detection_yunet_2023mar.onnx",
        [
            "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
            "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
        ],
    ),
    "recognizer": (
        "face_recognition_sface_2021dec.onnx",
        [
            "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
            "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
        ],
    ),
}

_detector = None
_recognizer = None


def _download(filename: str, urls: list[str]) -> Path:
    folder = _models_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    if path.exists() and path.stat().st_size > 100_000:
        return path

    last_error: Optional[Exception] = None
    for url in urls:
        tmp = path.with_suffix(".part")
        try:
            log.info("Baixando modelo %s ...", filename)
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
            if tmp.stat().st_size < 100_000:
                raise RuntimeError("arquivo baixado é pequeno demais")
            tmp.replace(path)
            return path
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            tmp.unlink(missing_ok=True)

    raise RuntimeError(
        f"Não consegui baixar o modelo {filename} ({last_error}). "
        f"Baixe manualmente de {urls[0]} e salve em {folder}."
    )


def _load_models() -> None:
    global _detector, _recognizer
    if _detector is not None and _recognizer is not None:
        return
    det_path = _download(*_MODELS["detector"])
    rec_path = _download(*_MODELS["recognizer"])
    try:
        _detector = cv2.FaceDetectorYN.create(str(det_path), "", (320, 320), 0.85, 0.3, 5000)
        _recognizer = cv2.FaceRecognizerSF.create(str(rec_path), "")
    except AttributeError as exc:
        raise RuntimeError(
            "Sua versão do OpenCV é antiga demais. Rode: pip install --upgrade opencv-python"
        ) from exc


def _faces(img: np.ndarray) -> list:
    h, w = img.shape[:2]
    _detector.setInputSize((w, h))
    _, faces = _detector.detect(img)
    return [] if faces is None else list(faces)


def _embedding(img: np.ndarray) -> tuple[Optional[np.ndarray], int]:
    """Retorna (vetor do maior rosto, nº de rostos). O .copy() é obrigatório:
    o OpenCV reaproveita o mesmo buffer e sobrescreveria o vetor anterior."""
    faces = _faces(img)
    if not faces:
        return None, 0
    face = max(faces, key=lambda f: f[2] * f[3])
    aligned = _recognizer.alignCrop(img, face)
    return _recognizer.feature(aligned).copy(), len(faces)


# ---------- Perfil ----------
def has_profile() -> bool:
    return PHOTO_PATH.exists()


def get_name() -> str:
    try:
        name = json.loads(META_PATH.read_text(encoding="utf-8")).get("name", "")
    except (OSError, ValueError):
        name = ""
    return name.strip() or settings.USER_NAME


def save_profile(image_bytes: bytes, name: str) -> None:
    """Valida (exatamente 1 rosto) e salva a foto de perfil + nome. Lança ValueError se inválida."""
    _load_models()
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Não consegui ler essa imagem. Use uma foto JPG ou PNG.")

    h, w = img.shape[:2]
    if max(h, w) > 1280:
        scale = 1280 / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    faces = _faces(img)
    if not faces:
        raise ValueError("Não encontrei nenhum rosto na foto. Use uma foto nítida, de frente e bem iluminada.")
    if len(faces) > 1:
        raise ValueError("Encontrei mais de um rosto na foto. Use uma foto só sua.")

    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise ValueError("Falha ao salvar a foto.")
    PHOTO_PATH.write_bytes(buf.tobytes())
    META_PATH.write_text(json.dumps({"name": name.strip()}, ensure_ascii=False), encoding="utf-8")


# ---------- Verificação ----------
FrameCallback = Callable[[dict], None]


def _largest_face(faces: list):
    return max(faces, key=lambda f: f[2] * f[3]) if faces else None


def _norm_box(face, w: int, h: int) -> Optional[list[float]]:
    if face is None or w <= 0 or h <= 0:
        return None
    x, y, fw, fh = (float(v) for v in face[:4])
    x0, y0 = max(0.0, x / w), max(0.0, y / h)
    x1, y1 = min(1.0, (x + fw) / w), min(1.0, (y + fh) / h)
    return [round(x0, 4), round(y0, 4), round(max(0.0, x1 - x0), 4), round(max(0.0, y1 - y0), 4)]


def _encode_preview(frame: np.ndarray) -> Optional[bytes]:
    """JPEG reduzido só para a transmissão ao vivo (nunca é salvo em disco aqui)."""
    h, w = frame.shape[:2]
    width = max(160, int(settings.FACE_STREAM_WIDTH))
    if w > width:
        frame = cv2.resize(frame, (width, int(h * width / w)))
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(settings.FACE_STREAM_QUALITY)])
    return buf.tobytes() if ok else None


def verify_against_profile(
    timeout: Optional[float] = None,
    on_frame: Optional[FrameCallback] = None,
    refs: Optional[list[tuple[str, Path]]] = None,
) -> dict:
    """Olha para a webcam por até `timeout` segundos e compara com a foto de perfil.

    Retorna {"verified": bool, "saw_face": bool, "score": float, "profile_id": str|None}.
    refs (V4.5): [(id_do_perfil, foto)] para reconhecer entre várias pessoas; sem refs, compara só
    com a foto do perfil ativo, como antes.

    on_frame (opcional): chamado com {"jpeg", "box", "saw_face", "score", "phase"} a no máximo
    FACE_STREAM_FPS quadros por segundo, para mostrar a câmera ao vivo. Fases: searching,
    comparing, verified, failed. Sem on_frame, o comportamento é o de antes. Os quadros só
    existem em memória; a câmera é sempre liberada no finally. O limite FACE_THRESHOLD não muda.
    """
    timeout = settings.FACE_TIMEOUT if timeout is None else timeout
    _load_models()

    references: list[tuple[Optional[str], np.ndarray]] = []
    for pid, path in refs or [(None, PHOTO_PATH)]:
        try:
            ref_img = cv2.imdecode(np.frombuffer(Path(path).read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        except OSError:
            continue
        emb_ref, _ = _embedding(ref_img) if ref_img is not None else (None, 0)
        if emb_ref is not None:
            references.append((pid, emb_ref))
    if not references:
        raise RuntimeError("Não encontrei rosto na foto de perfil salva. Cadastre outra foto.")

    min_interval = 1.0 / max(1.0, float(settings.FACE_STREAM_FPS))
    last_emit = 0.0
    last_frame = None
    last_box = None
    compare_every = 1  # sobe para 2 ou 3 se a comparação for pesada (vídeo fluido)

    def emit(frame, box, saw, score, phase, force=False):
        nonlocal last_emit
        if on_frame is None or frame is None:
            return
        now = time.monotonic()
        if not force and now - last_emit < min_interval:
            return
        last_emit = now
        jpeg = _encode_preview(frame)
        if not jpeg:
            return
        try:
            on_frame({"jpeg": jpeg, "box": box, "saw_face": saw, "score": round(max(score, 0.0), 4), "phase": phase})
        except Exception:  # noqa: BLE001 - a transmissão nunca derruba a verificação
            log.debug("Falha ao entregar quadro ao vivo", exc_info=True)

    cap = open_camera()
    best, saw_face, frames, faced = -1.0, False, 0, 0
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            ok, frame = cap.read()
            if not ok:
                continue
            frames += 1
            last_frame = frame
            if frames <= 5:  # aquecimento da câmera
                emit(frame, None, False, best, "searching")
                continue
            h, w = frame.shape[:2]
            face = _largest_face(_faces(frame))
            if face is None:
                last_box = None
                emit(frame, None, saw_face, best, "searching")
                continue
            saw_face = True
            faced += 1
            last_box = _norm_box(face, w, h)
            if on_frame is not None and faced % compare_every != 0:
                emit(frame, last_box, True, best, "comparing")
                continue
            started = time.monotonic()
            aligned = _recognizer.alignCrop(frame, face)
            emb = _recognizer.feature(aligned).copy()
            score, who = max(
                (float(_recognizer.match(r, emb, cv2.FaceRecognizerSF_FR_COSINE)), pid) for pid, r in references
            )
            took = time.monotonic() - started
            compare_every = 1 if took < 0.05 else 2 if took < 0.1 else 3
            best = max(best, score)
            if score >= settings.FACE_THRESHOLD:
                log.info("Rosto reconhecido (similaridade %.3f, perfil %s).", score, who or "ativo")
                emit(frame, last_box, True, score, "verified", force=True)
                return {"verified": True, "saw_face": True, "score": score, "profile_id": who}
            emit(frame, last_box, True, best, "comparing")
    finally:
        cap.release()

    emit(last_frame, last_box, saw_face, best, "failed", force=True)
    log.info("Rosto não reconhecido (melhor similaridade %.3f).", best)
    return {"verified": False, "saw_face": saw_face, "score": best, "profile_id": None}


def detect_presence(timeout: float = 1.2) -> bool:
    """Checagem rápida de presença (seção 17.5): só detecta se há um rosto, sem comparar
    com a foto e sem salvar imagem. A câmera é liberada no final."""
    _load_models()
    cap = open_camera()
    frames = 0
    deadline = time.monotonic() + max(0.3, timeout)
    try:
        while time.monotonic() < deadline:
            ok, frame = cap.read()
            if not ok:
                continue
            frames += 1
            if frames <= 3:
                continue
            if _faces(frame):
                return True
    finally:
        cap.release()
    return False
