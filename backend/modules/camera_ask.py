"""V6.8.2: "o que é isso?" pela câmera do APARELHO (celular ou PC), como o Google Lens.

A tela da câmera (frontend/src/components/CameraWindow.jsx) manda UMA foto, só quando você toca em
"O QUE É ISSO?", e a IA responde. A foto não é gravada em lugar nenhum.
"""
from __future__ import annotations

import base64
import binascii
import re

MAX_BYTES = 2_500_000
_DATA_URL = re.compile(r"^data:image/(?:jpeg|jpg|png|webp);base64,")


def build_prompt(question: str) -> str:
    q = (question or "").strip()[:300] or "O que é isso?"
    return (
        "A imagem anexada é uma foto feita AGORA pela câmera do celular ou do computador do usuário, a pedido dele. "
        "Responda à pergunta com base no que aparece na foto, em 1 a 3 frases curtas (a resposta é falada). "
        "Se for um produto, planta, animal, prato, lugar ou texto, diga o que é e uma informação útil. "
        "Se não der para ver direito, diga isso e peça para aproximar ou iluminar melhor. Não invente. "
        "Não tente identificar pessoas pelo rosto nem dizer quem são; descreva só o que estão fazendo, se perguntado. "
        "Não repita dados sensíveis visíveis (documentos, cartões, senhas).\n"
        f'Pergunta do usuário: "{q}"'
    )


def clean_image(data: str) -> str:
    """Valida e devolve o base64 puro (sem o 'data:image/...'). Lança ValueError se não for imagem válida."""
    raw = _DATA_URL.sub("", (data or "").strip())
    if not raw:
        raise ValueError("Nenhuma foto recebida.")
    try:
        blob = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("A foto chegou corrompida.") from exc
    if len(blob) > MAX_BYTES:
        raise ValueError("A foto é grande demais.")
    if not (blob[:3] == b"\xff\xd8\xff" or blob[:8] == b"\x89PNG\r\n\x1a\n" or blob[8:12] == b"WEBP"):
        raise ValueError("Isso não parece uma foto.")
    return raw
