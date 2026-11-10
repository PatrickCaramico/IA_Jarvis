# API do JARVIS

Referência gerada a partir do código (`scripts/dev/gerar_api_md.py`). Com o JARVIS ligado, a
documentação interativa do FastAPI fica em `http://127.0.0.1:8000/docs`.

**Acesso:** `sempre` = funciona até com a central bloqueada; `visitante` = também no modo visitante;
`liberada` = só depois do rosto ou do PIN (o servidor responde 403 `{code: "locked"}`).
Fora deste computador, toda chamada precisa do cabeçalho `X-Jarvis-Token` (ou `?token=`) e do modo rede.

## Sistema, conversa e WebSocket

Arquivo: `backend/routes/system.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/health` | sempre | Estado dos serviços (backend, IA, câmera, perfil, timers). |
| GET | `/api/auth/token` | sempre | Retorna o token de acesso (permitido apenas para requisições locais). |
| GET | `/api/network-access` | liberada | Retorna o endereço local para outro dispositivo na mesma rede. |
| GET | `/api/timers` | sempre | Timers ativos. |
| POST | `/api/cancel` | sempre | Botão Cancelar: corta a voz na hora, para os avisos e descarta a resposta que estiver a caminho. |
| POST | `/api/chat` | sempre | Conversa (digitada ou falada). |
| POST | `/api/trigger-jarvis` | liberada | Rotina completa: câmera + notícias + IA. |
| WS | `/ws` | token na rede | Canal em tempo real com a interface (eventos abaixo). |
| POST | `/api/speak` | sempre | Fala um texto com o TTS do assistente (feedback de opções selecionadas). |
| GET | `/api/cameras` | liberada | Detecta webcams conectadas e retorna o índice selecionado. |
| GET | `/api/logs` | liberada | Últimos eventos registrados. |
| GET | `/api/diagnostics` | liberada | V4.2.2: diagnóstico sem segredos para o botão "Copiar diagnóstico" (rota protegida pelo bloqueio). |

## Acesso: rosto, PIN, visitante e bloqueio

