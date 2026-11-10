# JARVIS v4.1 — Registro da atualização

Base: `JARVIS_V4_bkp29-10.zip`. Implementa as seções 14 a 18 da documentação de atualização
(palmas, Ouvinte de Palmas, câmera ao vivo, funções da tela de bloqueio e água animada) e o
documento do **Modo Sentinela**.

## 1. Decisões tomadas (confirmadas pelo Patrick)

| Decisão | Escolha |
| --- | --- |
| Modo Sentinela | Opção em Configurações > Bloqueio, **desligado por padrão** (respeita "com tudo desligado, a tela é igual à atual") |
| Bloqueio no backend | **Real**: rotas pessoais respondem 403 com a tela bloqueada ou no modo visitante (interruptor para voltar ao modo só visual) |
| Palavras de ativação | "Jarvis", "Ei, Jarvis", "Tá acordado" + o nome da IA (se trocar para A.R.E.S, "Ares" também vale) |
| Clima bloqueado | Liberado (hora, data, clima, cumprimentos, identidade, contas, timers e foco) |

Outras decisões de implementação (documentadas por não estarem fechadas nos textos):

- **Modo visitante** ganhou interruptor próprio (`lock_guest_enabled`, desligado), já que cada função da seção 17 precisa de interruptor.
- **Cartões padrão** (`lock_cards = ["clock", "weather"]`) seguem a tabela 17.8; desligando-os, a tela clássica fica igual à anterior.
- **Entrar sozinho** (`clap_auto_enter`) vale para qualquer acesso autorizado (palma, botão ou PIN). Um pedido pendente do Sentinela também entra sozinho.
- **Sem PIN cadastrado**, a troca de foto continua possível na tela de bloqueio (caminho de recuperação). **Com PIN**, trocar a foto exige acesso liberado (senão seria um atalho para burlar o rosto).
- **F5 na central** volta à tela de bloqueio (como antes) e agora também bloqueia o backend.
- **Modo visitante** não usa a IA (só respostas locais públicas e música), para não gastar cota nem expor memória.
- **Modo noturno** (22h–7h, Sentinela ligado): orbe mais escuro e voz com volume −35% enquanto a central estiver bloqueada.
- **Versão**: selo da tela de bloqueio e `/api/health` passam para 4.1.

## 2. O que foi implementado

### Seção 14 — Ativação por 2 palmas (página aberta)
- `frontend/src/utils/clapDetector.js`: função pura (piso de ruído adaptativo, fator/mínimo pela sensibilidade 1–10, recuperação de 60 ms, pico > 120 ms descarta, intervalo 120–800 ms, ~300 ms de silêncio antes, 400–900 ms depois, espera de 3 s).
- `frontend/src/hooks/useClapDetector.js`: microfone com `echoCancellation/noiseSuppression/autoGainControl` desligados, passa-alta de 1 kHz, **AudioWorklet por Blob URL** (alternativa: AnalyserNode + setInterval), respeita o microfone escolhido, status `off/starting/listening/blocked/unsupported/insecure/error`, aviso "Clique uma vez na tela para ativar as palmas" quando o AudioContext começa suspenso, e fecha as trilhas ao desligar.
- Tela de bloqueio: dica "Pressione espaço, clique ou bata palmas 2x", barras de nível, pulso no anel e som curto (`soundManager`, respeitando o modo silencioso). Em `ready` e `failed`; pausado com o JARVIS falando/processando ou escaneando.
- Configurações > **Palmas**: interruptor, sensibilidade, entrar sozinho, escopo, bloquear se falhar, avisos e **modo de teste** com medidor ao vivo e contador.
- Preferências `clap_wake_enabled`, `clap_sensitivity`, `clap_auto_enter` validadas no `PATCH /api/prefs`.

