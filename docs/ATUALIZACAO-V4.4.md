# Atualização V4.4: central em espera limpa e cabeçalho novo

4 de novembro de 2026. Ajustes de posicionamento depois de testar a 4.3 (briefing em etapas).

## O que muda para você

### Modo em espera só com o orbe

Depois que você entra (rosto ou PIN) e o JARVIS cumprimenta, **as duas colunas recolhem juntas**
após 10 segundos: a da esquerda (telemetria, serviços, tarefas) e, agora também, a da direita
(clima e Canal Ativo). Fica só o orbe, a frase do dia e a faixa **DIGA:** com os atalhos
("bom dia", "boa noite", "notícias", "notificações", "e-mails", "agenda", "clima", "tarefas",
"comandos").

- A coluna da direita **não reabre mais a cada fala do JARVIS**. Ela reabre quando **você** fala
  (microfone) ou envia um pedido, e nunca durante o briefing.
- Para abrir na mão, use as abas nas bordas: "▶ TELEMETRIA & SERVIÇOS" à esquerda e
  "◀ CLIMA & CANAL ATIVO" à direita.
- Ao fechar a fileira de cards de um briefing (✕), a central volta para esse modo em espera limpo.
- A regra antiga continua: sem uso por 3 minutos, a coluna da direita recolhe sozinha.

### Cabeçalho em três zonas

| Zona | O que tem |
| --- | --- |
| Esquerda | Botão ☰ (menu), logo Núcleo, nome do assistente e "ASSISTENTE PESSOAL · v4.4" |
| Centro | ⚡ CONTROLES, agora no centro exato da tela (alinhado com o orbe) |
| Direita | Status combinado "● SISTEMA ONLINE · VOZ LIVRE" (a voz muda para OUVINDO, PROCESSANDO ou FALANDO, em âmbar), relógio com a data embaixo ("QUA · 04 NOV"), ÁUDIO e SPOTIFY num grupo só, CANCELAR quando há algo em andamento, SAIR e a foto do perfil |

Um filete de luz ciano marca a borda de baixo do cabeçalho (verde no Modo Torcedor). Em telas
menores, o cabeçalho esconde primeiro a data e o subtítulo e depois os textos do status, sem
sobrepor os botões.

### Outros

- Versão **4.4** em `/api/health`, no topo da central, na tela de bloqueio e na tela extra (as duas
  últimas mostravam "v4.2.2" fixo; agora usam `frontend/src/utils/version.js`).

### Fundo blueprint (5 de novembro)

O fundo virou uma planta técnica azul: azul royal com brilho no centro, grade fina a cada 20 px e
grade forte a cada 100 px. Vale na central, na tela de bloqueio (clássica e Sentinela), na
inicialização e no modo visitante. No bloqueio entram também uma moldura com marcas de régua, um
círculo tracejado de cota em volta do orbe, um brilho que atravessa a tela devagar e o carimbo
"J.A.R.V.I.S. · FOLHA · REV. v4.4" no canto inferior direito (some em telas pequenas).

- Painéis e cartões ganharam um vidro azul-marinho mais escuro, para o texto continuar legível.
- O Reator Arc do bloqueio ganhou destaque próprio: um invólucro azul-marinho atrás dos anéis, um
  halo claro que "respira", anéis e marcações mais claros e o núcleo com brilho mais forte. Na
  Sentinela ele não é mais escurecido enquanto espera (só à noite, de leve). O "alterar foto" subiu
  para não ficar embaixo do carimbo.
- Para conferir o visual sem backend: `frontend/lock-demo.html` no modo dev
  (`?mode=classic`, `?fan=1`, `?bg=classic`). Não entra no build.
- No Modo Torcedor a planta fica verde.
- É tudo CSS, sem imagem. Na central nada se mexe no fundo (os painéis usam desfoque, que ficaria
  pesado com fundo animado). O brilho do bloqueio desliga com "reduzir movimento" do Windows.
- Para voltar ao fundo escuro antigo: **Configurações > Geral > Fundo > Clássico escuro** (salva e
  aplica na hora). A escolha fica guardada no navegador, então a próxima abertura já começa certa.

### Inicialização mais rápida (5 de novembro)