Arquivo: `backend/routes/access.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| POST | `/api/auth/verify` | sempre | Olha pela webcam, compara com a foto de perfil e fala a saudação. |
| GET | `/api/access` | sempre | Estado de acesso atual (bloqueada, liberada ou visitante). |
| POST | `/api/access/lock` | sempre | Volta para a tela de bloqueio (botão sair, bloqueio por ausência ou F5). |
| GET | `/api/auth/pin/status` | sempre | Se há PIN cadastrado e se está temporariamente travado. |
| POST | `/api/auth/pin` | sempre | Libera a central com o PIN. |
| POST | `/api/auth/pin/set` | liberada | Cadastra ou troca o PIN. |
| DELETE | `/api/auth/pin` | liberada | Remove o PIN. |
| POST | `/api/guest/enter` | sempre | Modo visitante: só relógio, clima e música. As rotas pessoais passam a responder 403. |
| POST | `/api/guest/exit` | sempre | Sai do modo visitante para a tela de bloqueio (liberar exige rosto ou PIN). |
| GET | `/api/lock/log` | liberada | Registro de tentativas de acesso. |
| DELETE | `/api/lock/log` | liberada | Apaga o registro de tentativas e as fotos de intrusos. |
| GET | `/api/presence` | sempre | Quantas páginas do JARVIS estão abertas (usado pelo Ouvinte de Palmas). Sem dados sensíveis. |
| GET | `/api/face/present` | liberada | Checagem rápida de presença (bloqueio por ausência): só detecta rosto, não compara nem salva. |
| POST | `/api/enter` | liberada | Chamado quando o usuário entra na tela principal. |
| GET | `/api/lock/summary-data` | liberada | Dados extras do resumo do dia (seção 17.3): próximo jogo (Modo Torcedor) e água de ontem. |
| POST | `/api/lock/intro-music` | liberada | Som/música de abertura (seção 17.7): só depois do login, nunca no modo silencioso. |

## Perfil, "sobre mim" e preferências

Arquivo: `backend/routes/profile.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/about` | liberada | Lê o texto "sobre mim". |
| POST | `/api/about` | liberada | Salva o texto "sobre mim". |
| GET | `/api/profile` | sempre | Nome e se há foto de perfil. |
| GET | `/api/profile/photo` | liberada | Foto de perfil. |
| POST | `/api/profile` | liberada | Cadastra ou troca nome e foto de perfil. |
| GET | `/api/prefs` | sempre | Retorna todas as preferências do JARVIS (nome da IA, tema de cores, widgets, câmera, cota, cooldown). |
| PATCH | `/api/prefs` | liberada | Atualiza parcialmente as preferências. |
| GET | `/api/prefs/export` | liberada | Baixa as preferências em JSON (sem chaves, PIN, rosto, memórias nem índice da câmera). |
| POST | `/api/prefs/import` | liberada | Aplica um arquivo exportado. Passa pelas mesmas validações do PATCH /api/prefs. |

## Hidratação

Arquivo: `backend/routes/water.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/water` | sempre | Retorna o progresso hídrico de hoje. |
| POST | `/api/water/add` | liberada | Registra uma ingestão de água em ml. |
| POST | `/api/water/reminder` | liberada | Ajusta a frequência e o horário do lembrete de água. |
| POST | `/api/water/undo` | liberada | Desfaz o último registro de hoje. |
| POST | `/api/water/goal` | liberada | Atualiza a meta diária de ingestão de água. |
| POST | `/api/water/reset` | liberada | Zera o consumo de hoje. |

## Atalhos, tarefas, lembretes, foco, briefing e memória

Arquivo: `backend/routes/productivity.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/sites` | liberada | Lista os sites abertos por voz e pela tela de configurações. |
| POST | `/api/sites` | liberada | Cria ou atualiza um site com URL, apelidos e janela do Chrome. |
| PUT | `/api/sites/{name}` | liberada | Atualiza um site existente. |
| DELETE | `/api/sites/{name}` | liberada | Remove um site da lista de atalhos. |
| GET | `/api/shortcuts` | liberada | Lista os atalhos personalizados. |
| POST | `/api/shortcuts` | liberada | Cria ou atualiza um atalho personalizado. |
| DELETE | `/api/shortcuts/{name}` | liberada | Remove um atalho personalizado. |
| GET | `/api/tasks` | liberada | Lista as tarefas. |
| POST | `/api/tasks` | liberada | Cria uma tarefa. |
| PATCH | `/api/tasks/{task_id}/complete` | liberada | Conclui uma tarefa. |
| DELETE | `/api/tasks/{task_id}` | liberada | Apaga uma tarefa. |
| GET | `/api/reminders` | liberada | Lista os lembretes. |
| POST | `/api/reminders` | liberada | Cria um lembrete. |
| DELETE | `/api/reminders/{rem_id}` | liberada | Apaga um lembrete. |
| GET | `/api/focus` | liberada | Estado do modo foco (Pomodoro). |
| POST | `/api/focus/start` | liberada | Inicia o modo foco. |
| POST | `/api/focus/stop` | liberada | Encerra o modo foco. |
| GET | `/api/briefing` | liberada | Resumo do dia em texto corrido (o "bom dia" na central usa o briefing em etapas). |
| POST | `/api/briefing/skip` | liberada | V4.3: pula para o próximo assunto do briefing em andamento (corta só a fala atual). |
| GET | `/api/memory` | liberada | Memórias salvas. |
| POST | `/api/memory` | liberada | Salva uma memória. |
| GET | `/api/protocols` | liberada | Protocolos salvos (ou os exemplos padrão) e as ações disponíveis. |
| POST | `/api/protocols/run` | liberada | Executa um protocolo pelo nome (a resposta traz o texto e os passos que falharam). |
| GET | `/api/triggers` | liberada | Gatilhos condicionais com os ajustes do usuário aplicados sobre os padrões. |
| GET | `/api/routine` | liberada | Hábitos encontrados para as sugestões pela rotina e as sugestões silenciadas. |
| POST | `/api/routine/unmute` | liberada | Volta a permitir todas as sugestões que foram silenciadas com "não sugira mais". |
| GET | `/api/notifications` | liberada | Central de notificações (experimental): status da leitura e as últimas notificações. |
| DELETE | `/api/notifications` | liberada | Limpa a lista do JARVIS (as notificações do Windows não são apagadas). |

## Informações: notícias, sistema, volume, clima, finanças

Arquivo: `backend/routes/info.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/news` | liberada | Radar de notícias do HUD: destaques por categoria (RSS do Google News). |
| GET | `/api/system` | liberada | CPU, memória, disco e volume do computador. |
| PATCH | `/api/system/volume` | liberada | Muda o volume do Windows. |
| GET | `/api/weather` | sempre | Retorna dados estruturados para o widget de clima. |
| GET | `/api/finance/expenses` | liberada | V4.5: gastos e entradas que você contou ao JARVIS (sem banco), por período. |
| POST | `/api/finance/expenses` | liberada | add expense |
| GET | `/api/finance` | liberada | Retorna cotações de moedas e mercado financeiro em tempo real (AwesomeAPI). |
| GET | `/api/datasources` | liberada | Catálogo unificado de fontes de dados e canais do JARVIS. |

## Busca profunda

Arquivo: `backend/routes/search.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/search/quota` | liberada | Retorna o status da cota diária de pesquisa profunda. |
| POST | `/api/search/execute` | liberada | Executa a pesquisa no modo escolhido (navegador ou profunda com IA). |

## Modo Torcedor

Arquivo: `backend/routes/fan.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/fan/news` | liberada | Notícias recentes do clube via Google News / GE. |
| GET | `/api/fan/match` | sempre | Informações da partida atual ou próxima agendada do clube. |
| GET | `/api/fan/logo/{side}` | sempre | Serve o escudo do Palmeiras local ou o escudo do adversário em cache. |
| POST | `/api/fan/toggle` | sempre | V4.4: liga/desliga o Modo Torcedor pelo botão da tela de bloqueio. |
| GET | `/api/fan/schedule` | liberada | Retorna os próximos jogos do clube com links para o Google Calendar. |
| POST | `/api/fan/match/reminder` | liberada | Cria um lembrete local e link do Google Agenda para a partida. |

## Integrações (Google Agenda e Spotify)

Arquivo: `backend/routes/integrations.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| POST | `/api/integrations/spotify/control` | visitante | Controles simples de música (também liberados no modo visitante). |
| GET | `/api/integrations/google-calendar/status` | liberada | Se o Google Agenda está configurado e conectado. |
| GET | `/api/integrations/google-calendar/authorize` | liberada | Inicia o login no Google Agenda. |
| GET | `/api/integrations/google-calendar/callback` | sempre | Retorno do login do Google (OAuth). |
| DELETE | `/api/integrations/google-calendar` | liberada | Desconecta o Google Agenda. |
| GET | `/api/integrations/google-calendar/events` | liberada | Próximos eventos da agenda. |
| GET | `/api/integrations/spotify/status` | visitante | Se o Spotify está configurado e conectado. |
| GET | `/api/integrations/spotify/track` | sempre | Faixa atual em partes para o cartão "Tocando agora" (bloqueado: só com o cartão Spotify ligado). |
| GET | `/api/integrations/spotify/now-playing` | visitante | Música tocando agora. |
| POST | `/api/integrations/spotify/play` | liberada | Procura e toca uma música ou playlist. |
| GET | `/api/integrations/spotify/authorize` | liberada | Inicia o login no Spotify. |
| GET | `/api/integrations/spotify/callback` | sempre | Retorno do login do Spotify (OAuth). |
| DELETE | `/api/integrations/spotify` | liberada | Desconecta o Spotify. |