### Seção 15 — Palmas com o JARVIS fechado
- `scripts/clap_launcher.py` (`--list-devices`, `--test`, modo normal), `scripts/clap_detector.py` (mesma lógica do JS), `scripts/requirements-clap.txt` (separado do backend), `data/clap_launcher.json` criado com padrões.
- Decisão: backend desligado → `Iniciar-JARVIS.bat wake`; ligado sem página → `Abrir-Painel.bat wake`; com página → nada. Pausa a escuta (fecha o microfone) enquanto houver página aberta, consulta a cada 5 s, espera 30 s após disparar, bipe do Windows, desiste após 60 s sem backend, tenta abrir o microfone de novo a cada 30 s. Log só com horários.
- `.bat`: `Iniciar-Palmas.bat`, `Parar-Palmas.bat`, `Instalar-Palmas-no-Windows.bat` (atalho na pasta Inicializar, `pythonw.exe`) e `Remover-Palmas-do-Windows.bat`. `Iniciar-JARVIS.bat` e `Abrir-Painel.bat` aceitam `wake` (sem argumento, comportamento idêntico; com `wake`, espera backend e frontend responderem antes de abrir o navegador).
- `GET /api/presence` → `{"clients": N}`. `App.jsx` trata `?wake=clap` uma única vez e limpa o endereço.

### Seção 16 — Câmera ao vivo e verificação a cada palma
- `face.verify_against_profile(timeout, on_frame)`: quadros JPEG reduzidos (480 px, qualidade 70, até 12 qps — configuráveis por `FACE_STREAM_FPS/WIDTH/QUALITY`), caixa normalizada, similaridade e fase. Retorno inalterado; sem `on_frame`, comportamento idêntico. Comparação a cada 1–3 quadros conforme o custo medido; `FACE_THRESHOLD` não foi alterado; câmera liberada no `finally`.
- `POST /api/auth/verify` aceita `mode` (`login`/`recheck`) e `trigger`; quadros enviados com `run_coroutine_threadsafe` **somente para conexões locais** (`manager.send_local`), sem fila acumulada; `face_scan_start`/`face_frame`/`face_scan_end`. Nada é salvo (exceto a miniatura opcional da 17.2).
- Frontend: vídeo espelhado **dentro do orbe** (`ArcReactorHUD liveFrame`), `FaceScanOverlay` (cantos, varredura, barra de similaridade, "CÂMERA ATIVA"), `FaceRecheckPanel` (reverificação na central, "IDENTIDADE CONFIRMADA", fecha em ~3 s, vidro no Modo Torcedor).
- Reverificação fala só "Identidade confirmada, Patrick." e respeita o modo silencioso. Palmas ignoradas com o JARVIS ocupado, ouvindo, falando, com BioScan/Teste de Dispositivos ou Configurações abertos.
- Preferências `clap_scope` (padrão `always`) e `clap_relock_on_fail`.

### Seção 17 — Funções da tela de bloqueio
- **17.0** Bloqueio real: `backend/modules/access.py` (estado `locked/unlocked/guest`, política de rotas com negação por padrão, tabela no fim deste documento). `GET /api/prefs` e `GET /api/profile` devolvem só dados públicos quando restritos. Avisos de timer/lembrete ficam genéricos com a central bloqueada. Sem foto e sem PIN, nada é bloqueado.
- **17.1 PIN**: `backend/modules/lock_pin.py` (scrypt com sal, `hmac.compare_digest`, 5 erros → 5 min, dobrando até 30 min, persistente). Fase `pin` com teclado na tela e físico. Endpoints de status, verificação, criação/troca (exige acesso e PIN atual) e remoção. Aviso de PIN fraco.
- **17.2 Registro**: `backend/modules/lock_log.py` (últimas 200 entradas, sem imagens), aviso falado "Houve N tentativas não reconhecidas desde o último acesso", histórico com botão limpar em Configurações. Miniatura opcional (`lock_save_failed_photo`, desligada) em `data/intruders/`, máx. 20, apagadas após 30 dias.
- **17.3 Resumo do dia**: reaproveita o fluxo existente do `enterMain` (sem duplicar o briefing), agora com `lock_daily_summary` (`off`/`first_login`/`always`), próximo jogo (Modo Torcedor) e água de ontem, limitado a ~20 s (partes opcionais saem primeiro), exibido na resposta e com botão "pular" (Esc também pula).
- **17.4 Cartões**: `LockCards.jsx` (relógio, clima, próximo jogo, água de hoje), escondidos durante o escaneamento, visual de vidro no Modo Torcedor.
- **17.5 Bloqueio por ausência**: 5/10/15/30 min; aviso "Bloqueando em 30 s. Mexa o mouse para cancelar."; checagem de presença opcional (`GET /api/face/present`, 2 checagens, sem salvar imagem); não bloqueia falando/processando/verificando; ao bloquear fecha microfone e câmera da central.
- **17.6 Modo visitante**: `GuestScreen.jsx` (relógio, clima, música, perguntas públicas por voz/texto); rotas pessoais 403; sair exige rosto ou PIN; entrada/saída no registro.
- **17.7 Som e música**: som padrão, `sounds/intro.mp3` ou desligado; playlist (`lock_intro_playlist_uri`/`fan_intro_playlist_uri`) via `spotify.play_playlist` com volume subindo, depois da saudação; ignora em silêncio sem Premium/dispositivo; nada no modo silencioso nem na reverificação.

