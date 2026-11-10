"""Módulo de visão: acesso à webcam e captura de um frame em Base64 (JPEG)."""
import base64
import logging
import os

import cv2

from config import settings

log = logging.getLogger("jarvis.vision")


def list_available_cameras(max_tested: int = 5) -> list[dict]:
    """Testa portas de câmera e retorna as webcams disponíveis."""
    available = []
    for i in range(max_tested):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(i)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                available.append({"index": i, "name": f"Webcam {i}" + (" (Padrão)" if i == 0 else "")})
            cap.release()
    if not available:
        available.append({"index": 0, "name": "Webcam 0 (Padrão)"})
    return available


def open_camera(camera_index: int | None = None) -> "cv2.VideoCapture":
    """Abre a webcam (lança RuntimeError se não conseguir). Quem chama deve dar release()."""
    if camera_index is None:
        try:
            from modules import prefs
            index = prefs.get_camera_index()
        except Exception:  # noqa: BLE001
            index = settings.CAMERA_INDEX
    else:
        index = camera_index

    # No Windows, o backend DirectShow abre a câmera bem mais rápido.
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(index)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(
            f"Não foi possível abrir a câmera (índice {index}). "
            "Verifique se outro app está usando a webcam e se há permissão de acesso."
        )
    return cap


def capture_webcam_frame(
    camera_index: int | None = None,
    warmup_frames: int = 8,
    max_width: int = 896,
) -> str:
    """Captura um frame da webcam e retorna o JPEG codificado em Base64.

    - warmup_frames: descarta os primeiros quadros (a câmera precisa ajustar a exposição).
    - max_width: reduz a imagem para economizar tokens/latência na chamada da IA.
    """
    cap = open_camera(camera_index)
    try:
        frame = None
        for _ in range(warmup_frames):
            ok, current = cap.read()
            if ok:
                frame = current
        if frame is None:
            raise RuntimeError("A câmera abriu, mas não retornou nenhuma imagem.")

        height, width = frame.shape[:2]
        if width > max_width:
            frame = cv2.resize(frame, (max_width, int(height * max_width / width)))

        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if not ok:
            raise RuntimeError("Falha ao codificar a imagem em JPEG.")

        log.info("Frame capturado (%sx%s).", frame.shape[1], frame.shape[0])
        return base64.b64encode(buffer.tobytes()).decode("utf-8")
    finally:
        cap.release()
