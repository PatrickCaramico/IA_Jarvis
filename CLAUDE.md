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
  chamada (`LLM_TIMEOUT_S`) e por turno (`LLM_TURN_BUDGET_S`), function calling das Skills, temperatura baixa
  (`LLM_TEMPERATURE`, V8.12).
- `services/grounding.py` (V8.12): contra alucinação. `needs_fresh_facts` manda pergunta de fato atual para a IA
  com pesquisa no Google; `RULES` (veracidade) entra no `SYSTEM_PROMPT`; a nota do pedido diz "só o que as fontes
  dizem" ou, sem pesquisa, "avise que pode estar desatualizado". Ao mexer no prompt, não tire essas regras.
- `core/speech.py` + `modules/tts.py`: voz (edge-tts em partes, pygame). `core/voice_route.py`: a voz sai no
  aparelho que pediu; também diz se o pedido é remoto (`is_remote()`).
- `core/runtime.py`: WebSockets (`manager.broadcast`, em paralelo e com prazo por aparelho), `track`/`track_service`.
- `core/confirm.py`: ações que esperam "sim" (`offer(kind, data)` / `answer(norm)`).
- `modules/access.py` + `modules/sentinel.py`: bloqueio real; rotas não listadas como públicas exigem a central liberada.
- Inicialização (V8.11): `modules/autostart.py` (atalho na Inicialização do Windows → `scripts/ligar_jarvis.py`, sem
  janela), `scripts/guardiao.py` (religa o backend se cair; respeita `logs/iniciando.flag`, que o
  `Iniciar-JARVIS.bat` deixa enquanto liga/atualiza) e a atualização ao abrir a central (`auto_on_open` em
  `/api/system/update/status`, regra em `frontend/src/utils/updateCheck.js`). O `Parar-JARVIS.bat` encerra o
  guardião primeiro. Mudou o `.bat`? Mantenha CRLF (há teste) e não use `echo texto%var%> arquivo` (vira `2>`).
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
- Dados persistentes: `settings.DATA_DIR / "<arquivo>.json"` num atributo `_PATH` do módulo, com
  `safe_io.read_json`/`write_json`, e o caminho entra no `_WRITABLE_SKILLS` do `tests/conftest.py`.
- Grupo na aba ⚡ HABILIDADES: o módulo vira o grupo; dê nome e ícone em `GROUPS` de
  `frontend/src/utils/skillsCatalog.js` (sem isso aparece com o nome do arquivo).
- Cartão na tela: use o cartão genérico `{"type": "skill", "data": {"tag": "TÍTULO", "source": "resumo",
  "rows": [{"label": "...", "value": "..."}]}}` (renderizado por `ReactiveCard.jsx`). Componente próprio só se
  a skill realmente precisar de interação.
- Uma skill pode usar outra com `await ctx.call("nome", ...)` (passa pelas mesmas regras) e oferecer uma ação com
  `confirm.offer("skill", {"name": ..., "args": {...}})` (o "sim" do usuário executa).
- Skill demorada (mais que o prazo do turno da IA, `LLM_TURN_BUDGET_S`) fica com `llm=False` e mostra o progresso
  com `ctx.broadcast({"type": "agent", "agent": ..., "label": ..., "icon": ..., "status": "working|done|error",
  "text": ...})`. Skill que só deve rodar depois de um "sim" vindo de outro código: sem `triggers` e `llm=False`.
- Gatilho que depende do estado do PC (ex.: programa aberto) vai num `parse` rápido e com cache; se não
  reconhecer, devolve `None` para a frase seguir para as funções legadas e a IA.

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

`backend/tests/test_skill_<nome>.py`, com o fixture `real_skills` (catálogo só com as skills reais, central
liberada) e trocando o que toca o sistema (Windows, psutil, agenda, Spotify) por falsos via `monkeypatch`.
Cobre: frases → skill e parâmetros, frases legadas que NÃO podem ser capturadas, execução feliz, erro e (se
crítica) o fluxo do "sim". Referências: `tests/test_skill_workspace.py` e `tests/test_skills_engine_811.py`.
Atualize também a tabela da skill em `docs/COMANDOS.md` (seção "Skills").

### Ao entregar uma skill, explique

O que ela faz, como o JARVIS a aciona (frases de exemplo e/ou chamada pela IA) e quais arquivos foram
criados/afetados.

## Roadmap combinado (auditoria V8.11)

Feito: Q1 a Q4 (prazo da IA, JSON atômico com cache, broadcast em paralelo, ouvido sem travar com
"Jarvis, para"), Q8 ("abrir" desconhecido ou de sistema só com "sim": `skills/abrir_programa.py`), o motor de
Skills e as skills Workspace (`skills/workspace/`), System Guard (`skills/system_guard.py`), Context Autopilot
(`skills/context_autopilot.py`), Deep Brief (`skills/deep_brief.py`; pesquisa com fontes por chamada via
`llm_orchestrator.ask_web`), Clipboard AI (`skills/clipboard_ai.py`), conversor e senha (`skills/dia_a_dia.py`),
"quais são suas habilidades" (`skills/habilidades.py`), Q5 a Q7 e a aba ⚡ HABILIDADES da Central de Agentes
(`frontend/src/components/SkillsPanel.jsx` + `utils/skillsCatalog.js`).

V9.0: memória pesquisável (`modules/memory_index.py`, SQLite + FTS5, e `skills/memoria_busca.py`), copiados por
voz (`skills/copiados.py`), tempo de tela (`skills/tempo_de_tela.py`), OCR offline (`skills/ocr_tela.py`),
navegador por CDP (`skills/navegador/`), voz que começa antes (`core/early_voice.py` + `speech.speak_after`),
fila de pedidos (`core/turn_queue.py` no backend, `utils/turnQueue.js` na central), paleta Ctrl+K
(`components/CommandPalette.jsx` + `utils/palette.js`) e o clima por hora (`utils/mood.js`, `v9.css`).

V9.1: vidro em toda a interface (`frontend/src/glass.css`: use as variáveis `--g-*` em superfície nova, não
um gradiente próprio), janela do Spotify (`SpotifyWidget.jsx`), Configurações com menu lateral e o Branding Book
3.0 (`docs/branding-book.html`: atualize o capítulo e o histórico a cada lançamento visual).

V9.1.2/V9.2: desempenho da central (vidro pintado nas superfícies fixas — não ponha `backdrop-filter` em algo
que fica sempre na tela; animações só com transform/opacity; `utils/frameWatch.js` + `utils/slowSpin.js` = modo
econômico automático) e a auto-análise do PC (`skills/auto_analise.py`, aviso calmo no `system_guard`).
V9.3: segurança (`skills/seguranca/`: vigia da câmera com `face.look_once`, pendrive, otimização do dia; relatório em
`/api/security/report` + `components/SecurityReport.jsx`). A câmera é única: use `session.auth_lock` para usá-la.

Próximos, na ordem sugerida:
- Skills: Quick Capture com escrita no Google Agenda.
- Estruturais: logs estruturados com latência por etapa, desmontar `handle_turn` em skills, barramento de eventos.
- Migração gradual: ao mexer num handler de `tools.py` ou num bloco de `turns.py`, prefira movê-lo para uma Skill.