### Seção 18 — Água animada
- `WaterVessel.jsx` (SVG + clipPath; copo, garrafa e reator; duas ondas animadas por `transform`; fio de água, impacto nas ondas, 4–8 bolhas, contador sincronizado; animações redirecionadas sem empilhar; desfazer desce suave; meta batida enche a borda, brilha, solta gotas e um novo recipiente desliza, com o anterior virando ícone de concluído; pausa fora da tela; `prefers-reduced-motion`; `role="img"` + `aria-live`).
- `WaterPanel.jsx` (`size` compact/full): botões rápidos editáveis com ícones, "outro valor" (aceita "0,5 L"), desfazer (`POST /api/water/undo`), último registro, ritmo do dia, som sintetizado opcional, alvos de 44 px. Usado no cartão do chat, no widget e no painel flutuante.
- Pedido "índice de água"/"bebi 300 ml" abre o painel completo, que fecha após ~6 s sem interação, a menos que seja fixado (📍).
- **Inconsistência corrigida**: o texto da resposta é atualizado junto com o cartão (`water_updated`), usando a mesma frase do backend.
- Configurações > **Hidratação** com pré-visualização dos 3 recipientes, valores rápidos, meta, ritmo e som.

### Modo Sentinela
- Layout próprio (relógio e data discretos, orbe maior, "MODO BLOQUEIO · Diga 'Jarvis'", MIC ATIVO com botão de silenciar, "ESPAÇO = LIBERAR", link "alterar foto" no canto), estados do orbe (dormindo, ouvindo, pedindo liberação em âmbar, escaneando, autorizado, negado) e modo noturno.
- `useSentinelListener.js`: escuta contínua com reinício automático e palavra de ativação no começo da frase (janela de 8 s após só a palavra).
- Backend `modules/sentinel.py`: classificador público × protegido antes da IA; respostas públicas sem nome nem dados pessoais; protegido devolve `requires_unlock` e a frase de liberação; "o que tenho hoje" responde só números.
- Pedido pendente: após a fala, abre a câmera; reconhecido → entra e executa o pedido sem repetir; não reconhecido → nega e descarta. 3 falhas seguidas pausam a escuta por 3 min.
- "Jarvis, bloquear" / "modo sentinela" bloqueia a central (diferente de "bloquear a tela", que continua bloqueando o Windows).

### Correções encontradas no caminho
- `main.py` usava `requests` sem importar (cartão e rota de finanças caíam sempre no valor fixo).
- `widget_layout` não existia no `PrefsRequest`: a posição dos widgets nunca era salva.
- O CORS ficava por dentro do middleware de segurança: respostas 401/403 chegavam ao navegador como erro de rede. Agora o CORS envolve tudo.
- Cartões explícitos de uma ação substituem os detectados automaticamente (o cartão de água com `open_panel` não era usado).

## 3. Testes executados

| Conjunto | Comando | Resultado |
| --- | --- | --- |
| Backend (pytest, 18 antigos + 40 novos) | `cd backend && python -m pytest -q tests` | 58 aprovados |
| Detector e ouvinte em Python | `python -m pytest -q scripts/tests` | 35 aprovados |
| Frontend (node --test) | `cd frontend && npm test` | 34 aprovados |
| Sintaxe/imports do frontend | bundle com esbuild + ESLint `no-undef` | sem erros |
| Fluxo completo no Chromium (Playwright) | backend real com câmera/voz simuladas e microfone falso tocando 2 palmas | 40/40 verificações |

