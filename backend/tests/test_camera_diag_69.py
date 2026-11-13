"""V6.9: diagnóstico do item pela câmera (janela na tela)."""
import base64

from fastapi.testclient import TestClient

import main
from modules import access, camera_ask
from services import llm_orchestrator

JPEG = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"x" * 100).decode()
RAW = """```json
{"fala": "É uma jabuticabeira, senhor.", "item": "Jabuticabeira", "categoria": "Planta", "confianca": "Alta",
 "resumo": "Árvore frutífera nativa.", "detalhes": [{"rotulo": "Nome científico", "valor": "Plinia cauliflora"}, {"rotulo": "", "valor": "x"}],
 "dicas": ["Regue bem", 3], "alertas": []}
```"""


def test_parse_answer_builds_diagnosis():
    text, diag = camera_ask.parse_answer(RAW)
    assert text == "É uma jabuticabeira, senhor."
    assert diag["item"] == "Jabuticabeira" and diag["confianca"] == "alta"
    assert diag["detalhes"] == [{"rotulo": "Nome científico", "valor": "Plinia cauliflora"}]
    assert diag["dicas"] == ["Regue bem"] and diag["alertas"] == []


def test_plain_text_has_no_window():
    assert camera_ask.parse_answer("É um copo, senhor.") == ("É um copo, senhor.", None)
    assert camera_ask.parse_answer("{quebrado") == ("{quebrado", None)


def test_route_returns_diagnosis(monkeypatch):
    access.reset_for_tests(access.UNLOCKED)
    monkeypatch.setattr(llm_orchestrator, "ask_with_image", lambda prompt, image: RAW)
    r = TestClient(main.app).post("/api/camera/ask", json={"image": JPEG, "question": "analisa esse item"})
    body = r.json()
    assert r.status_code == 200 and body["text"].startswith("É uma jabuticabeira") and body["diagnostico"]["categoria"] == "Planta"