## Saúde (biometria e relógios Bluetooth)

Arquivo: `backend/routes/health.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/health/biometrics` | liberada | Retorna os dados biométricos atuais persistidos. |
| POST | `/api/health/biometrics` | sempre | Atualiza a telemetria do smartwatch recebida via Android Sync / Webhook ou BLE. |
| GET | `/api/health/ble-scan` | liberada | Escaneia o ambiente Bluetooth buscando relógios ou sensores BLE. |
| POST | `/api/health/connect-ble` | liberada | Conecta ou associa um dispositivo Bluetooth escaneado. |

## JARVIS no celular

Arquivo: `backend/routes/mobile.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/mobile/info` | sempre | Pública (tela de bloqueio): dá o QR de download, sem token. |
| GET | `/api/mobile` | sempre | Página que abre ao escanear o QR do bloqueio: baixar o app e como conectar. |
| GET | `/api/mobile/app.apk` | sempre | mobile apk |
| POST | `/api/mobile/pair-pin` | sempre | Pareia o app digitando o PIN do perfil principal (V4.5). Devolve o endereço com a chave. |
| GET | `/api/mobile/notifications` | sempre | Avisos para o app Android (lembretes, água, gatilhos, Modo Torcedor). |
| GET | `/api/mobile/pair` | liberada | Página de pareamento (exige o token, que já veio no QR da central liberada). |

## Perfis por pessoa

Arquivo: `backend/routes/profiles.py`

| Método | Rota | Acesso | O que faz |
| --- | --- | --- | --- |
| GET | `/api/profiles/lock-info` | sempre | Pública (tela de bloqueio): só diz se dá para criar e se pede o PIN do dono. Nenhum nome. |
| GET | `/api/profiles` | liberada | Com a central liberada: lista as pessoas deste PC. |
| POST | `/api/profiles` | sempre | Cria o perfil de uma pessoa nova, entra com ele e libera a central para a configuração inicial. |
| DELETE | `/api/profiles/{profile_id}` | liberada | Só o dono, com a central liberada, remove perfis (a pasta da pessoa é apagada). |

## Eventos do WebSocket (`/ws`)

| Evento | Quando |
| --- | --- |
| `state` | idle, processing ou speaking |
| `step` | etapa do processamento (câmera, notícias, IA, voz) |
| `response` / `error` / `alert` | resposta, erro ou aviso de timer/lembrete |
| `access_state` | central bloqueada, liberada ou em modo visitante |
| `face_scan_start` / `face_frame` / `face_scan_end` | escaneamento facial ao vivo (só para este computador) |
| `sentinel_reply` | resposta do Modo Sentinela |
| `water_updated` | mudança no registro de água |
| `prefs_updated` / `fan_shout` | Modo Torcedor ligado sozinho / grito da torcida |
| `notice` / `reset` | aviso curto / limpar a resposta anterior |
| `briefing_start` | "bom dia": abas do briefing, saudação e abertura ("Sem desvios relevantes") |
| `briefing_step` | um assunto do briefing: aba, texto de progresso e o card falado agora |
| `briefing_end` | fim do briefing: todos os cards, prontidão e recomendação do dia |

Total: 114 rotas.
