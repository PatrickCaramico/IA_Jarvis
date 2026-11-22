"""MODELO DE SKILL (este arquivo começa com "_" e por isso NÃO é carregado).

Para criar uma skill: copie para skills/<nome>.py (ou skills/<nome>/__init__.py), troque o nome e a lógica.
O JARVIS aciona a skill de dois jeitos, sem mexer em mais nada:
  1. caminho rápido: a frase bate com um dos `triggers` (regex sobre a frase normalizada: minúsculas,
     sem acentos). Grupos nomeados viram parâmetros. Sem IA, resposta na hora.
  2. pela IA: a `description` e os `params` viram uma função (function calling) no Gemini e na Groq/OpenAI.
     A IA decide chamar; o executor confere a permissão e os parâmetros antes de rodar.

Regras (veja CLAUDE.md, seção Skills):
- nome em minúsculas_com_underscore, único; description clara (é o que a IA lê);
- permission: READ (só consulta), ACTION (efeito local reversível) ou CRITICAL (irreversível: o JARVIS
  pergunta "sim?" antes, sempre; use confirm_text para a pergunta);
- trabalho lento ou bloqueante (rede, disco, PowerShell): use `async` + `asyncio.to_thread`, ou declare a
  função sem async (o executor já roda numa thread);
- timeout curto (padrão 10 s); devolva SkillResult com speech curta, em português, sem markdown;
- dados em settings.DATA_DIR (no conftest dos testes, aponte o caminho para tmp_path);
- teste em backend/tests/test_skill_<nome>.py.
"""
from __future__ import annotations

from core.skills import Permission, SkillContext, SkillResult, skill


@skill(
    name="exemplo_eco",
    title="eco de exemplo",
    description="Repete em voz alta o texto que o usuário pedir. Use quando ele disser 'repita ...'.",
    permission=Permission.READ,
    timeout=5,
    public=False,  # True = funciona com a central bloqueada (só para coisas sem dado pessoal)
    triggers=[r"^(?:jarvis\s+)?repita\s+(?P<texto>.+)$"],
    params={
        "type": "object",
        "properties": {"texto": {"type": "string", "description": "O que repetir."}},
        "required": ["texto"],
    },
    examples=["repita bom dia"],
)
async def exemplo_eco(ctx: SkillContext, texto: str) -> SkillResult:
    return SkillResult(speech=texto, cards=[])
