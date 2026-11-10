# JARVIS — Fase 1 (instruções para o GitHub Copilot)

> Leia este arquivo inteiro antes de qualquer ação. Ele vale para toda esta conversa.

## Projeto

Assistente pessoal local, em português (BR), rodando no Windows.
- Backend: Python + FastAPI. `backend/main.py` (rotas e WebSocket `/ws`), `backend/modules/` (tools, prefs, tts, event_log, google_calendar, spotify, tasks, reminders, briefing, memory...), `backend/services/llm_orchestrator.py` (IA: Gemini, OpenAI, Anthropic), `backend/config/settings.py`.
- Frontend: React + Vite + Tailwind. `frontend/src/App.jsx`, `frontend/src/components/*.jsx`, `frontend/src/index.css`, `frontend/tailwind.config.js`.
- Início: `Iniciar-JARVIS.bat`.

## Regras

- Faça **só o item pedido**. Não refatore nem renomeie nada fora dele.
- **Nunca** leia, edite ou mostre o `.env`. Não adicione dependências sem perguntar.
- Antes de editar, diga **quais arquivos** vai alterar e **o que** vai mudar.
- Mantenha o comportamento atual: o que já funciona não pode quebrar.
- Textos de interface e logs em português do Brasil, **com acentuação correta**, no mesmo estilo dos existentes.
- Ao terminar: diga **como testar** e espere minha confirmação antes do próximo item.
- Valide com `python -m py_compile` (backend) e `npm run build` (frontend).

**Já existe, não refazer:** HUD com reator, widgets flutuantes, painel de configurações, OAuth do Spotify e do Google Calendar (rotas `/api/integrations/...`), registro de eventos (`/api/logs`), `/api/health`, WebSocket `/ws`.

## Regras extras

- **Não faça commit, push nem apague arquivos.** Eu faço o commit depois de testar. Se um arquivo precisar ser removido, pergunte.
- **Não altere** a pasta `data/` (memória, atalhos, configurações e tokens do usuário), os arquivos `.bat`, as portas (backend 8000, frontend 5173) nem as origens permitidas (CORS), sem me avisar antes.
- **Preserve o final de linha de cada arquivo** (alguns usam CRLF) e salve tudo em UTF-8.
- **Se achar outro problema fora do item pedido, só me avise.** Não corrija por conta própria.
- **Se algo estiver ambíguo, pergunte** (no máximo 3 perguntas) em vez de adivinhar.
- Mudanças **pequenas**: prefira editar o que existe e seguir o estilo do código vizinho (nomes, organização, comentários).
- **Nunca registre** chaves, tokens ou conteúdo de notas no `event_log` nem no console.

## Armadilhas conhecidas deste projeto

- Estou no **Windows**: use PowerShell/`cmd`, não comandos do Linux. O caminho da pasta pode ter **espaços e acentos**, então sempre use aspas nos caminhos.
- O backend sobe pelo `Iniciar-JARVIS.bat` com `--host 0.0.0.0` (necessário para o acesso pelo celular via QR Code). Não mude isso.
- Em `backend/modules/tools.py`, a **ordem** dos handlers em `_HANDLERS` importa: um handler novo pode “roubar” comandos de outro. Se criar um, diga onde pretende colocá-lo.
- O `.env` é lido só na inicialização: mudanças em `settings.py` ou no `.env` exigem reiniciar o backend.
- A escolha do provedor de IA vem primeiro de **Configurações** (arquivo em `data/`) e depois do `.env`. Se a chave do provedor escolhido não existir, o código já pula para outro.

## Formato da resposta ao terminar cada item

1. Arquivos alterados (lista).
2. O que mudou, em 3 a 5 linhas.
3. Como testar, passo a passo, incluindo o que devo ver na tela.
4. Riscos ou dúvidas que ficaram.

## Tarefas da Fase 1 (um item por vez)

### 1. Tokens de design
Adicionar as cores abaixo ao tema (`tailwind.config.js` e variáveis em `index.css`) **sem mudar a aparência atual**; só acrescentar.

| Token | Hex | Uso |
|---|---|---|
| fundo-base | #070B12 | Fundo |
| superficie | #0F172A | Cards |
| superficie-elevada | #1E293B | Hover e modais |
| borda | #1E3A5F | Contornos |
| primaria | #22D3EE | Destaques e foco |
| primaria-forte | #06B6D4 | Botões |
| sucesso | #34D399 | Conectado |
| alerta | #FBBF24 | Atenção |
| erro | #F87171 | Falha |
| texto | #E2F3FF | Texto principal |
| texto-suave | #94A3B8 | Legendas |

**Pronto quando:** as classes existem e o `npm run build` passa, sem mudança visual.

