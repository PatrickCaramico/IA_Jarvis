# JARVIS — Comandos do dia a dia

**Versão do projeto:** 6.5.20 (Windows). Substitui o antigo `Guia de comandos do dia a dia.md`.

> Montado a partir do código do projeto. Se algum comando não responder como descrito, me avise que eu ajusto o guia.
> Para a lista técnica de rotas, veja [API.md](API.md); para o `.env`, [CONFIGURACAO.md](CONFIGURACAO.md).

## 1. Abrir, parar e conferir

| Quero… | Como fazer |
| --- | --- |
| **Ligar o JARVIS** | Duplo clique em `Iniciar-JARVIS.bat` (sobe backend e frontend em segundo plano e abre o navegador). |
| **Ligar em modo desenvolvimento** | Duplo clique em `Iniciar-JARVIS-Dev.bat` (ativa `--reload` para recarregar o backend automaticamente ao editar código). |
| **Abrir o painel** | Navegador em `http://127.0.0.1:5173` (também funciona `http://localhost:5173`). |
| **Desligar o JARVIS** | Duplo clique em `Parar-JARVIS.bat` (encerra as portas 8000 e 5173). |
| **Reiniciar** | `Parar-JARVIS.bat`, esperar 3 segundos, depois `Iniciar-JARVIS.bat`. |
| **Ver o erro quando não abre** | Parar primeiro; depois duplo clique em `Diagnostico-Backend.bat`. Ele roda o backend com a janela visível e mostra o erro. |
| **Usar no celular (V5)** | Baixe o APK da [Release mais recente](https://github.com/PatrickCaramico/IA_Jarvis/releases/latest) ou inicie o JARVIS em modo de rede. No bloqueio do PC, toque em **CELULAR** e escaneie o QR; toque em **ABRIR O JARVIS** e digite o PIN principal. PC e celular precisam estar na mesma Wi-Fi. Para ficar só no PC: `set JARVIS_LOCAL=1` antes de rodar. |

| **Palmas com o JARVIS fechado** | `Iniciar-Palmas.bat` (ou `Instalar-Palmas-no-Windows.bat` para abrir junto com o Windows). Para parar: `Parar-Palmas.bat`. |
| **Ver status e logs** | `Status-JARVIS.bat` e `Ver-Logs.bat`. |
| **Fazer backup dos seus dados** | `Backup-Dados.bat` (copia a pasta `data`). |
| **Levar só os ajustes para outro PC** | Configurações > Geral > **Exportar ajustes** (gera um JSON); no outro PC, **Importar ajustes**. |
| **Pedir ajuda com um erro** | Configurações > Geral > **Copiar diagnóstico** e cole na conversa. Não leva chaves, PIN nem seus pedidos. |

**Dica:** rodar um .bat de dentro do CMD fecha a janela, porque os scripts terminam com `exit`. Para evitar, use duplo clique, ou escreva `start "" Iniciar-JARVIS.bat`.

## 2. Comandos no CMD

Abra o CMD na pasta do projeto: no Explorador de Arquivos, entre na pasta `JARVIS`, clique na barra de endereço, digite `cmd` e tecle Enter.

> **Aviso:** Os exemplos abaixo servem no próprio computador (`localhost` / `127.0.0.1`). Caso realize requisições a partir de outro aparelho conectado à rede local, é necessário incluir o cabeçalho `-H "X-Jarvis-Token: <seu_token>"` (ou o parâmetro `?token=<seu_token>`).

| O que faz | Comando |
| --- | --- |
| Ver se o backend está no ar | `curl http://127.0.0.1:8000/api/health` |
| Ver se as portas estão ocupadas | `netstat -ano \| findstr ":8000"` e `netstat -ano \| findstr ":5173"` |
| Ver a cota diária de pesquisa profunda | `curl http://127.0.0.1:8000/api/search/quota` |
| Ver os timers ativos | `curl http://127.0.0.1:8000/api/timers` |
| Ver as tarefas | `curl http://127.0.0.1:8000/api/tasks` |
| Ver os lembretes | `curl http://127.0.0.1:8000/api/reminders` |
| Ver os últimos eventos | `curl "http://127.0.0.1:8000/api/logs?limit=20"` |
| Cancelar fala e resposta em andamento | `curl -X POST http://127.0.0.1:8000/api/cancel` |
| Mandar uma pergunta ao JARVIS | `curl -X POST http://127.0.0.1:8000/api/chat -H "Content-Type: application/json" -d "{\"message\":\"que horas são\"}"` |
| Abrir a documentação da API | Navegador em `http://127.0.0.1:8000/docs` |
| Atualizar dependências do backend | `backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt` |
| Atualizar dependências do frontend | `cd frontend` e depois `npm install` |
| Abrir o projeto no VS Code | `code .` |
| Rodar os testes | `backend\venv\Scripts\python.exe -m pytest -q backend\tests scripts\tests` e `cd frontend` + `npm test` |
| Conferir o código (lint) | `cd backend` + `ruff check .` (depois de instalar o `requirements-dev.txt`) e `cd frontend` + `npm run lint` |
| Atualizar o `docs/API.md` | `backend\venv\Scripts\python.exe scripts\dev\gerar_api_md.py` |

Se `curl` não responder, o JARVIS provavelmente está desligado: use o `Iniciar-JARVIS.bat`.

## 3. Atalhos de teclado e tela

| Tecla | O que faz |
| --- | --- |
| **Espaço** (tela principal) | Liga ou desliga o microfone. Na tela de entrada, confirma a entrada. |
| **Espaço** (tela de bloqueio) | Inicia o escaneamento facial (no Modo Sentinela: "ESPAÇO = LIBERAR"). |
| **P** (tela de bloqueio) | Liga ou desliga o microfone (escuta do Sentinela e palmas). O bloqueio sempre começa com o microfone silenciado. |
| **2 palmas** | Na tela de bloqueio, inicia o escaneamento; na central, reverifica o rosto (se ligado em Configurações > Palmas). |
| **Esc** | Cancela a fala e a resposta em andamento. Se as configurações estiverem abertas, fecha as configurações. |
| **Setas esquerda e direita** | Trocam de tela quando o painel de telas está aberto. |
| **Ctrl + F5** | Recarrega o painel sem cache (bom depois de uma atualização). |

O Espaço e o P não agem enquanto você está digitando em um campo de texto.

## 4. Comandos de voz

Fale naturalmente; os exemplos abaixo são modelos, não frases exatas.

### Rotina do dia

| Exemplo | O que faz |
| --- | --- |
| "Bom dia" / "Resumo do dia" | Briefing em etapas: abertura (há algo urgente?), clima, agenda, e-mails, notícias (tecnologia, IA, política) e saúde sob demanda, um card por assunto, e uma recomendação do dia no fim. **→** ou PRÓXIMO ▸ pula o assunto; Esc ou ✕ CANCELAR interrompe. |
| Na tela de bloqueio: "Jarvis, como está o clima?" (V6.5.8) | Responde falando e abre uma mini janela: agora, hoje (máx/mín, chuva, sol) e os próximos dias. Contas, timers e outras perguntas públicas mostram a pergunta e a resposta. |
| Só o nome: "YouTube", "Netflix", "vai no YouTube", "entra no Netflix" (V6.5.14) | Abre como "abra o YouTube" (o reconhecimento às vezes corta o "abre"). Nomes mal ouvidos ("iutubi", "espotifai", "netflx") também são entendidos. |
| "Abra o YouTube" / "Abra o Google" (V6.5.8) | Abre numa janela média do navegador, no canto da tela, que dá para arrastar. |
| Resposta a "Em qual navegador?" (V6.5.11): "no Chrome", "Edge", "o padrão", "sempre no Chrome", "cancela" | Abre no navegador escolhido; com "sempre", não pergunta mais (volta a perguntar em Configurações › Mídia & Foco › NAVEGADOR DOS SITES). Também dá para tocar na lista que aparece. |
| "Modo bloqueio" / "Ativa o modo bloqueio" / "Volta pra tela de bloqueio" / "Bloqueia a central" (V6.5.7) | Leva a central para a tela de bloqueio (PC e celular). "Modo sentinela" faz o mesmo e fica ouvindo "Jarvis". "Bloquear a tela" bloqueia o Windows. |
| "Boa tarde" / "Resumo da tarde" (V6.5) | Resumo da tarde em etapas: o que falta da agenda de hoje, tarefas pendentes, clima, água, e-mails e as notícias dos seus temas. "Resumo" sozinho entre 12h e 18h também abre a tarde. |
| Botão **NOTÍCIAS** (rodapé) ou tocar em "notícias" (V6.5) | Janela de notícias: os temas do briefing em abas, busca de outro assunto e "Avisar no celular quando sair notícia nova". |
| "Boa noite" / "Fechar o dia" / "Boa noite, resumo do dia" | Fechamento do dia em etapas, no mesmo formato do "bom dia": tarefas pendentes, agenda de amanhã, clima de amanhã, água de hoje e anotações de hoje, um card por assunto, e uma dica para a noite. |
| "Resumo" / "Briefing" | Antes das 18h, o "bom dia"; a partir das 18h, o fechamento. |

### Telas por assunto (V4.3)

Uma palavra ou frase curta abre a tela do assunto no mesmo formato do "bom dia": um card por item,
abas, legenda e fileira no fim. Ela precisa ser só isso (com ou sem "Jarvis" ou "por favor").
Embaixo do orbe, a faixa **DIGA:** mostra as frases; clicar numa delas faz o mesmo que falar.

| Diga | Abre |
| --- | --- |
| "Notícias" / "Últimas notícias" / "Manchetes" | Radar com um card por tema: tecnologia, novos modelos de IA, política, economia e mundo. |
| "Notificações" / "Minhas notificações" | Um card por aplicativo. Na fala, só o nome do app (o conteúdo só se "ler o conteúdo" estiver ligado em Automação). Precisa da central de notificações ligada. |
| "E-mails" / "Meus e-mails" / "Caixa de entrada" | Triagem de e-mail (precisa de `EMAIL_IMAP_*`). |
| "Agenda" / "Minha agenda" / "Compromissos" | Compromissos e lembretes de hoje. |
| "Clima" / "Previsão do tempo" | Hoje e amanhã, um card cada. |
| "Tarefas" / "Minhas tarefas" / "Pendências" | Lista de pendências. |
| "Meus dados de saúde" / "Prontidão" | Os números de saúde na tela, e recuperação e sono falados (só porque você pediu). |
| "Comandos" / "Ajuda" / "O que posso falar" | A lista de frases com o que cada uma faz. |

Frases mais longas seguem os comandos de sempre: "adiciona tarefa comprar pão", "notícias sobre o
Palmeiras", "como está o tempo em Recife".
| "Que horas são?" / "Que dia é hoje?" | Hora e data. |
| "Como está o tempo?" / "Vai chover amanhã?" | Clima na cidade padrão (ou em outra, se você disser). |
| "Quanto está o dólar?" / "Valor do bitcoin" | Cotação em reais. |

### Tarefas, lembretes e anotações

| Exemplo | O que faz |
| --- | --- |
| "Adiciona comprar pão" | Cria tarefa. |
| "Quais são minhas tarefas?" | Lista as pendentes. |
| "Completar tarefa 1" / "Apaga a tarefa 2" | Conclui ou remove. |
| "Me lembra de ligar para o dentista amanhã às 3 da tarde" | Cria lembrete com data e hora (V5.1 entende "às 6 e meia", "às 7 da noite", "meio-dia", "sexta às 10", "dia 15 às 9", "daqui a 2 horas"). |
| "Me lembra toda terça às 19 de levar o lixo" / "Todo dia às 8 tomar o remédio" | Lembrete que repete (dias da semana ou todo dia). |
| "Quais são meus lembretes?" | Lista os pendentes. |
| "Cancela o lembrete do dentista" / "Cancela o lembrete das 15h" / "Apaga todos os lembretes" | Remove um só (pelo assunto ou pela hora) ou todos. |
| "Anote: reunião com cliente na sexta" | Salva anotação. |
| "O que eu anotei?" / "O que anotei sobre reunião?" | Lê ou busca anotações. |

### Alarmes (V5.1, como a Alexa)

| Exemplo | O que faz |
| --- | --- |
| "Jarvis, me acorda às 7" / "Alarme amanhã às 6 e meia" | Alarme único. Sem horário ("me acorda"), ele pergunta "Para que horas, senhor?". |
| "Alarme de segunda a sexta às 6" / "Alarme todo dia às 7" / "Alarme no fim de semana às 9" | Alarme que repete. |
| "Alarme às 16 para a reunião" | Alarme com nome (o nome não aparece com a central bloqueada). |
| "Quais são meus alarmes?" | Lista os próximos. |
| "Cancela o alarme das 7" / "Apaga todos os alarmes" | Remove um ou todos. |
| Tocando: "Jarvis, parar" / "Já acordei" | Desliga (vale até com a central bloqueada). Ou o botão PARAR (ENTER). |
| Tocando: "Soneca" / "Mais 5 minutos" | Adia 9 minutos (ou o tempo dito). Ou o botão SONECA (tecla S). |

O alarme toca bipes no PC e, a cada 25 s, fala a hora ("Senhor, são 7 horas."). Sem resposta, desliga sozinho depois de 10 minutos. Se o PC estava desligado na hora, ele não toca atrasado (mais de 30 min).

### Notícias do briefing (V6.2)

O "bom dia" lê os temas de **Configurações › Geral › NOTÍCIAS DO BRIEFING** (Google Notícias, últimos 2 dias). Padrão: Tecnologia, Novos modelos de IA, Política e **Marvel com as 3 principais**. Cada tema escolhe de 1 a 5 manchetes; ideias prontas com um toque (DC, Palmeiras, Games, Fórmula 1, Bitcoin, Séries e filmes, Espaço, Star Wars…).

### Lista de compras (V6.0)

| Exemplo | O que faz |
| --- | --- |
| "Jarvis, coloca leite, pão e ovos na lista" / "adiciona café na lista de compras" | Põe na lista (vários de uma vez). |
| "Jarvis, comprei o leite" | Marca como comprado (risca na lista). |
| "Tira o pão da lista" | Remove. |
| "O que tem na lista de compras?" | Lê o que falta comprar. |
| "Limpa a lista de compras" / "limpa a lista inteira" | Apaga o que já foi comprado (ou tudo). |

A lista aparece no painel LISTA DE COMPRAS (no celular, logo abaixo da conversa), com caixinhas para marcar no mercado.

### Rotinas em 1 comando (V6.0)

| Exemplo | O que faz |
| --- | --- |
| "Jarvis, vou dormir" / "modo dormir" | Pausa a música, para o foco, baixa o volume e fala o despertador, o primeiro compromisso e o clima de amanhã. |
| "Jarvis, estou saindo" / "modo saindo de casa" | Fala o clima agora e a lista de compras, pausa a música e bloqueia o computador. |
| "Modo trabalho" / "protocolo gravação" | Os protocolos de antes também respondem por "modo …". |

Monte as suas em Configurações › Automação › Protocolos (passos novos: pausar a música, bloquear o computador, resumo de amanhã, clima agora, ler a lista de compras).

### No celular (V6.0)

| Onde | O que faz |
| --- | --- |
| Toque longo no ícone do JARVIS | Atalhos: Falar com o JARVIS, Bom dia, Lista de compras. |
| Cortina do Android (lápis › arraste o "JARVIS") | Botão que abre o JARVIS já ouvindo, mesmo com o app fechado. |
| Compartilhar › JARVIS (em qualquer app) | Resumir, Anotar, Lembrar amanhã ou pôr na lista de compras. |
| Bloqueio do app › ENTRAR COM A DIGITAL | Depois de entrar uma vez pelo PIN, o app oferece ativar a digital. |
| Fora de casa | Com o Tailscale no PC e no celular, o app entra pelo 4G (guia em docs/ACESSO-FORA-DE-CASA.md). |

### Timers e foco

| Exemplo | O que faz |
| --- | --- |
| "Cria um timer de 10 minutos" / "Me avise em 30 segundos" | Timer simples. |
| "Quais timers estão ativos?" / "Cancele os timers" | Lista ou cancela. |
| "Ativa o modo foco" | Pomodoro padrão (25 min de foco + 5 de pausa). |
| "Inicia o modo foco por 45 minutos" | Foco com tempo personalizado. |
| "Status do modo foco" / "Desativa o modo foco" | Tempo restante, ou para o Pomodoro. |

### Abrir e pesquisar

Por padrão, a pesquisa de informações gerais e perguntas de fatos recentes (como *"quem ganhou o jogo ontem?"*) são direcionadas diretamente ao navegador, economizando a cota de IA.

| Exemplo | O que faz |
| --- | --- |
| "Abre o YouTube" / "Abre o Gmail" | Abre o site cadastrado; sites e apelidos são gerenciados em Configurações > Meus Sites. |
| "Abre <nome do site>" / "Abre <apelido>" | Abre o site correspondente em Configurações > Meus Sites. |
| "Meus sites" / "Quais sites você abre?" | Informa quantos sites estão cadastrados e diz os primeiros nomes. |
| "Abre o VS Code" / "Abre a calculadora" | Abre o programa local (atalhos de programas continuam em `data/atalhos.json`). |
| "Pesquise Python tutorial" | Busca no Google via navegador (padrão). |
| "Quem ganhou o jogo ontem?" | Pergunta factual — enviada diretamente para o navegador por padrão. |
| "Procure música lofi no YouTube" | Busca no YouTube pelo navegador. |
| "Quanto é 20% de 500?" | Calculadora por voz. |
| "Pesquisa profunda sobre fusão nuclear" / "Pesquise a fundo o mercado de IA" | Dispara pesquisa profunda com IA (analisa a web e responde estruturado). |
| "Sim" / "Pode liberar" | Confirmação vocal quando o JARVIS pergunta se deseja aprofundar a busca com IA. |

> **Aprofundar com IA e Cota:**
> - Quando uma busca simples é feita, você também pode clicar no botão **"Aprofundar com IA"** exibido no painel para iniciar a pesquisa detalhada.
> - A pesquisa profunda tem limite diário de cota (verificável via `/api/search/quota`), que reseta diariamente à meia-noite. Falhas na API não descontam o seu limite diário.

### Computador

| Exemplo | O que faz |
| --- | --- |
| "Aumenta o volume" / "Diminui o volume" | Muda o volume. |
| "Coloca no mudo" / "Tira o mudo" | Silencia ou volta o som. |
| "Aumenta o brilho" / "Diminui o brilho" | Muda o brilho (depende do monitor aceitar). |
| "Bloqueia a tela" | Bloqueia o Windows. |
| "Tira um print" | Captura a tela. |
| "Modo cinema" | Volume em 45% e brilho em 35%. |
| "Modo trabalho" | Volume em 30% e brilho em 85%. |

Os modos cinema e trabalho não têm comando para voltar ao que estava antes; ajuste volume e brilho depois, na mão ou por voz.

### Navegador

Citando "aba" junto com navegador, Chrome, Edge ou Firefox:

| Exemplo | O que faz |
| --- | --- |
| "Próxima aba do navegador" | Vai para a próxima aba. |
| "Aba anterior" | Volta uma aba. |
| "Fechar aba" / "Nova aba" | Fecha a atual ou abre uma nova. |
| "Reabrir aba" | Reabre a última fechada. |

### Spotify

Precisa da conta conectada no painel. Sempre diga "Spotify" na frase.

| Exemplo | O que faz |
| --- | --- |
| "Abre o Spotify" | Abre o aplicativo no computador. |
| "Tocar \[música ou artista\] no Spotify" | Procura e toca. |
| "Tocar playlist \[nome\] no Spotify" | Procura e toca a playlist. |
| "Pausar o Spotify" / "Próxima do Spotify" / "Voltar no Spotify" | Controles básicos. |
| "Qual música está tocando no Spotify?" | Diz a faixa atual. |

### Modo Torcedor (Palmeiras / Glassmorphism)

Mostra o Palmeiras e o jogo atual/próximo, com escudos, notícias e grito de torcida. Depois de uma ativação em dia de jogo, o modo sai sozinho no dia seguinte e avisa qual é a próxima partida.

| Exemplo | O que faz |
| --- | --- |
| "Ativar modo torcedor" / "Ligar modo torcedor" | Ativa o tema Glassmorphism do Palmeiras, notícias e placar. |
| "Desativar modo torcedor" / "Modo normal" | Volta imediatamente ao tema padrão e restaura o layout anterior. |
| "Como está o jogo do Palmeiras?" | Consulta o placar, o estado da partida ou a contagem regressiva do próximo jogo. Jogos antigos não permanecem como ao vivo depois da janela de encerramento. |
| "Avante Palestra!" | Dispara a saudação da torcida alviverde. |

### Atualizações

**V5.1:** na tela de bloqueio, o botão **⟳ ATUALIZAR** baixa a versão nova do GitHub, avisa por voz ("Senhor, estou atualizando os meus sistemas") e reinicia sozinho; a central volta já na versão nova. Em **Configurações > Manutenção**, use **Verificar atualizações** para consultar a release mais recente. A checagem automática é diária e em segundo plano; o PC não baixa nem instala atualizações sozinho. No Android (5.1.1+), o app se atualiza sozinho quando o PC tem um APK mais novo: na primeira vez o Android pede para permitir instalar apps para o JARVIS e confirma a troca; no Android 12 ou mais novo, as próximas entram sem perguntar. Escanear o QR com o app instalado abre o app em vez de baixar de novo.

### Lembretes de Água e Hidratação

Monitore sua meta diária de hidratação (padrão 2000 ml). O lembrete vem a cada 2 horas por padrão, contando do último copo ou do último aviso, só entre 8h e 22h (muda em Configurações > Hidratação).

| Exemplo | O que faz |
| --- | --- |
| "Bebi 250ml de água" / "Tomei um copo de água" | Registra o consumo e mostra seu progresso atual. |
| "Bebi uma garrafinha de água" | Adiciona 500 ml ao seu total de hoje. |
| "Índice de água" / "Ver água" / "Quanto de água já bebi hoje?" | Informa o volume total consumido e a porcentagem da meta (abre o painel de água, que fecha sozinho em ~6 s se não for fixado). |
| "Mudar meta de água para 2500ml" | Atualiza sua meta diária personalizada. |

### Bloqueio, Modo Sentinela e visitante

A central fica bloqueada até o rosto ser reconhecido (ou o PIN digitado). Com o **Modo Sentinela**
ligado (Configurações > Bloqueio, ou o botão **MODO SENTINELA** no menu ⚡ CONTROLES), o JARVIS fica
ouvindo a palavra de ativação mesmo bloqueado.

| Exemplo | O que faz |
| --- | --- |
| "Abrir central" / "Liberar" / "Desbloquear" / "Entrar" | Com o microfone ligado (tecla **P**), vai direto para o escaneamento do rosto, com ou sem "Jarvis" na frente. |
| "Jarvis" / "Ei, Jarvis" / "Tá acordado?" | Acorda o Sentinela (o nome da IA também vale, ex.: "Ares"). Depois diga o pedido em até 8 s. |
| "Jarvis, que horas são?" / "Jarvis, como está o tempo?" | Pedidos públicos: respondidos sem liberar a central (hora, data, clima, contas, timers, foco, cumprimentos). |
| "Jarvis, o que tenho hoje?" | Responde só números (quantas tarefas e lembretes), sem detalhes pessoais. |
| "Jarvis, minhas tarefas" (ou outro pedido pessoal) | Pede liberação: abre a câmera e, se reconhecer você, entra e executa o pedido. |
| "Jarvis, bloquear" / "Bloquear a central" / "Modo sentinela" | Bloqueia a central do JARVIS. |
| "Bloqueia a tela" | Bloqueia o **Windows** (diferente de bloquear a central). |

- **PIN:** se o rosto falhar, use o teclado na tela. 5 erros travam por 5 minutos.
- **Esqueci o PIN (V5.1):** no teclado do PIN, "Esqueci o PIN" lê o seu rosto e, se for você, pede o PIN novo duas vezes. Também em Configurações > Bloqueio > ESQUECI O PIN. Sem câmera, rode o `Redefinir-PIN.bat` (apaga o PIN do dono, com cópia em `data\lock_pin.antigo.json`).
- **Modo visitante** (se ligado em Configurações > Bloqueio): relógio, clima, música e perguntas públicas, sem acesso a nada pessoal. Sair exige rosto ou PIN.
- **Bloqueio por ausência:** depois do tempo escolhido sem uso, avisa "Bloqueando em 30 s" e bloqueia (mexa o mouse para cancelar).

### Automação (4.2)

Ajustes em Configurações > **Automação**.

| Exemplo | O que faz |
| --- | --- |
| "Protocolo trabalho" / "Ativar protocolo gravação" | Roda os passos do protocolo (abrir programas, foco, volume, playlist, modo silencioso). Os exemplos que já vêm prontos: trabalho, gravação e descanso. |
| "Quais são os meus protocolos?" | Lista os protocolos. |
| "O que é esse erro na tela?" / "Leia minha tela" / "Explica essa janela" | Captura a tela e pergunta à IA. Nada é salvo; só com a central liberada. |
| "Acha o vídeo que gravei ontem" / "Cadê a planilha de gastos" / "Encontra o arquivo relatório" | Procura nas suas pastas pessoais e lista até 5. |
| "Abre o primeiro" / "Mostra o segundo na pasta" | Abre ou mostra um dos arquivos encontrados (vale por 10 minutos). |
| "Organiza a pasta Downloads" | Mostra o plano (separar por tipo) e só move depois do "sim". Nada é apagado nem sobrescrito. |
| "Desfazer organização" | Devolve os arquivos para onde estavam. |
| "Quais são minhas notificações?" / "Limpa as notificações" | Central de notificações do Windows (experimental; precisa ser ligada e instalada). |
| "Sim" / "Não" / "Não sugira mais isso" | Responde a uma sugestão pela rotina ("o senhor costuma ativar o protocolo trabalho por volta das 9h. Quer que eu ative?"). |

Avisos automáticos (gatilhos): chuva amanhã (à noite), jogo começando (com o Modo Torcedor), processador alto por alguns minutos e, se ligado, água atrasada. Entre 22h e 7h eles só aparecem na tela.

### Conversa e diagnóstico

| Exemplo | O que faz |
| --- | --- |
| "Quem é você?" / "O que você sabe fazer?" | Apresenta o JARVIS e as funções. |
| "Status do sistema" | Diagnóstico de câmera, IA e perfil. |
| "Buscar Bluetooth" | Procura smartwatch ou dispositivos BLE por perto. |

### V4.5: memória, arquivos, WhatsApp e finanças

| Diga… | O que acontece |
| --- | --- |
| "Lembre que eu treino às 18h" | Guarda na memória de longo prazo; ele usa isso nas próximas conversas. |
| "O que você lembra de mim?" / "Esqueça o treino" | Lista ou apaga memórias. |
| "Acha a planilha de gastos" → "manda o primeiro para a lixeira" | Pergunta antes e, no "sim", manda para a **Lixeira do Windows** (dá para restaurar). |
| "Move o segundo para documentos" | Pergunta antes; só mexe nas suas pastas pessoais. |
| "Cria uma pasta Projetos na área de trabalho" | Pergunta antes e cria. |
| "Salva o contato Ana 11 99999-8888" | Guarda o contato só neste PC. |
| "Manda uma mensagem no WhatsApp para a Ana dizendo que eu chego às 8" | Repete a mensagem e pergunta. No "sim", abre o WhatsApp com a conversa e o texto prontos: **quem toca em enviar é você**. |
| "Gastei 45 reais no mercado" / "Recebi 3000 de salário" | Anota (sem banco). |
| "Quanto eu gastei esse mês?" / "hoje" / "essa semana" | Total e as categorias que mais pesaram. Também na tela **Finanças**. |
| "Apaga o último gasto" | Desfaz o último lançamento. |

Ao entrar na central: na primeira vez do dia o JARVIS já começa o **briefing**. Nas próximas, pergunta se repete ou pula (botões, Enter/Esc ou "repetir"/"pular").

## 5. Onde mudar as coisas

| O que quero mudar | Arquivo |
| --- | --- |
| Chaves de IA, voz, cidade do clima, câmera | `.env` (na pasta `JARVIS`) |
| Programas e sites que o JARVIS abre | `data/atalhos.json` |
| Respostas rápidas (perguntas simples) | `data/respostas.json` |
| Nome da IA, tema de cores, widgets, personalidade | Painel de configurações, ou `data/jarvis_settings.json` |
| Palmas, bloqueio, PIN, Modo Sentinela, visitante, hidratação | Painel de configurações (abas Palmas, Bloqueio e Hidratação) |
| Gatilhos, protocolos, sugestões pela rotina, leitura de tela, notificações | Painel de configurações (aba Automação) |
| Sua foto e nome do perfil | Menu de perfil no painel |

Depois de mexer no `.env`, feche e ligue o JARVIS de novo para valer.

## 6. Se algo der errado

1. **O painel não abre:** rode o `Parar-JARVIS.bat`, depois o `Iniciar-JARVIS.bat`, e abra `http://127.0.0.1:5173` com Ctrl+F5.
2. **O painel abre, mas o JARVIS não responde:** confira `curl http://127.0.0.1:8000/api/health`. Sem resposta, use o `Diagnostico-Backend.bat` e leia a última mensagem de erro.
3. **"Porta ocupada":** algo ainda está rodando; use o `Parar-JARVIS.bat` e tente de novo.
4. **A IA não responde ou dá erro de cota (429):** confira a chave e o limite do provedor no `.env`.
5. **Microfone ou câmera não funcionam:** permita o acesso no navegador e confira o `CAMERA_INDEX` no `.env`.
6. **"Acesso externo não permitido (403)":** o modo rede está desligado porque o JARVIS foi iniciado pelo `Iniciar-JARVIS.bat`. Feche e inicie pelo `Iniciar-JARVIS-Rede.bat`.
7. **"Central bloqueada" (403 com `code: locked`):** a central está bloqueada; libere pelo rosto ou PIN. Veja quais rotas funcionam bloqueadas em [API.md](API.md).
8. **"Não autorizado (401)":** token ausente ou incorreto. Escaneie novamente o QR Code com o celular ou passe o token gerado pelo painel no header `X-Jarvis-Token`.