| Antes | Agora |
| --- | --- |
| Interface em modo de desenvolvimento (`npm run dev`): o Vite compilava tudo a cada abertura | Interface já compilada (`frontend/dist`) num servidor leve em Python (`scripts/serve_frontend.py`), que sobe em ~0,5 s. Mesmo endereço de antes (`http://127.0.0.1:5173`), então câmera, microfone e preferências do navegador continuam valendo |
| Build manual | O `Iniciar-JARVIS.bat` refaz o build sozinho só quando algum arquivo da interface mudou (só nessa vez demora uns 10 s). Se o build falhar, cai no modo de desenvolvimento |
| Espera fixa de 4 s antes de abrir e mais 4 s no fim | Abre o painel assim que o backend e a interface respondem |
| Backup diário antes de tudo | Backup depois que o painel já abriu |
| A voz (`edge_tts` + `aiohttp`) era carregada na subida do backend | A voz carrega em segundo plano logo depois que o servidor sobe. No perfil de importação, `core.watchers` caiu de 4,8 s para 0,5 s |

O mesmo vale para o `Iniciar-JARVIS-Rede.bat`. Para desenvolver com recarga ao vivo, use o
`Iniciar-JARVIS-Dev.bat` (continua com `npm run dev` e `--reload`). O `Parar-JARVIS.bat` não mudou:
ele já encerra o que estiver nas portas 8000 e 5173.

### Modo Torcedor com jogo de verdade (5 de novembro)

Antes, a agenda do Palmeiras era **fixa no código, com jogos inventados**, então o "dia de jogo"
nunca batia com a realidade. Agora:

- **Agenda e placar reais, sem IA e sem token:** a ESPN (JSON público, sem chave) dá os jogos de
  todas as competições, com horário de Brasília, estádio e placar ao vivo. O **Google Notícias** (RSS)
  confirma o dia de jogo pelas matérias "onde assistir" publicadas hoje e serve de reserva se a ESPN
  cair (aí aparece "horário a confirmar"). Nenhuma chamada a modelo de IA.
- **Entra sozinho no Modo Torcedor** no dia do jogo e avisa: "Hoje tem Palmeiras contra o Remo às
  19:30, no Allianz Parque. Modo Torcedor ativado. Avante Palestra!". No dia seguinte sai sozinho.
  Se você desligar na mão no dia do jogo, ele não liga de novo até o próximo jogo. A opção vem ligada
  (aba Torcedor > "ativar em dia de jogo"); quem tinha desligado antes passou a ter ligada uma vez.
- **Gol do Palmeiras:** "GOOOOL!" em tela cheia por 8 s, com placar, minuto e uma explosão verde e
  branca, mais a voz "GOOOL DO PALMEIRAS!". Gol do adversário: um cartão discreto, "Vamos virar,
  Verdão!". Tocar fecha.
- **Placar no bloqueio:** em dia de jogo aparece um cartão verde acima do relógio, com "AO VIVO · 34'"
  ou "HOJE · 19:30".
- **Faixa da central** com mandante certo ("Remo x Palmeiras" fora de casa), horário, contagem e a
  fonte ("ESPN · Google Notícias").
- **Visual:** a planta continua azul; só o layout fica verde (painéis, barra superior, moldura,
  carimbo "· MODO TORCEDOR" e o reator, com anéis, núcleo e halo verdes).
- "Agenda de jogos" e "lembrar do jogo" por voz agora usam os jogos reais. O aviso "o jogo começa em
  X minutos" não dispara quando o horário não é conhecido.

**Ajustes depois do primeiro jogo (Palmeiras x Remo, 5/11):**

