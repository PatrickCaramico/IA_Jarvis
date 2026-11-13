"""V6.8.2: "o que é isso?" pela câmera do APARELHO (celular ou PC), como o Google Lens.

A tela da câmera (frontend/src/components/CameraWindow.jsx) manda UMA foto, só quando você toca em
"O QUE É ISSO?", e a IA responde. A foto não é gravada em lugar nenhum.
"""
from __future__ import annotations

import base64
import binascii
import json
import re

MAX_BYTES = 2_500_000
_DATA_URL = re.compile(r"^data:image/(?:jpeg|jpg|png|webp);base64,")


def build_prompt(question: str) -> str:
    """V6.9: além da fala curta, a IA devolve um DIAGNÓSTICO do item (aparece numa janela na tela)."""
    q = (question or "").strip()[:300] or "O que é isso?"
    return (
        "A imagem anexada é uma foto feita AGORA pela câmera do celular ou do computador do usuário, a pedido dele. "
        "Analise o item principal da foto e responda à pergunta. Se for produto, planta, animal, prato, objeto, peça, "
        "lugar ou texto, diga o que é e informações úteis. Se não der para ver direito, diga isso e peça para aproximar "
        "ou iluminar melhor. Não invente: se não tiver certeza, diga e use confiança baixa. "
        "Não tente identificar pessoas pelo rosto nem dizer quem são. Não repita dados sensíveis visíveis "
        "(documentos, cartões, senhas).\n"
        "Responda SOMENTE com um JSON, em português do Brasil, neste formato:\n"
        '{"fala": "1 a 3 frases curtas respondendo à pergunta (vai ser falada)", '
        '"item": "nome do item", "categoria": "ex.: Planta, Eletrônico, Alimento, Remédio, Peça, Documento", '
        '"confianca": "alta|media|baixa", "resumo": "2 a 4 frases descrevendo o item", '
        '"detalhes": [{"rotulo": "ex.: Nome científico, Marca, Modelo, Estado, Material, Preço médio", "valor": "..."}], '
        '"dicas": ["cuidados, como usar, onde encontrar..."], "alertas": ["riscos, validade, toxicidade... (vazio se nada)"]}\n'
        "No máximo 6 detalhes, 4 dicas e 3 alertas.\n"
        f'Pergunta do usuário: "{q}"'
    )


_CONF = {"alta": "alta", "media": "media", "média": "media", "baixa": "baixa"}


def _short(value, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def parse_answer(raw: str) -> tuple[str, dict | None]:
    """Separa a fala e o diagnóstico. Se a IA não mandou JSON, a resposta toda vira a fala (sem janela)."""
    text = (raw or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return text, None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return text, None
    if not isinstance(data, dict):
        return text, None
    fala = _short(data.get("fala") or data.get("resumo"), 600)
    item = _short(data.get("item"), 80)
    if not item:
        return fala or text, None
    detalhes = []
    for d in data.get("detalhes") or []:
        if isinstance(d, dict) and _short(d.get("rotulo"), 40) and _short(d.get("valor"), 160):
            detalhes.append({"rotulo": _short(d["rotulo"], 40), "valor": _short(d["valor"], 160)})
    lists = {k: [_short(x, 220) for x in (data.get(k) or []) if isinstance(x, str) and x.strip()] for k in ("dicas", "alertas")}
    diag = {
        "item": item,
        "categoria": _short(data.get("categoria"), 40),
        "confianca": _CONF.get(_short(data.get("confianca"), 10).lower(), "media"),
        "resumo": _short(data.get("resumo"), 700),
        "detalhes": detalhes[:6],
        "dicas": lists["dicas"][:4],
        "alertas": lists["alertas"][:3],
    }
    return fala or diag["resumo"] or item, diag


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
