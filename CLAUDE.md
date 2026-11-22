# CLAUDE.md — JARVIS

Assistente pessoal full-stack: backend Python/FastAPI (`backend/`), central web React/Vite (`frontend/`),
app Windows (`desktop/`), app Android (`mobile/`), ouvido offline Vosk (`scripts/voice_listener.py`).
Roda no Windows do usuário; o CI também é Windows.

## Comandos

```bash
cd backend && ruff check .                                 # lint (configuração em backend/pyproject.toml)
cd backend && python -m pytest -q tests ../scripts/tests   # testes do backend e dos scripts
cd frontend && npm test                                    # testes do frontend
```

Os testes rodam fora do Windows (Linux) desde que as dependências de `backend/requirements.txt` estejam
instaladas (`pycaw` é só do Windows e pode ficar de fora). O `tests/conftest.py` redireciona TODOS os arquivos
de `data/` para uma pasta temporária: um módulo novo que grava em `data/` entra na lista `_WRITABLE` dele.

## Convenções do projeto

- Tudo em **português do Brasil**: código comentado, mensagens, logs e commits. Comentário de mudança leva a
  versão na frente (`# V8.11: ...`) e explica o porquê (o que acontecia antes).
- Texto falado pelo JARVIS: curto (1 a 3 frases), sem markdown, sem emoji, tom de mordomo ("senhor"), e nunca
  diz que fez algo que não fez. Erro = calma + próximo passo, sem detalhe técnico na fala (o detalhe vai pro log).
- Cada entrega tem teste em `backend/tests/test_<assunto>_<versão>.py`.
- Versão em `backend/version.py` (+ `frontend/src/utils/version.js`, `CHANGELOG.md`, `test_v422.py`): só
  muda num lançamento, porque a atualização automática (`modules/auto_update.py`) compara esse número.
- Commit e push só no branch de trabalho combinado; PR só quando o usuário pedir.

## Mapa do backend

- `main.py`: log, middleware de segurança (rede, token, bloqueio), CORS, `lifespan` (tarefas de fundo), rotas.
- `core/turns.py`: motor de conversa (`handle_turn`). Ordem: alarme → bloqueio/Sentinela → intents especiais
  → **Skills (caminho rápido)** → `modules/tools.py` (funções locais legadas) → IA.
- `services/llm_orchestrator.py`: IA (Groq, Gemini, OpenAI, Anthropic; modo "auto" com reservas), prazo por
  chamada (`LLM_TIMEOUT_S`) e por turno (`LLM_TURN_BUDGET_S`), function calling das Skills.
- `core/speech.py` + `modules/tts.py`: voz (edge-tts em partes, pygame). `core/voice_route.py`: a voz sai no
  aparelho que pediu; também diz se o pedido é remoto (`is_remote()`).
- `core/runtime.py`: WebSockets (`manager.broadcast`, em paralelo e com prazo por aparelho), `track`/`track_service`.
- `core/confirm.py`: ações que esperam "sim" (`offer(kind, data)` / `answer(norm)`).
- `modules/access.py` + `modules/sentinel.py`: bloqueio real; rotas não listadas como públicas exigem a central liberada.
- `core/safe_io.py`: gravação segura; **`read_json`/`write_json`** (cache por data/tamanho, atômico, guarda cópia
  de arquivo corrompido).

## Regras de engenharia (obrigatórias)

1. **Nada bloqueante no event loop.** Rede, disco pesado, PowerShell, câmera: `await asyncio.to_thread(...)`.
   Laços de fundo: `runtime.track_service(...)` com `try/except` e `log.exception`.
2. **Todo I/O externo tem timeout** (HTTP, subprocess, IA). Nada de esperar sem limite.
3. **JSON de `data/`: use `safe_io.read_json` / `safe_io.write_json`**, nunca `Path.write_text` direto.
4. **Falha visível**: `log.exception` (com o stack trace), `event_log.add("error", ...)` quando o usuário deve
   saber, e uma frase honesta para ele. Proibido `except Exception: pass` em caminho de ação.
5. **Segurança**: nada de `shell=True`; argumentos em lista; dados vindos da voz/IA/web nunca viram comando sem
   validação. Ação irreversível sempre passa por confirmação.

## Skills (habilidades plug-and-play) — padrão obrigatório

**Toda habilidade nova é uma Skill em `backend/skills/`.** Não adicione handler novo em `modules/tools.py`,
nem `if` novo em `core/turns.py`, nem rota específica, nem texto de capacidade no `SYSTEM_PROMPT`.
O motor (`backend/core/skills/`) descobre o arquivo sozinho e liga a skill no caminho rápido, na IA
(function calling), no Sentinela (se pública), no "sim" das críticas, no catálogo e nos serviços de fundo.

### Como criar

1. Copie `backend/skills/_template.py` para `backend/skills/<nome>.py` (ou uma pasta `<nome>/__init__.py`
   quando precisar de mais de um arquivo). Arquivos que começam com `_` não são carregados.