### 2. Componentes reutilizáveis
Criar em `frontend/src/components/`: `ConnectorCard`, `StatusBadge` e `Toggle`. Estados: normal, hover, desativado, erro e carregando. Badge: Conectado (verde), Adicionar (neutro), Sincronizando (azul), Erro (vermelho), Desativado (cinza). Nunca indicar o estado só pela cor: incluir ícone e texto.

**Pronto quando:** os três componentes aceitam propriedades simples e ainda não alteram nenhuma tela.

### 3. Tela “Fontes de Dados”
Novo painel `DataSourcesPanel.jsx`, aberto a partir da interface atual (seguir o padrão do `SettingsPanel`). Mostrar cards do **Google Calendar** e do **Spotify**, usando os endpoints de status, autorizar e desconectar que já existem. Grid: 1 coluna no celular, 2 em telas médias, 3 em telas grandes. Seção “Disponíveis” com cartões desativados para futuros conectores.

**Pronto quando:** dá para conectar e desconectar os dois serviços por essa tela.

### 4. Health check e “última sincronização”
Backend: criar `GET /api/integrations/status` que devolva, para cada integração, `connected`, `last_ok` (data/hora da última resposta com sucesso) e `latency_ms`. Mostrar esses dados nos cards.

**Pronto quando:** cada card exibe “sincronizado há X min” e o tempo de resposta.

### 5. Contador de uso da IA
Backend: contar por provedor, por dia, chamadas com sucesso e com erro (incluindo 429), guardando em um JSON na pasta `data/`. Criar `GET /api/llm/usage` e mostrar um resumo na tela de Fontes de Dados.

**Pronto quando:** dá para ver quantas chamadas cada provedor recebeu hoje e quantas falharam.

### 6. Fallback entre provedores de IA
Em `_call_llm` (`llm_orchestrator.py`): se o provedor escolhido falhar (erro de cota, rede ou chave inválida), tentar automaticamente os outros que tenham chave configurada, na ordem gemini, openai, anthropic. Registrar cada troca no `event_log`. Não mudar a escolha salva em Configurações.

**Pronto quando:** com a cota do Gemini esgotada e outra chave configurada, o JARVIS ainda responde.

### 7. Segurança (somente análise)
**Não altere nada.** Liste as rotas do `main.py` que mudam estado ou expõem dados pessoais (por exemplo `/api/speak`, `/api/chat`, `/api/memory`, `/api/shortcuts`, `/api/profile`) e proponha como protegê-las sem quebrar o acesso pelo celular via QR Code. Aguarde minha aprovação.

**Pronto quando:** recebo a lista e a proposta, sem nenhum arquivo alterado.

### 8. Voz reserva feminina (quando a voz principal falhar)
Em `backend/modules/tts.py`: hoje, se o `edge_tts` falhar (erro 403, rede ou outro), o JARVIS fica mudo. Fazer com que, nesse caso, ele fale com uma voz do Windows.

- **Sem novas dependências:** usar PowerShell com `System.Speech` via `subprocess` (só usar `pyttsx3` se eu aprovar).
- **Voz feminina pt-BR:** escolher por gênero e idioma (`SelectVoiceByHints` com Female e `pt-BR`). Se não houver voz feminina, usar qualquer voz pt-BR. Se não houver nenhuma, registrar um aviso e não travar.
- Gerar um arquivo WAV e tocar pelo **mesmo caminho do pygame** que já existe, para o cancelamento da fala e o visualizador de ondas continuarem funcionando.
- A cada fala, tentar primeiro o `edge_tts` normal. Assim a voz principal volta sozinha quando o serviço voltar.
- Registrar no `event_log`: “Voz principal falhou; usando voz reserva”.
- Configurações novas lidas em `settings.py` com valores padrão (`TTS_FALLBACK=windows`, `TTS_FALLBACK_VOICE` vazio). Só incluí-las no `.env.example`; não mexer no `.env`.

**Pronto quando:** com a internet desligada (ou com o erro 403), o JARVIS ainda responde falando com voz feminina; com o serviço normal, ele volta à voz do Antonio.

## Como começar

Primeira mensagem para o Copilot (não altera nada):
> Leia `COPILOT-FASE1.md` e o código do projeto. Resuma em 5 linhas o que entendeu e diga se algo no arquivo não bate com o código.

Depois, um item por vez (troque o número):
> Faça apenas o item 1 de `COPILOT-FASE1.md`. Antes de editar, liste os arquivos e as mudanças. Depois diga como testar e espere minha confirmação.

Ordens sugeridas:
- Para resolver primeiro o erro de cota (429): item 6, depois o 5.
- Para resolver primeiro a voz que fica muda (erro 403): item 8, que é independente dos outros.
