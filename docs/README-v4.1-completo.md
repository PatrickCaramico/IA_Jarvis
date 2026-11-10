# 🤖 JARVIS — Assistente Pessoal v4.1

> Assistente pessoal local com voz, câmera e inteligência artificial.  
> Backend em **Python + FastAPI** · Frontend em **React + Vite + Tailwind CSS**

---

## 📋 Índice

1. [Visão Geral](#-visão-geral)
2. [Funcionalidades](#-funcionalidades)
3. [Pré-requisitos](#-pré-requisitos)
4. [Instalação](#-instalação)
5. [Como Executar](#-como-executar)
6. [Estrutura de Arquivos](#-estrutura-de-arquivos)
7. [Comandos de Voz](#-comandos-de-voz)
8. [API REST](#-api-rest)
9. [Configuração](#-configuração)
10. [Temas de Cores](#-temas-de-cores)
11. [Roteiro de Funcionalidades](#-roteiro-de-funcionalidades)
12. [Solução de Problemas](#-solução-de-problemas)
13. [Integrações OAuth](#-integrações-oauth)

---

## 🌟 Visão Geral

O JARVIS é um assistente pessoal local que roda inteiramente no seu computador. Ele combina:

- **Reconhecimento de voz** direto no navegador (Web Speech API)
- **Síntese de voz** realista em português via `edge-tts` (voz `pt-BR-AntonioNeural`)
- **Inteligência Artificial** via Gemini, OpenAI ou Anthropic
- **Pesquisa atualizada no Gemini** via Google Search Grounding (quando ativada)
- **Câmera + reconhecimento facial** para saudação personalizada
- **Funções locais** que funcionam sem internet: timers, tarefas, lembretes, notas, Pomodoro
- **Funções com internet**: clima, cotação de moedas, notícias e pesquisa no Google

A interface tem estética **futurista inspirada no Iron Man** (tema padrão azul), com fonte Orbitron e animações de HUD.

---

## ✅ Funcionalidades

### Fase 1 — Base do dia a dia ✅
- Abrir programas e sites com lista de atalhos permitidos
- Menu de perfil com foto e nome
- Personalização: nome da IA, tema de cores, widgets visíveis
- Atalhos personalizados (abrir múltiplos apps + URLs de uma vez)
- Controle do sistema: volume, brilho, mute, bloquear tela, print
- Seleção de câmera (detecta automaticamente as webcams conectadas)

### Fase 2 — Produtividade ✅
- Lista de tarefas por voz ("adiciona comprar pão")
- Lembretes com data e hora que sobrevivem ao fechar o JARVIS
- Modo Foco / Pomodoro com timer e som ambiente
- Anotações com busca, leitura e exclusão por voz
- Resumo do dia ao dizer "bom dia" (clima + tarefas + lembretes + notícias)

### Modo Torcedor — Glassmorphism (Palmeiras) ✅
- Tema com estética Glassmorphism, escudo translúcido central e gradientes em verde e branco
- Widget com notícias em tempo real do Palmeiras direto do GE (Globo Esporte)
- Widget de placar e contagem regressiva para a próxima partida
- Banner superior de Dia de Jogo com status ao vivo da partida
- Grito de torcida "Avante Palestra!" com bola rolando (respeitando modo silencioso)
- Ativação por voz ("ativar modo torcedor"), pelo menu de controles `⚡ CONTROLES` ou nas Configurações

### Hidratação & Lembrete de Água (Fase W) ✅
- Widget holográfico com copo animado em SVG e nível de água dinâmico
- Registro rápido (+200ml, +300ml, +500ml) ou por voz ("bebi um copo de água", "bebi 300ml")
- Meta diária ajustável, percentual em tempo real e celebração ao atingir 100%
- Lembretes periódicos de hidratação nos horários do operador (respeitando modo silencioso)

### Tela de bloqueio inteligente, palmas e hidratação animada (v4.1) ✅
Detalhes, decisões e pendências em [`docs/ATUALIZACAO-V4.1.md`](docs/ATUALIZACAO-V4.1.md).
- **Ativação por 2 palmas** na tela de bloqueio (e, opcionalmente, reverificação do rosto a cada palma com a central aberta). A palma só inicia o escaneamento; o rosto continua obrigatório.
- **Câmera ao vivo** durante o escaneamento: vídeo dentro do orbe, cantos no rosto e barra de similaridade (quadros só para conexões deste computador, nunca salvos).
- **Ouvinte de Palmas** (`Iniciar-Palmas.bat`): com o JARVIS fechado, 2 palmas ligam tudo e já iniciam o leitor facial.
- **PIN de reserva**, **registro de tentativas**, **resumo do dia** ao entrar, **cartões** na tela de bloqueio, **bloqueio por ausência**, **modo visitante** e **som/música de abertura**.
- **Bloqueio real no backend**: com a tela bloqueada (ou no modo visitante), as rotas pessoais respondem 403.
- **Modo Sentinela** (opcional): tela de bloqueio só com orbe e relógio; o JARVIS escuta "Jarvis" e responde hora, data e clima; para mostrar algo pessoal, pede o escaneamento e executa o pedido pendente.
- **Recipiente de água animado** (copo, garrafa ou reator) com ondas, fio de água, bolhas, contador, desfazer, valor livre, ritmo do dia e comemoração da meta.

### Funções sempre disponíveis
- Timers e alarmes por voz
- Consulta de clima (Open-Meteo, sem chave de API)
- Cotação de dólar, euro e bitcoin (AwesomeAPI, sem chave de API)
- Calculadora por voz
- Pesquisa no Google e YouTube
- Pesquisa dinâmica no Google: abre o navegador, lê trechos públicos dos resultados e resume por voz
- Comandos naturais como "me mostra ..." também abrem a pesquisa em uma nova guia
- Integração Spotify via OAuth para tocar, pausar, avançar, voltar e informar a faixa atual
- Painel Spotify na interface com status da conexão, faixa atual e botões de reprodução
- Busca e reprodução de música ou playlist específica pelo nome
- Controle por voz das abas do navegador: próxima, anterior, nova, fechar e reabrir
- Janela flutuante do Spotify na hub, com arraste, redimensionamento, tela cheia, minimizar, fechar e seleção de monitor
- O comando "abrir Spotify" foca o aplicativo desktop já aberto no Windows ou o inicia, e mostra o reator em popup até o retorno à hub
- Indicador do reator em popup separado durante pesquisas externas, fechado ao retornar para a hub
- Reconhecimento facial para saudação personalizada
- QR Code para acesso por celular na mesma rede local
- Contador do tempo da sessão logada no cabeçalho
- Mini painel de áudio com visualizador reativo e controle do volume do Windows
- Janelas flutuantes arrastáveis pela barra de título e redimensionáveis
- Relógio digital flutuante com horário de Brasília, segundos e data completa
- Painel automático de início com mensagem motivacional, clima, relógio e tarefas
- Saudação falada ao iniciar cada conversa, com horário, clima, inspiração do dia e tarefas ativas
- Apresentação de boas-vindas falada antes da saudação com o resumo inicial
- Transcrição de conversa limpa automaticamente após um minuto de inatividade
- Registro persistente de comandos e erros, consultável por "JARVIS, relatório do log"

---

## 🔧 Pré-requisitos

| Requisito | Versão mínima | Para que serve |
|---|---|---|
| Python | 3.11+ | Backend (FastAPI, edge-tts, opencv) |
| Node.js | 18+ | Frontend (Vite, React) |
| npm | 8+ | Gerenciar dependências do frontend |
| Chave de API Gemini | — | Inteligência artificial (recomendado) |
| Chave OpenAI (opcional) | — | Alternativa à IA |
| Chave Anthropic (opcional) | — | Alternativa à IA |
| Webcam (opcional) | — | Reconhecimento facial e câmera |
| Microfone | — | Reconhecimento de voz |

> **Nota:** O reconhecimento de voz usa a API nativa do navegador Google Chrome. Use o Chrome para melhor compatibilidade.

---

## 📦 Instalação

### 1. Clone ou baixe o projeto

```bash
# Se for clonar
git clone <url-do-repositorio>
cd jarvis_assistant
```

### 2. Configure as variáveis de ambiente

Copie o arquivo de exemplo e edite com as suas chaves:

```bash
copy .env.example .env
```

Edite o `.env` e preencha pelo menos a chave do Gemini:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=sua_chave_aqui
GEMINI_SEARCH_GROUNDING=true
```

Com `GEMINI_SEARCH_GROUNDING=true`, o Gemini pode consultar informações atuais
pela ferramenta Google Search Grounding. A chave precisa ter acesso à API Gemini
e o computador precisa estar conectado à internet.

Se o provedor salvo nas preferências não tiver uma chave configurada, o JARVIS
seleciona automaticamente o primeiro provedor disponível, priorizando o Gemini
quando há `GEMINI_API_KEY`. Isso evita que pesquisas atuais falhem por uma
preferência antiga de provedor.

### 3. Instale as dependências do backend

```bash
cd backend
pip install -r requirements.txt
```

### 4. Instale as dependências do frontend

```bash
cd frontend
npm install
```

---

## ▶️ Como Executar

Você precisa de **dois terminais** abertos ao mesmo tempo.

### Terminal 1 — Backend

```bash
cd jarvis_assistant\backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

O backend estará disponível em: `http://localhost:8000`

### Terminal 2 — Frontend

```bash
cd jarvis_assistant\frontend
npm run dev
```

O frontend estará disponível em: `http://localhost:5173`

Abra o navegador Chrome em `http://localhost:5173`.

Para abrir no celular, computador e celular precisam estar na mesma rede Wi-Fi.
O atalho **Abrir no celular** gera um QR Code com o endereço LAN do computador.
O frontend é iniciado em `0.0.0.0` para aceitar conexões da rede. Se o celular
não abrir o endereço, permita as portas TCP `5173` e `8000` no Firewall do
Windows e confirme que a rede está marcada como privada.

> **Dica:** Use o atalho `Espaço` para ativar o microfone e falar com o JARVIS.

---

## 📁 Estrutura de Arquivos

```
jarvis_assistant/
├── .env                        ← Variáveis de ambiente (NÃO versionar)
├── .env.example                ← Template de variáveis (versionar)
├── README.md                   ← Esta documentação
│
├── backend/
│   ├── main.py                 ← Servidor FastAPI, rotas, WebSocket
│   ├── requirements.txt        ← Dependências Python
│   │
│   ├── config/
│   │   └── settings.py         ← Lê o .env e expõe constantes
│   │
│   ├── modules/
│   │   ├── tools.py            ← Pipeline de handlers locais (timers, notas, clima...)
│   │   ├── quick_replies.py    ← Respostas instantâneas sem IA (hora, data, cumprimentos)
│   │   ├── tasks.py            ← Lista de tarefas persistida
│   │   ├── reminders.py        ← Lembretes persistentes com worker background
│   │   ├── focus.py            ← Modo Foco / Pomodoro com som ambiente
│   │   ├── briefing.py         ← Resumo matinal (clima + tarefas + lembretes + notícias)
│   │   ├── prefs.py            ← Preferências (nome IA, tema, widgets, câmera)
│   │   ├── system_control.py   ← Controle de volume, brilho, mute, lock, print
│   │   ├── vision.py           ← Webcam (OpenCV), detecção de câmeras
│   │   ├── face.py             ← Reconhecimento facial (YuNet/SFace)
│   │   ├── tts.py              ← Síntese de voz (edge-tts + pygame)
│   │   ├── about.py            ← Texto "sobre o JARVIS"
│   │   ├── memory.py           ← Memória persistente
│   │   ├── event_log.py        ← Registro persistente de eventos e erros
│   │   ├── system_monitor.py   ← Coleta de status do sistema
│   │   ├── google_calendar.py  ← Integração Google Calendar via OAuth
│   │   └── spotify.py          ← Integração Spotify via OAuth
│   │
│   └── services/
│       └── llm_orchestrator.py ← Monta prompt e chama o LLM (Gemini/OpenAI/Anthropic)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx             ← Componente raiz, layout geral
│   │   ├── index.css           ← Estilos globais, scrollbar futurista
│   │   │
│   │   ├── components/
│   │   │   ├── ArcReactorHUD.jsx   ← Animação central (HUD do Iron Man)
│   │   │   ├── ProfileMenu.jsx     ← Menu de perfil com foto e toggle de widgets
│   │   │   ├── SettingsPanel.jsx   ← Painel de configurações (3 abas)
│   │   │   ├── ResponseBox.jsx     ← Caixa de resposta do JARVIS
│   │   │   ├── StatusPanel.jsx     ← Status do sistema (câmera, IA, perfil)
│   │   │   ├── AboutWidget.jsx     ← Widget "sobre"
│   │   │   ├── AppLauncher.jsx     ← Botões de atalho para apps
│   │   │   ├── ShortcutsWidget.jsx ← Lista de atalhos personalizados
│   │   │   ├── TodoWidget.jsx      ← Widget de tarefas com checkboxes
│   │   │   └── FocusWidget.jsx     ← Widget do timer Pomodoro
│   │   │
│   │   └── hooks/
│   │       └── useSpeechRecognition.js ← Reconhecimento de voz contínuo
│   │
│   ├── package.json
│   └── vite.config.js
│
└── data/                       ← Dados persistidos (criados automaticamente)
    ├── jarvis_settings.json    ← Preferências (nome IA, tema, widgets)
    ├── profile.json            ← Nome e perfil do usuário
    ├── profile.jpg             ← Foto de perfil para reconhecimento facial
    ├── tarefas.json            ← Lista de tarefas (criado quando usado)
    ├── lembretes.json          ← Lembretes com data/hora (criado quando usado)
    ├── anotacoes.json          ← Anotações por voz (criado quando usado)
    ├── atalhos.json            ← Sites e apps que podem ser abertos
    ├── respostas.json          ← Respostas personalizadas (editável)
    ├── memoria.json            ← Memórias salvas pelo usuário
    ├── eventos.json            ← Registro persistente de comandos e erros
    └── spotify_token.json      ← Token OAuth do Spotify (não versionar)
```

---

## 🎤 Comandos de Voz

Use o atalho **Espaço** para ativar o microfone. O JARVIS fica aguardando você falar.

### 🕐 Timers e Alarmes

| Exemplo de Comando | O que faz |
|---|---|
| "Cria um timer de 10 minutos" | Timer simples de 10 min |
| "Me avise em 30 segundos" | Timer de 30 seg |
| "Alarme de 1 hora e meia" | Timer de 90 min |
| "Me lembra de tomar remédio em 2 horas" | Timer com rótulo |
| "Quais timers estão ativos?" | Lista os timers |
| "Cancele os timers" | Cancela todos |

### ✅ Tarefas

| Exemplo de Comando | O que faz |
|---|---|
| "Adiciona comprar pão" | Cria nova tarefa |
| "Adicionar tarefa reunião amanhã" | Cria nova tarefa |
| "O que falta fazer hoje?" | Lista tarefas pendentes |
| "Quais são minhas tarefas?" | Lista tarefas |
| "Completar tarefa 1" | Marca como concluída |
| "Apaga a tarefa 2" | Remove a tarefa |

### 📅 Lembretes

| Exemplo de Comando | O que faz |
|---|---|
| "Lembrete: reunião amanhã às 14 horas" | Cria lembrete com data/hora |
| "Me lembra de ligar para o médico dia 15 às 9 horas" | Lembrete específico |
| "Quais são meus lembretes?" | Lista lembretes |
| "Cancele o lembrete 1" | Remove lembrete |

> **Nota:** Os lembretes também podem ser criados via timer ("me avise em X minutos") e sobrevivem ao fechar o JARVIS.

### 🎯 Modo Foco / Pomodoro

| Exemplo de Comando | O que faz |
|---|---|
| "Ativa o modo foco" | Pomodoro padrão (25 min foco + 5 min pausa) |
| "Inicia o modo foco por 45 minutos" | Foco com duração personalizada |
| "Desativa o modo foco" | Para o Pomodoro e o som |
| "Para o modo foco" | Para o Pomodoro |
| "Status do modo foco" | Informa tempo restante |

### 📝 Anotações

| Exemplo de Comando | O que faz |
|---|---|
| "Anote: reunião com cliente na sexta" | Salva anotação |
| "Guarda isso: senha do WiFi é 12345" | Salva anotação |
| "O que eu anotei?" | Lê as últimas 4 anotações |
| "Minhas anotações" | Lê as últimas 4 anotações |
| "O que anotei sobre reunião?" | Busca por palavra-chave |
| "Apaga a anotação sobre WiFi" | Remove anotações específicas |
| "Apaga todas as anotações" | Limpa todas as anotações |

### ☀️ Resumo do Dia (Briefing)

| Exemplo de Comando | O que faz |
|---|---|
| "Bom dia" | Resumo completo (clima + tarefas + lembretes + notícias) |
| "Resumo do dia" | Mesmo resumo completo |
| "Como está meu dia?" | Mesmo resumo completo |

### 🌤️ Clima

| Exemplo de Comando | O que faz |
|---|---|
| "Como está o tempo?" | Clima na cidade padrão |
| "Qual a previsão do tempo em Curitiba?" | Clima em outra cidade |
| "Vai chover amanhã?" | Previsão para amanhã |
| "Está frio hoje?" | Temperatura atual |

O widget consulta geocodificação e previsão no Open-Meteo, priorizando cidades
brasileiras. Se o serviço estiver indisponível, o painel mostra o erro e permite
uma nova tentativa pelo botão **Atualizar**.

### 💰 Cotações

| Exemplo de Comando | O que faz |
|---|---|
| "Quanto está o dólar?" | Cotação USD/BRL |
| "Qual é o euro hoje?" | Cotação EUR/BRL |
| "Valor do bitcoin" | Cotação BTC/BRL |

### 🧮 Calculadora

| Exemplo de Comando | O que faz |
|---|---|
| "Quanto é 15 vezes 8?" | Multiplicação |
| "Calcule 100 dividido por 4" | Divisão |
| "Raiz quadrada de 144" | Raiz quadrada |
| "Quanto é 20% de 500?" | Porcentagem |
| "2 elevado a 10" | Potenciação |

### 🖥️ Abrir Sites e Programas

| Exemplo de Comando | O que faz |
|---|---|
| "Abre o YouTube" | Abre youtube.com |
| "Abre o Gmail" | Abre mail.google.com |
| "Abre o VS Code" | Abre o Visual Studio Code |
| "Abre o Bloco de Notas" | Abre o Notepad |
| "Abre o Explorador de Arquivos" | Abre o Explorer |

> Os atalhos disponíveis estão em `data/atalhos.json`. Você pode adicionar novos!

### 🔍 Pesquisa no Navegador

| Exemplo de Comando | O que faz |
|---|---|
| "Pesquise Python tutorial" | Busca no Google |
| "Procure música lofi no YouTube" | Busca no YouTube |
| "Busca notícias sobre tecnologia" | Busca no Google |

### 🔊 Controle do Sistema

| Exemplo de Comando | O que faz |
|---|---|
| "Aumenta o volume" | Volume +20% |
| "Diminui o volume" | Volume -20% |
| "Volume no máximo" | Volume 100% |
| "Coloca no mudo" | Muta o áudio |
| "Tira o mudo" | Desmuta o áudio |
| "Aumenta o brilho" | Brilho +20% |
| "Diminui o brilho" | Brilho -20% |
| "Bloqueia a tela" | Bloqueia o Windows |
| "Tira um print" | Captura a tela |

### 💬 Conversa e Informações

| Exemplo de Comando | O que faz |
|---|---|
| "Que horas são?" | Hora atual |
| "Que dia é hoje?" | Data atual |
| "Quem é você?" | Apresentação do JARVIS |
| "O que você sabe fazer?" | Lista funcionalidades |
| "Status do sistema" | Diagnóstico de câmera, IA e perfil |
| "Obrigado" | Resposta de cortesia |

---

## 🌐 API REST

O backend expõe as seguintes rotas em `http://localhost:8000`.

### Sistema e conversa

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/health` | Status do servidor, provedor de IA e serviços |
| `GET` | `/api/network-access` | URL para acessar o frontend por outro dispositivo na rede local |
| `POST` | `/api/chat` | Envia uma mensagem: `{ "message": "..." }` |
| `POST` | `/api/trigger-jarvis` | Executa a rotina de saudação/briefing |
| `POST` | `/api/cancel` | Cancela a operação atual sem cancelar timers ou lembretes |
| `POST` | `/api/speak` | Reproduz texto com TTS: `{ "text": "..." }` |
| `POST` | `/api/enter` | Reproduz a saudação ao entrar na tela principal |
| `WS` | `/ws` | WebSocket para estados, progresso, respostas e alertas em tempo real |

### Perfil, câmera e autenticação facial

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/profile` | Retorna nome e se existe foto cadastrada |
| `GET` | `/api/profile/photo` | Retorna a foto de perfil |
| `POST` | `/api/profile` | Salva nome e foto em Base64/data URL |
| `POST` | `/api/auth/verify` | Verifica o rosto pela webcam. Corpo opcional `{ "mode": "login" \| "recheck", "trigger": "button" \| "clap" \| "wake" }`; envia `face_frame` ao vivo só para conexões locais |
| `GET` | `/api/auth/pin/status` | `has_pin`, `locked_until`, `remaining_attempts` |
| `POST` | `/api/auth/pin` | Libera com o PIN: `{ "pin": "1234" }` (5 erros bloqueiam por 5 min, dobrando até 30 min) |
| `POST` | `/api/auth/pin/set` | Cria/troca o PIN (exige acesso liberado e o PIN atual, se houver) |
| `DELETE` | `/api/auth/pin` | Remove o PIN: `{ "current_pin": "..." }` |
| `GET` | `/api/access` · `POST` `/api/access/lock` | Estado de acesso (`locked`, `unlocked`, `guest`) e bloquear |
| `POST` | `/api/guest/enter` · `/api/guest/exit` | Modo visitante (sair volta ao bloqueio) |
| `GET`/`DELETE` | `/api/lock/log` | Histórico de acessos (últimas 200 entradas) |
| `GET` | `/api/presence` | Número de páginas do JARVIS abertas (Ouvinte de Palmas) |
| `GET` | `/api/face/present` | Checagem rápida de presença (só detecção, sem salvar imagem) |
| `GET` | `/api/lock/summary-data` | Próximo jogo e água de ontem para o resumo do dia |
| `POST` | `/api/lock/intro-music` | Toca a playlist de abertura após a saudação |
| `POST` | `/api/integrations/spotify/control` | `{ "action": "play" \| "pause" \| "next" \| "previous" }` |
| `POST` | `/api/water/undo` | Desfaz o último registro de água de hoje |
| `GET` | `/api/cameras` | Lista webcams detectadas e o índice atual |

### Preferências e atalhos

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/prefs` | Retorna preferências, tema, widgets, câmera e provedor |
| `PATCH` | `/api/prefs` | Atualiza preferências parcialmente |
| `GET` | `/api/shortcuts` | Lista atalhos personalizados |
| `POST` | `/api/shortcuts` | Cria/atualiza: `{ "name": "...", "apps": [], "urls": [] }` |
| `DELETE` | `/api/shortcuts/{name}` | Remove um atalho |

### Tarefas

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/tasks` | Lista tarefas (parâmetro: `?include_completed=true`) |
| `POST` | `/api/tasks` | Cria tarefa: `{ "texto": "..." }` |
| `PATCH` | `/api/tasks/{id}/complete` | Marca tarefa como concluída |
| `DELETE` | `/api/tasks/{id}` | Remove tarefa |

### Lembretes

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/reminders` | Lista lembretes (parâmetro: `?only_pending=true`) |
| `POST` | `/api/reminders` | Cria lembrete: `{ "texto": "...", "data_hora": "YYYY-MM-DD HH:MM" }` |
| `DELETE` | `/api/reminders/{id}` | Remove lembrete |

### Modo Foco

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/focus` | Status do Pomodoro atual |
| `POST` | `/api/focus/start` | Inicia: `{ "minutes": 25, "break_minutes": 5 }` |
| `POST` | `/api/focus/stop` | Para o Pomodoro |

### Briefing

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/briefing` | Gera e retorna o resumo do dia |

### Informações

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/about` | Texto "sobre o JARVIS" |
| `POST` | `/api/about` | Salva texto "sobre": `{ "text": "..." }` |

### Memória, sistema, clima e logs

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/memory` | Lista memórias salvas |
| `POST` | `/api/memory` | Salva memória: `{ "text": "...", "category": "facts" }` |
| `GET` | `/api/system` | Retorna status do sistema e volume |
| `PATCH` | `/api/system/volume` | Ajusta volume: `{ "level": 0 }` a `{ "level": 100 }` |
| `GET` | `/api/weather?city=São Paulo` | Consulta clima da cidade informada ou padrão |
| `GET` | `/api/logs?limit=50` | Lista eventos e erros registrados |

### Integrações

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/integrations/google-calendar/status` | Verifica configuração e conexão |
| `GET` | `/api/integrations/google-calendar/authorize` | Inicia o fluxo OAuth |
| `GET` | `/api/integrations/google-calendar/callback` | Callback OAuth do Google |
| `GET` | `/api/integrations/google-calendar/events` | Lista eventos do calendário |
| `DELETE` | `/api/integrations/google-calendar` | Remove a conexão salva |
| `GET` | `/api/integrations/spotify/status` | Verifica configuração e conexão |
| `GET` | `/api/integrations/spotify/authorize` | Inicia o fluxo OAuth |
| `GET` | `/api/integrations/spotify/callback` | Callback OAuth do Spotify |
| `DELETE` | `/api/integrations/spotify` | Remove a conexão salva |

### Observações sobre a API

- **Bloqueio real (v4.1):** com uma foto de perfil ou PIN cadastrado, o backend começa
  bloqueado e só libera as rotas pessoais depois do rosto ou do PIN. Bloqueado (ou no modo
  visitante), elas respondem `403` com `{"code": "locked" | "guest"}`. A lista completa de
  rotas liberadas e bloqueadas está em `docs/ATUALIZACAO-V4.1.md`. Dá para voltar ao bloqueio
  só visual em Configurações > Bloqueio. Por padrão, o backend deve continuar sendo usado
  apenas na máquina local ou em uma rede confiável.
- O WebSocket `/ws` é usado pela interface para acompanhar estados como
  `idle`, `processing` e `speaking`, além de respostas e alertas.
- Os endpoints de lembretes usam o formato local `YYYY-MM-DD HH:MM`.
- Os dados ficam em `data/` e são criados conforme cada funcionalidade é usada.

---

## ⚙️ Configuração

### Arquivo `.env`

Crie o arquivo `.env` na pasta `jarvis_assistant/` com as variáveis abaixo:

```env
# ─── Inteligência Artificial ───────────────────────────────────────────────────
# Escolha um provedor: gemini | openai | anthropic
LLM_PROVIDER=gemini

# Preencha a chave do provedor escolhido
GEMINI_API_KEY=sua_chave_gemini_aqui
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Modelos (opcional - os padrões já são bons)
GEMINI_MODEL=gemini-2.5-flash
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-sonnet-5-5

# Limite de tokens na resposta da IA
LLM_MAX_TOKENS=400

# ─── Voz ────────────────────────────────────────────────────────────────────────
# Vozes disponíveis: pt-BR-AntonioNeural (masculina), pt-BR-FranciscaNeural (feminina)
TTS_VOICE=pt-BR-AntonioNeural
TTS_RATE=+0%

# ─── Câmera ─────────────────────────────────────────────────────────────────────
CAMERA_INDEX=0

# ─── Clima ──────────────────────────────────────────────────────────────────────
WEATHER_CITY=São Paulo

# ─── Usuário ────────────────────────────────────────────────────────────────────
USER_NAME=Patrick

# ─── Avisos durante processamento ("só um minutinho...") ────────────────────────
FILLER_FIRST_DELAY=6
FILLER_INTERVAL=20
```

### Arquivo `data/jarvis_settings.json`

Criado automaticamente na primeira execução. Contém:

```json
{
  "ai_name": "JARVIS",
  "color_theme": "blue",
  "widgets": ["todo", "focus", "shortcuts", "about"],
  "camera_index": 0,
  "shortcuts": {}
}
```

### Arquivo `data/atalhos.json`

Lista de sites e programas que o JARVIS pode abrir. Edite à vontade:

```json
{
  "youtube": "https://www.youtube.com",
  "github": "https://github.com",
  "vs code": "code",
  "bloco de notas": "notepad",
  "calculadora": "calc"
}
```

### Arquivo `data/respostas.json`

Respostas personalizadas para perguntas fixas. Criado automaticamente com os padrões. Você pode adicionar novas regras sem reiniciar o backend.

---

## 🎨 Temas de Cores

O JARVIS tem 5 temas disponíveis, configuráveis pelo painel de configurações:

| Tema | Cor Primária | Descrição |
|---|---|---|
| `blue` | `#1fc2f5` | Azul ciano (padrão) |
| `green` | `#00ff88` | Verde neon |
| `red` | `#ff4466` | Vermelho / Rosa |
| `purple` | `#b44dff` | Roxo |
| `gold` | `#ffd700` | Dourado |

---

## 🗺️ Roteiro de Funcionalidades

### ✅ Fase 1 — Base do dia a dia (Concluída)
- [x] Abrir programas e sites com lista de atalhos
- [x] Menu de perfil com foto e nome
- [x] Personalização: nome da IA, tema de cores, widgets
- [x] Atalhos personalizados (múltiplos apps + URLs)
- [x] Controle do sistema: volume, brilho, mute, lock, print
- [x] Seleção de câmera

### ✅ Fase 2 — Produtividade (Concluída)
- [x] Lista de tarefas por voz
- [x] Lembretes com data e hora persistentes
- [x] Modo Foco / Pomodoro com som ambiente
- [x] Anotações com busca, leitura e exclusão por voz
- [x] Resumo do dia (clima + tarefas + lembretes + notícias)

### ✅ Fase 3 — Integrações e experiência (Concluída parcialmente)
- [x] Spotify via OAuth: status, autorização, reprodução, pausa, avanço e retorno
- [x] Google Calendar via OAuth: autorização, status e consulta de eventos
- [x] Pesquisa atualizada com Google Search Grounding no Gemini
- [x] Pesquisa visual no navegador com leitura dos resultados
- [x] Visualizador de ondas sonoras do microfone e da fala
- [x] QR Code para acesso por celular na rede local
- [ ] Google Meet
- [ ] Controle nativo de janelas e múltiplos monitores no Windows
- [ ] Envio e leitura de e-mails

### ✅ Fase 4 — Inteligência e Memória (Concluída parcialmente)
- [x] Memória persistente adicionada por comando ou API
- [x] Histórico curto da conversa para o provedor de IA
- [x] Modos de personalidade: direto, descontraído e formal
- [ ] Contexto de tela ("o que é esse erro?")
- [ ] Memória semântica e rotina personalizada

### 🔜 Fase 5 — Polimento para publicar
- [x] Script `Iniciar-JARVIS.bat` que sobe backend e frontend
- [ ] Tela de configuração de chaves de API
- [ ] Iniciar com o Windows (bandeja do sistema)
- [x] Tratamento de erros no backend com registro persistente

---

## 🔗 Integrações OAuth

### Google Calendar

1. Crie credenciais OAuth 2.0 do tipo **Aplicativo para computador** no Google Cloud.
2. Ative a Google Calendar API.
3. Preencha `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` no `.env`.
4. Mantenha `GOOGLE_REDIRECT_URI` como:
   `http://127.0.0.1:8000/api/integrations/google-calendar/callback`.
5. Autorize a conta pelo painel de integrações do JARVIS.

### Spotify

1. Crie um aplicativo no [Spotify for Developers](https://developer.spotify.com/dashboard).
2. Cadastre como URI de redirecionamento:
   `http://127.0.0.1:8000/api/integrations/spotify/callback`.
3. Preencha `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET` no `.env`.
4. Autorize a conta pelo painel de integrações.

Os tokens são armazenados localmente em `data/spotify_token.json`. Não compartilhe
esse arquivo nem o `.env`. Para remover uma conexão, use o painel ou as rotas
`DELETE /api/integrations/google-calendar` e `DELETE /api/integrations/spotify`.

---

## 🔍 Solução de Problemas

### Palmas não funcionam

1. Ligue em **Configurações > Palmas** e use o **modo de teste** para ajustar a sensibilidade.
2. O microfone do navegador só funciona em `localhost`/`127.0.0.1` (ou HTTPS). Pelo IP da rede
   (`Iniciar-JARVIS-Rede.bat`) aparece "Palmas indisponíveis nesta conexão"; espaço e clique continuam valendo.
3. Se aparecer "Clique uma vez na tela para ativar as palmas", é a política de áudio do navegador: um clique resolve.
4. Para o JARVIS fechado, rode `Iniciar-Palmas.bat` e teste com
   `backend\venv\Scripts\python.exe scripts\clap_launcher.py --test`.

### Fiquei preso na tela de bloqueio

- Use o **PIN de reserva** (botão "USAR PIN" após uma falha).
- Sem PIN e sem câmera: a troca de foto continua liberada na tela de bloqueio (só passa a exigir
  acesso quando existe um PIN). Em último caso, apague `data/profile.jpg` com o JARVIS desligado.

### O backend não inicia

**Sintoma:** Erro ao rodar `python main.py`

**Soluções:**
1. Verifique que está na pasta correta: `jarvis_assistant\backend`
2. Instale as dependências: `pip install -r requirements.txt`
3. Verifique se o arquivo `.env` existe e tem a chave de API

---

### O microfone não funciona

**Sintoma:** Pressiono Espaço mas o JARVIS não escuta

**Soluções:**
1. Use o **Google Chrome** (outros navegadores têm suporte limitado à Web Speech API)
2. Permita acesso ao microfone quando o Chrome pedir
3. Verifique se o microfone está selecionado corretamente nas configurações do Windows

---

### O JARVIS não fala (sem voz)

**Sintoma:** Respostas aparecem na tela, mas sem áudio

**Soluções:**
1. Verifique se o volume não está no zero ou mudo
2. Verifique se o `pygame` está instalado: `pip install pygame`
3. Verifique se o `edge-tts` está instalado: `pip install edge-tts`
4. Certifique-se de estar conectado à internet (o edge-tts precisa de internet)

---

### A câmera não abre

**Sintoma:** Erro de câmera ou tela preta

**Soluções:**
1. Feche outros programas que usam a câmera (Zoom, Teams, etc.)
2. Verifique o índice da câmera nas Configurações → aba Webcam
3. Teste com `CAMERA_INDEX=1` no `.env` se tiver mais de uma câmera

---

### A IA não responde / erro de API

**Sintoma:** Mensagem de erro ao fazer perguntas que precisam de IA

**Soluções:**
1. Verifique se a chave de API está correta no `.env`
2. Verifique se `LLM_PROVIDER` está correto (`gemini`, `openai` ou `anthropic`)
3. Verifique sua conexão com a internet
4. Diga "status do sistema" para o JARVIS diagnosticar

Se o provedor escolhido não tiver uma chave configurada, o JARVIS tenta usar
automaticamente outro provedor disponível. Para validar a configuração atual,
consulte `GET /api/health`.

---

### O modo foco não para / continua com som

**Sintoma:** Após desativar, o som ambiente continua

**Solução:** Diga "desativa o modo foco" ou "para o barulho". Se persistir, reinicie o backend com `Ctrl+C` e `python main.py`.

---

### O JARVIS diz que está ocupado

**Sintoma:** Mensagem "O JARVIS já está ocupado com outra solicitação"

**Solução:** Clique no botão **Cancelar** (ícone X) na interface ou aguarde a resposta atual terminar.

---

## 📄 Licença

Projeto pessoal — uso livre para fins de aprendizado e uso pessoal.

---

*Documentação gerada em outubro de 2026 para JARVIS v4.0*