2. Declare com o decorador:

```python
from core.skills import Permission, SkillContext, SkillResult, service, skill

@skill(
    name="workspace_layout",                 # minúsculas_com_underscore, único (vira nome de função na IA)
    title="organizar janelas",               # como o JARVIS fala dela ("Não consegui concluir organizar janelas")
    description="Organiza as janelas abertas entre os monitores num layout nomeado.",  # a IA lê isto
    permission=Permission.ACTION,            # READ | ACTION | CRITICAL
    timeout=8,                               # segundos (máx. 120)
    triggers=[r"\b(?:organiza|arruma)\b.*\bjanelas?\s+(?P<layout>lado a lado|foco)\b"],  # regex na frase normalizada
    params={"type": "object",
            "properties": {"layout": {"type": "string", "enum": ["foco", "lado a lado"]}},
            "required": ["layout"]},
    public=False,                            # True = vale com a central bloqueada (só sem dado pessoal)
    examples=["organiza as janelas lado a lado"],
)
async def workspace_layout(ctx: SkillContext, layout: str) -> SkillResult:
    ...
    return SkillResult(speech="Janelas organizadas, senhor.", cards=[...])
```

### Contrato

- Primeiro parâmetro sempre `ctx: SkillContext` (frase, origem, aparelho, `remote`, `ctx.call(...)` para usar
  outra skill, `ctx.broadcast(...)`). Os demais são os `params` (JSON Schema `type: object`).
- Devolve `SkillResult(speech, cards, data, url)`: `speech` curta e pronta para falar; `data` quando a IA deve
  explicar o resultado; `url` abre no aparelho que pediu.
- Gatilhos: regex sobre a frase **normalizada** (minúsculas, sem acentos). Grupos nomeados viram parâmetros.
  Precisam ser específicos (rodam antes das funções legadas). Para extração complexa, use `parse=fn(norm, original)`.
  Se faltar parâmetro obrigatório, a frase segue para a IA.
- Função `async` para I/O assíncrono; função comum (sem `async`) roda numa thread automaticamente.
- Tarefa de fundo: `@service("nome")` numa função `async` com laço e `await asyncio.sleep(...)`; o motor religa
  se ela cair.
- Dados persistentes: `settings.DATA_DIR / "<arquivo>.json"` com `safe_io.read_json`/`write_json`, e o caminho
  entra no `_WRITABLE` do `tests/conftest.py` (ou o teste aponta para `tmp_path`).

### Permissões (aplicadas pelo executor, nunca pela IA)

| Nível | Quando usar | O que o motor faz |
|---|---|---|
| `READ` | só consulta, sem efeito colateral | executa direto |
| `ACTION` | efeito local reversível (abrir, mover, tocar) | executa e registra; bloqueado com a central travada |
| `CRITICAL` | irreversível ou sensível (apagar, fechar processo, enviar mensagem) | pergunta antes (`confirm_text`), só executa depois do "sim"; recusa pedido remoto por padrão (`allow_remote`) |

Outras garantias: parâmetros validados contra o schema; prazo (`timeout`); 3 falhas seguidas = 5 min de pausa;
skills não são oferecidas à IA na pesquisa na internet, na rotina nem com imagem da câmera; o usuário liga e
desliga em `/api/skills/{nome}/toggle` (preferência `skills_disabled`).

### Teste obrigatório de cada skill

`backend/tests/test_skill_<nome>.py`, usando `registry.reset_for_tests()` + `registry.register(build_skill(...))`
ou importando o módulo da skill, e cobrindo: gatilho → parâmetros, execução feliz, erro/timeout e (se crítica) o
fluxo do "sim". Veja `tests/test_skills_engine_811.py` como referência.

### Ao entregar uma skill, explique

O que ela faz, como o JARVIS a aciona (frases de exemplo e/ou chamada pela IA) e quais arquivos foram
criados/afetados.

## Roadmap combinado (auditoria V8.11)

Feito: Q1 a Q4 (prazo da IA, JSON atômico com cache, broadcast em paralelo, ouvido sem travar com
"Jarvis, para") e o motor de Skills.

Próximos, na ordem sugerida:
- Q8 (pedir "sim" para "abrir X" desconhecido), Q5 (busca web em paralelo), Q6 (abas por `ctypes`),
  Q7 (mensagens honestas quando a IA não responde).
- Skills: workspace multi-monitor, System Guard, Context Autopilot, Deep Brief, macros de navegador por CDP,
  Quick Capture com escrita no Google Agenda, Clipboard AI.
- Estruturais: streaming da IA para a voz, fila de turnos no lugar de `session.busy`, memória em SQLite + FTS5,
  logs estruturados com latência por etapa, desmontar `handle_turn` em skills, barramento de eventos.
- Migração gradual: ao mexer num handler de `tools.py` ou num bloco de `turns.py`, prefira movê-lo para uma Skill.