O teste no navegador confirmou: palmas reais (áudio) iniciando o escaneamento, câmera ao vivo no orbe, entrada automática, reverificação por palma, painel de água (300 → 800 → desfazer 300, texto acompanhando, fechamento em 6 s), "Jarvis, bloquear", falha de rosto → PIN errado/certo, registro de tentativas, modo visitante (403 nas rotas pessoais, pergunta pública respondida, pessoal recusada), Sentinela, `?wake=clap` e as abas novas de Configurações.

**Não testado neste ambiente (precisa do seu PC):** webcam e reconhecimento facial reais, voz real (edge-tts/pygame), reconhecimento de voz do Chrome para o Sentinela, `sounddevice` e os `.bat` no Windows, Spotify Premium, build com Vite/Tailwind (o ambiente não tinha acesso ao npm; o frontend foi validado com esbuild e um subconjunto de estilos), tempo real de bloqueio por ausência (mínimo de 5 min).

## 4. Pendências e ideias para depois
- Ajustar a sensibilidade das palmas no seu ambiente (modo de teste) e conferir falsos positivos de TV/portas.
- Conferir no Windows se o detector de palmas e o reconhecimento de voz funcionam juntos na central (se houver conflito, usar `clap_scope = lock`).
- Sentinela: frase-senha por voz, reconhecimento da sua voz, controle de casa e saudação ao chegar (ideias "para depois" do documento) não foram feitos.
- Prova de vida (anti-foto) continua fora do escopo: o reconhecimento compara com a foto de perfil.
- O estado de bloqueio é do backend inteiro (um usuário). Com o modo rede, o celular segue o mesmo estado do PC (abrir o painel pelo celular não bloqueia o PC; o escaneamento usa a webcam do PC).

## 5. Como executar e verificar
1. `Iniciar-JARVIS.bat` (instala o que faltar). Em Configurações > Palmas, ligue as palmas e use o modo de teste.
2. Configurações > Bloqueio: crie um PIN, escolha cartões, ausência, visitante, som/playlist e, se quiser, o Modo Sentinela.
3. Configurações > Hidratação: escolha o recipiente. Diga "bebi 300 ml" ou "como está minha água".
4. Palmas com o JARVIS fechado: `Iniciar-Palmas.bat` (ou `Instalar-Palmas-no-Windows.bat`). Teste: `backend\venv\Scripts\python.exe scripts\clap_launcher.py --test`.
5. Testes (opcional): `backend\venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt`; depois, na raiz do projeto, `backend\venv\Scripts\python.exe -m pytest -q backend\tests scripts\tests` e `cd frontend && npm test`.

## 6. Rotas da API no modo bloqueado e no modo visitante

Tudo o que começa com `/api` e não está liberado abaixo responde **403** (`{"code": "locked"}` ou `{"code": "guest"}`). Com a central liberada, todas as rotas funcionam como antes.