- **Fala repetida corrigida:** ao reiniciar com o jogo rolando, o JARVIS dizia "Hoje tem Palmeiras
  contra o Remo às 19:30... Avante Palestra!" e, no mesmo segundo, o grito "Avante Palestra!" de novo.
  Agora é uma fala só, com o momento certo ("Bola rolando: Palmeiras 2 a 0 Remo, aos 19 minutos.
  Modo Torcedor ativado. Avante Palestra!"). Ativação, grito, intervalo e fim valem uma vez por jogo,
  e gols que saíram antes de abrir não são comemorados.
- **Painel do jogo no bloqueio** (coluna da esquerda): escudos, placar, barra de tempo, gols e
  expulsões com autor e assistência, posse, finalizações, chutes no gol e escanteios, posição na tabela
  e o próximo jogo. Antes do jogo mostra a contagem ("1h 35 para a bola rolar"); depois, VITÓRIA,
  EMPATE ou DERROTA. Em telas menores fica só o placar.
- **Gol com autor:** a tela e a voz dizem quem marcou ("GOOOL DO PALMEIRAS! Maurício, aos 21
  minutos. Palmeiras 3 a 0 Remo.").
- **Intervalo e fim de jogo** com cartão e fala ("Fim de jogo: Palmeiras 3 a 1 Remo. Vitória do
  Verdão!"); explosão na tela só na vitória.
- Os detalhes vêm do mesmo resumo público da ESPN (`/summary`), conferido a cada ~50 s durante o
  jogo e a cada 10 min no resto do dia de jogo. Continua sem IA.

**Botão do Modo Torcedor no bloqueio (5/11, 20h):**

- Ao lado do carimbo, no canto inferior direito, há um botão **⚽ MODO TORCEDOR · LIGADO/DESLIGADO**.
  Ele funciona com a central bloqueada (rota pública `POST /api/fan/toggle`, que só troca o visual do
  clube; o resto das configurações continua travado). A escolha pelo botão vale como sua: o JARVIS não
  a desfaz sozinho naquele dia nem desliga no dia seguinte o que você ligou.
- **Por que ele "não iniciou direto":** um teste antigo (`test_fan_mode.py`) ligava e desligava o
  Modo Torcedor no `data/jarvis_settings.json` **de verdade**, e ao rodar a bateria de testes às
  19:58 ele deixou o modo desligado. Como o JARVIS já tinha ligado sozinho naquele dia, ele achou que
  foi você quem desligou e não religou. Agora **todos os testes** gravam numa pasta temporária
  (`backend/tests/conftest.py`), conferido comparando o conteúdo de `data/` antes e depois, e o modo
  foi religado nas suas configurações.

**O Iniciar sempre substitui uma versão aberta (5/11, 20h15):** o botão do Modo Torcedor não
trocava porque o backend no ar ainda era o de antes da rota do botão. Rodar o `Iniciar-JARVIS.bat`
com o JARVIS já aberto fazia a versão nova falhar escondida (porta ocupada) e a antiga continuava.
Agora o `Iniciar-JARVIS.bat` (e o de rede) encerra o que estiver nas portas 8000 e 5173 antes de
subir, avisando "JARVIS já estava aberto: reiniciando com a versão atual...". E se o botão falhar,
ele mostra em âmbar "REINICIE O JARVIS" ou "SEM RESPOSTA" por 5 s, em vez de ficar mudo.

O placar é conferido a cada ~50 s durante o jogo (de 20 min antes até 3 h depois), a agenda a cada
6 h e o Google a cada 30 min. Tudo fica em `data/fan_cache.json`, então sem internet ele mostra o
último dado conhecido ou "Agenda indisponível" (nunca inventa jogo).

## Para quem mexe no código

| Arquivo | O que mudou |
| --- | --- |
| `frontend/src/components/HudLayout.jsx` | Recolhe as duas colunas no fim da inicialização e ao fechar o briefing; a direita só reabre com pedido seu. Cabeçalho novo (`hl-icon-btn`, `hl-brand-name`, `hl-status`, `hl-clockbox`, `hl-actions`). `useBrasiliaClock()` devolve hora e data. |
| `frontend/src/hud-layout.css` | Grade de três zonas no `.hl-top` e estilos do cabeçalho; regras de tela estreita. |
| `frontend/src/fan-mode.css` | Cores do cabeçalho novo no Modo Torcedor. |
| `frontend/src/components/LockScreen.jsx`, `ScreensPopout.jsx` | Versão lida de `APP_VERSION`. |
| `backend/version.py`, `frontend/src/utils/version.js` | 4.4 (conferidas por `backend/tests/test_v422.py`). |
| `frontend/src/blueprint.css` (novo) | Fundo blueprint, ativo com `<html data-bg="blueprint">`: grade, vidro dos painéis, moldura/régua, cota do orbe, brilho e carimbo (`.bp-stamp`). |
| `frontend/src/utils/theme.js`, `main.jsx`, `App.jsx` | `applyBackground()` / `initialBackground()` (guarda em `localStorage.jarvis_bg`); aplicado ao carregar e ao mudar as preferências. |
| `frontend/src/components/SettingsPanel.jsx` | Seletor "FUNDO" na aba Geral (salva na hora por `PATCH /api/prefs`). |
| `frontend/src/components/LockScreen.jsx` | `BlueprintStamp` no bloqueio clássico, na Sentinela e na tela de inicialização. |
| `backend/modules/prefs.py`, `backend/routes/profile.py` | Preferência `background_style` (`"blueprint"` padrão, ou `"classic"`), pública para a tela de bloqueio e validada no PATCH. |
| `backend/modules/tts.py`, `backend/main.py` | `edge_tts` importado sob demanda; `tts.preload()` roda em segundo plano no `lifespan`. |
| `scripts/serve_frontend.py` (novo) | Servidor estático multi-thread do `dist`, com tipos MIME fixos (o registro do Windows às vezes manda `.js` como texto), cache longo em `/assets/` e `--stale` para saber se o build está velho. |
| `Iniciar-JARVIS.bat`, `Iniciar-JARVIS-Rede.bat`, `Atualizar-Frontend.bat` | Build automático quando preciso, servidor leve, espera pelo `/api/health`, backup no fim. |
| `backend/modules/sports_provider.py` | Reescrito: `refresh()` (rede, com validade por tipo de dado) busca a agenda (`/all/teams/2029/schedule`) e o placar (`/summary`) da ESPN e o RSS do Google Notícias; `get_current_or_next_match()`, `get_schedule()` e `create_match_reminder()` só leem o cache; `detect_score_change()` acha gols; `auto_state()`/`set_auto_state()` guardam quem ligou o modo. Saiu a agenda inventada. |
| `backend/modules/fan_mode.py` | `espn_team_id`, `matchday_query` e `goal_phrase` do Palmeiras. |
| `backend/core/watchers.py` | `fan_watcher_loop` atualiza os dados, liga/desliga sozinho (`_fan_auto_mode`), grita na bola rolando e manda `fan_goal`. |
| `backend/modules/prefs.py` | `fan_auto_on_match_day` passa a vir ligado (migração `_v44_fan_auto`, uma vez). |
| `backend/core/turns.py`, `routes/fan.py`, `modules/triggers.py` | Usam os dados reais; o aviso de "começa em X minutos" ignora jogo sem horário. |
| `frontend/src/hooks/useFanMatch.js` (novo) | Lê `/api/fan/match` (30 s perto/durante o jogo, 2 min no resto); `matchSides()` e `matchTime()`. |
| `frontend/src/components/FanGoalOverlay.jsx` (novo), `FanMatchBanner.jsx`, `LockScreen.jsx` (`FanLockScoreboard`), `FanScoreWidget.jsx`, `App.jsx` | Comemoração de gol, faixa nova, placar no bloqueio, mandante certo na agenda, eventos `fan_goal` e aviso de ativação. |
| `frontend/src/fan-mode.css`, `frontend/src/blueprint.css` | Estilos `fmb-*`, `fls-*`, `fgo-*`; no Modo Torcedor a planta fica azul e o layout verde. |
| `frontend/src/dev/lockDemo.jsx` | Demo com `?fan=1`, `&live=0` e `&goal=goal|conceded|shout`. |
| `backend/tests/test_fan_matchday_44.py` (novo) | 10 testes: leitura da ESPN e do Google, jogo só pelo Google, sem dados, gols, validade do cache, liga/desliga sozinho e migração. |
| `docs/BRANDING-BOOK.md`, `docs/branding-book.html` | v1.3: capítulo "Planta e Modo Torcedor", cores da planta com contraste medido e histórico. |

Conferido na página de demonstração (`frontend/briefing-demo.html`) em 1900×860 e 1300×700: o
centro do cabeçalho, o botão CONTROLES e o orbe ficam no mesmo eixo. 156 testes do backend e o
build da interface passam.