| Rota | Método | Bloqueado (Sentinela) | Visitante |
| --- | --- | --- | --- |
| `/api/about` | GET | 403 | 403 |
| `/api/about` | POST | 403 | 403 |
| `/api/access` | GET | permitido | permitido |
| `/api/access/lock` | POST | permitido | permitido |
| `/api/auth/pin` | DELETE | 403 | 403 |
| `/api/auth/pin` | POST | permitido | permitido |
| `/api/auth/pin/set` | POST | 403 | 403 |
| `/api/auth/pin/status` | GET | permitido | permitido |
| `/api/auth/token` | GET | permitido | permitido |
| `/api/auth/verify` | POST | permitido | permitido |
| `/api/briefing` | GET | 403 | 403 |
| `/api/cameras` | GET | 403 | 403 |
| `/api/cancel` | POST | permitido | permitido |
| `/api/chat` | POST | permitido | permitido |
| `/api/datasources` | GET | 403 | 403 |
| `/api/enter` | POST | 403 | 403 |
| `/api/face/present` | GET | 403 | 403 |
| `/api/fan/match` | GET | permitido | permitido |
| `/api/fan/match/reminder` | POST | 403 | 403 |
| `/api/fan/news` | GET | 403 | 403 |
| `/api/fan/schedule` | GET | 403 | 403 |
| `/api/finance` | GET | 403 | 403 |
| `/api/focus` | GET | 403 | 403 |
| `/api/focus/start` | POST | 403 | 403 |
| `/api/focus/stop` | POST | 403 | 403 |
| `/api/guest/enter` | POST | permitido | permitido |
| `/api/guest/exit` | POST | permitido | permitido |
| `/api/health` | GET | permitido | permitido |
| `/api/health/biometrics` | GET | 403 | 403 |
| `/api/health/biometrics` | POST | permitido | permitido |
| `/api/health/ble-scan` | GET | 403 | 403 |
| `/api/health/connect-ble` | POST | 403 | 403 |
| `/api/integrations/google-calendar` | DELETE | 403 | 403 |
| `/api/integrations/google-calendar/authorize` | GET | 403 | 403 |
| `/api/integrations/google-calendar/callback` | GET | permitido | permitido |
| `/api/integrations/google-calendar/events` | GET | 403 | 403 |
| `/api/integrations/google-calendar/status` | GET | 403 | 403 |
| `/api/integrations/spotify` | DELETE | 403 | 403 |
| `/api/integrations/spotify/authorize` | GET | 403 | 403 |
| `/api/integrations/spotify/callback` | GET | permitido | permitido |
| `/api/integrations/spotify/control` | POST | 403 | permitido |
| `/api/integrations/spotify/now-playing` | GET | 403 | permitido |
| `/api/integrations/spotify/play` | POST | 403 | 403 |
| `/api/integrations/spotify/status` | GET | 403 | permitido |
| `/api/lock/intro-music` | POST | 403 | 403 |
| `/api/lock/log` | DELETE | 403 | 403 |
| `/api/lock/log` | GET | 403 | 403 |
| `/api/lock/summary-data` | GET | 403 | 403 |
| `/api/logs` | GET | 403 | 403 |
| `/api/memory` | GET | 403 | 403 |
| `/api/memory` | POST | 403 | 403 |
| `/api/network-access` | GET | 403 | 403 |
| `/api/news` | GET | 403 | 403 |
| `/api/prefs` | GET | permitido | permitido |
| `/api/prefs` | PATCH | 403 | 403 |
| `/api/presence` | GET | permitido | permitido |
| `/api/profile` | GET | permitido | permitido |
| `/api/profile` | POST | só sem PIN | 403 |
| `/api/profile/photo` | GET | 403 | 403 |
| `/api/reminders` | GET | 403 | 403 |
| `/api/reminders` | POST | 403 | 403 |
| `/api/reminders/{rem_id}` | DELETE | 403 | 403 |
| `/api/search/execute` | POST | 403 | 403 |
| `/api/search/quota` | GET | 403 | 403 |
| `/api/shortcuts` | GET | 403 | 403 |
| `/api/shortcuts` | POST | 403 | 403 |
| `/api/shortcuts/{name}` | DELETE | 403 | 403 |
| `/api/speak` | POST | permitido | permitido |
| `/api/system` | GET | 403 | 403 |
| `/api/system/volume` | PATCH | 403 | 403 |
| `/api/tasks` | GET | 403 | 403 |
| `/api/tasks` | POST | 403 | 403 |
| `/api/tasks/{task_id}` | DELETE | 403 | 403 |
| `/api/tasks/{task_id}/complete` | PATCH | 403 | 403 |
| `/api/timers` | GET | permitido | permitido |
| `/api/trigger-jarvis` | POST | 403 | 403 |
| `/api/water` | GET | permitido | permitido |
| `/api/water/add` | POST | 403 | 403 |
| `/api/water/goal` | POST | 403 | 403 |
| `/api/water/reset` | POST | 403 | 403 |
| `/api/water/undo` | POST | 403 | 403 |
| `/api/weather` | GET | permitido | permitido |

Total: 82 combinações rota/método.
