# JARVIS — Comandos do dia a dia

**Versão do projeto:** 9.3.0 (Windows). Substitui o antigo `Guia de comandos do dia a dia.md`.

> Montado a partir do código do projeto. Se algum comando não responder como descrito, me avise que eu ajusto o guia.
> Para a lista técnica de rotas, veja [API.md](API.md); para o `.env`, [CONFIGURACAO.md](CONFIGURACAO.md).

## 1. Abrir, parar e conferir

| Quero… | Como fazer |
| --- | --- |
| **Ligar o JARVIS** | Duplo clique em `Iniciar-JARVIS.bat` (sobe backend e frontend em segundo plano e abre o navegador). |
| **Ligar em modo desenvolvimento** | Duplo clique em `Iniciar-JARVIS-Dev.bat` (ativa `--reload` para recarregar o backend automaticamente ao editar código). |
| **Abrir o painel** | Navegador em `http://127.0.0.1:5173` (também funciona `http://localhost:5173`). |
| **Sempre ligado (V8.12.3, padrão)** | O JARVIS liga sozinho em segundo plano ao entrar no Windows (sem janela e sem abrir aba), religa se cair (guardião) e, **na tomada**, não deixa o PC dormir por inatividade (a tela ainda apaga). Configurações › **Inicialização** › "Sempre ligado" e "Não deixar o PC dormir na tomada", ou diga "liga o JARVIS junto com o Windows" / "não liga mais com o Windows". Também dá pelo `Instalar-JARVIS-no-Windows.bat` / `Remover-JARVIS-do-Windows.bat`. Desligado, ele não volta a ligar sozinho. |
| **Ficar sempre ligado (V8.11)** | O **guardião** (liga junto com o JARVIS) confere a cada 10 s: se o JARVIS cair sozinho, liga de novo em ~45 s (no máximo 4 vezes por hora). Não interfere em atualizações nem no `Parar-JARVIS.bat`. Registro em `logs\guardiao.log`. |
| **Atualizar ao abrir (V8.11)** | Ao abrir a central no PC (pelo site ou aqui), se tiver versão nova o JARVIS atualiza na hora, com a barra de progresso, e já abre na versão nova. Desligar: Configurações › Inicialização › "Atualizar ao abrir a central". Se a atualização falhar, ele não tenta de novo pelos próximos 15 min. |
| **Microfone só no botão (V8.11, padrão)** | Nada fica ouvindo sozinho: o microfone abre no 🎙 (ou na tecla do app do Windows) e fecha ao terminar a frase; no bloqueio, o botão do microfone vale para um pedido (desliga sozinho em 20 s). A escuta contínua ("Jarvis, …"), as palmas, o ouvido offline e o Ouvinte de Palmas **fecham o microfone**. Motivo: com o microfone aberto o tempo todo, o Windows trata o PC como "em chamada" e a música no fone Bluetooth fica abafada/distorcida. Para voltar a ouvir sempre: Configurações › Bloqueio › Modo Sentinela › desligue "Microfone só quando eu apertar o botão", ou diga "pode ficar me ouvindo o tempo todo" (e "microfone só no botão" para voltar). |
| **Desligar o JARVIS** | Duplo clique em `Parar-JARVIS.bat` (encerra as portas 8000 e 5173 e o guardião, para ele não religar). |
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
| Na tela de bloqueio: "Jarvis, abre o clima" / "abre o mercado" / "mostra a água" / "abre as manchetes" / "mostra os sistemas" (V9.5.1) | Abre a janela grande do cartão na tela, saindo do próprio cartão. No clima, também fala a previsão de agora. Se ele ainda estiver falando a resposta anterior, corta e atende. "Abre o Spotify" continua pedindo o rosto (é abrir o programa no PC). |
| Tela "Reconectando" (JARVIS do PC fora do ar): **⟳ ATUALIZAR E LIGAR** (V9.5.3) | O PC baixa a versão mais nova e liga. Precisa do botão LIGAR instalado (Instalar-Botao-Ligar.bat); o atalho se ajusta sozinho na primeira vez que o JARVIS ligar na 9.5.3. Se o JARVIS cair ao ligar, o PC confere o motivo, instala o que faltar e, havendo versão corrigida, baixa e religa sozinho (registro em `logs\\ligar.log` e `logs\\backend-erro.log`). |
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

**V9.4.2 — atualização automática com aviso:** a cada 40 minutos o PC confere se há versão nova. Achando, avisa na central, no celular e por voz e mostra **⬆ VERSÃO X DISPONÍVEL** com a contagem de 2 minutos, **ATUALIZAR AGORA** e **ADIAR 1 H**. Depois disso, atualiza sozinho assim que o JARVIS não estiver falando e não houver nada em tela cheia (vídeo, jogo). A central mostra a tela de atualização e volta na versão nova. Desligar: Configurações › Atualizações (Modo Desk). O **⟳ ATUALIZAR** também ficou mais robusto: arquivos regenerados no PC (package-lock) voltam ao original, outras mudanças locais ficam guardadas num `git stash` e uma pasta num ramo apagado no GitHub volta para o `main`. Se houver commits próprios no PC, ele não atualiza e diz o motivo.

### Lembretes de Água e Hidratação

Monitore sua meta diária de hidratação (padrão 2000 ml). O lembrete vem a cada 2 horas por padrão, contando do último copo ou do último aviso, só entre 8h e 22h (muda em Configurações > Hidratação).

| Exemplo | O que faz |
| --- | --- |
| "Bebi 250ml de água" / "Tomei um copo de água" | Registra o consumo e mostra seu progresso atual. |
| "Bebi uma garrafinha de água" | Adiciona 500 ml ao seu total de hoje. |
| "Índice de água" / "Ver água" / "Quanto de água já bebi hoje?" | Informa o volume total consumido e a porcentagem da meta (abre o painel de água, que fecha sozinho em ~6 s se não for fixado). |
| "Mudar meta de água para 2500ml" | Atualiza sua meta diária personalizada. |

### Bloqueio, Modo Sentinela e visitante

**V7.14:** o bloqueio padrão é o **clássico**, com a verificação nova do rosto (círculo com a máscara de pontos e IDENTIDADE CONFIRMADA). **◐ ESTILO** troca para o estilo **ORBE** (V7.12, igual ao vídeo: orbe de linhas, cartões numa faixa e botões em ⚙ GERENCIAR HUB).

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
- **Bloqueio por ausência:** depois do tempo escolhido sem uso (1, 2, 5, 10, 15 ou 30 minutos), avisa "Bloqueando em 10 s" e bloqueia (mexa o mouse para cancelar). O botão BLOQUEAR e o "Jarvis, bloquear" trocam a tela na hora (V8.13.1).

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
| (sozinho, V6.7.3) | Quando você fala de si nas conversas ("eu treino de manhã", "minha esposa Ana…"), ele guarda até 3 fatos duradouros por frase, sem repetir. Não guarda coisas passageiras nem senhas, documentos, banco ou detalhes de saúde. As memórias também valem fora de casa (nuvem). |
| "Pare de aprender sobre mim" / "pode voltar a aprender sobre mim" | Desliga ou liga o aprendizado sozinho (o que já sabe continua guardado). |
| "Acha a planilha de gastos" → "manda o primeiro para a lixeira" | Pergunta antes e, no "sim", manda para a **Lixeira do Windows** (dá para restaurar). |
| "Move o segundo para documentos" | Pergunta antes; só mexe nas suas pastas pessoais. |
| "Cria uma pasta Projetos na área de trabalho" | Pergunta antes e cria. |
| "Salva o contato Ana 11 99999-8888" | Guarda o contato só neste PC. |
| "Manda uma mensagem no WhatsApp para a Ana dizendo que eu chego às 8" | Repete a mensagem e pergunta. No "sim", abre o WhatsApp com a conversa e o texto prontos: **quem toca em enviar é você**. |
| "Gastei 45 reais no mercado" / "Recebi 3000 de salário" | Anota (sem banco). |
| "Quanto eu gastei esse mês?" / "hoje" / "essa semana" | Total e as categorias que mais pesaram. Também na tela **Finanças**. |
| "Apaga o último gasto" | Desfaz o último lançamento. |

### Câmera do aparelho (V6.8.2)

| Diga | O que acontece |
|---|---|
| "Abre a câmera" | Abre a câmera **do aparelho em que você está** (celular ou PC). Ao vivo só ali: nada sai do aparelho. Botões: 📸 FOTO (salva no aparelho), ↺ TROCAR (frontal/traseira), ⏱ 3 s. |
| "Tira uma foto" / "tira uma selfie" | Abre a câmera, conta 3, 2, 1 e salva a foto. |
| "O que é isso?" (com a câmera aberta) ou o botão 🔍 O QUE É ISSO? | Manda **só aquela foto** à IA, que responde por voz (planta, produto, prato, rótulo, lugar). A foto não é guardada. Funciona em casa e fora (nuvem). Não identifica pessoas pelo rosto. |

| "Abre a câmera e analisa esse item" / "analisa isso" (V7) | Abre a câmera, espera a imagem firmar e faz o **diagnóstico**: uma janela com o nome do item, categoria, confiança, resumo, detalhes (marca, modelo, nome científico, preço médio…), ⚠ alertas e 💡 dicas. A fala continua curta. |

"O que você está vendo?" (sem abrir a câmera) continua usando a webcam do PC.

### Segurança: aparelhos (V7.6)

| Situação | O que acontece |
|---|---|
| Aparelho novo escaneia o QR code | Fica em **AGUARDANDO APROVAÇÃO**; o PC mostra **PERMITIR / RECUSAR** e avisa por voz. Só a tela do PC aprova; o pedido vale 2 minutos. |
| Aparelho que já usava o JARVIS (até 14 dias depois da atualização) | Ganha a própria chave sozinho, sem escanear de novo. |
| Configurações > Segurança | Lista dos aparelhos com **REMOVER**, **DESCONECTAR TODOS E TROCAR O QR CODE**, **exigir aprovação agora** e o que aconteceu nas últimas 24 h. |
| 5 tentativas erradas em 10 min | Aquele aparelho fica bloqueado por 15 min (dobra a cada vez), com aviso por voz, notificação no celular e registro no 🩺 Diagnóstico. |

### Conversa com os agentes (V7.9)

| Fale / digite | Agente |
|---|---|
| `@mercado monta a lista do churrasco` · "agente mercado, o que falta comprar?" | 🛒 Mercado: lista de compras, receitas, quantidades |
| `@financas gastei 54,90 no mercado` · "pergunta pro agente de finanças quanto gastei no mês" | 💰 Finanças: gastos, entradas, resumo do mês |
| `@secretario marca dentista sexta às 10` · "o que tenho amanhã?" | 📅 Secretário: agenda, lembretes, tarefas |
| `@professor me explica frações` · "fala com o professor: me faz 3 perguntas sobre…" | 🧠 Professor: explicações, Holograma, perguntas tipo prova |
| `@rotas quero ir para o trabalho` | 🧭 Rotas |
| `@pesquisa procura receita de pão no YouTube` | 🔎 Pesquisa |

- Digitar `@` no campo de conversa mostra a lista dos agentes.
- 🤖 AGENTES abre a Central com **uma aba por agente**; cada um lembra as últimas 30 mensagens e tem o botão **LIMPAR**.
- Ações maiores esperam o **✓ CONFIRMAR**.

### Controle financeiro: 💰 @financas (V7.10)

| Fale / digite | O que acontece |
|---|---|
| "@financas tenho uma dívida de R$ 5.000 no banco, parcela de 450 em 12x, já paguei 3, vence dia 10, juros de 2,5% ao mês" | Cadastra a dívida (se faltar algo, ele pergunta). |
| "paguei a parcela do carro" · "paguei 500 a mais no empréstimo" · "quitei o cartão" | Abate o saldo, conta a parcela (quitar pede ✓ CONFIRMAR). |
| "minha conta de luz é 180 e vence dia 15" · "paguei a luz" | Conta fixa e "paga" no mês. |
| "meu cartão Nubank fecha dia 3 e vence dia 10" · "gastei 300 no Nubank em 3x" · "quanto está minha fatura?" | Cartão, compras parceladas e faturas. |
| "quero gastar no máximo 800 de mercado" · "quero juntar 6 mil de reserva" | Orçamento por categoria e metas. |
| "monta um plano para quitar minhas dívidas" · "e se eu pagar 300 a mais?" | Compara os dois jeitos de quitar e recomenda. |
| "quanto eu devo?" · "o que vence essa semana?" | Resumo e vencimentos. |

Painel completo na aba 💰 da Central de Agentes. Avisos 3 dias antes e no dia do vencimento. Fora de casa: resumo e anotações.

### Foto da galeria (V7.8)

| Como | O que acontece |
|---|---|
| 🖼 GALERIA (câmera), 📎 (campo de conversa) ou arrastar a imagem na central do PC | Abre **FOTO ENVIADA**. A foto é reduzida e perde a localização antes de sair do aparelho. |
| 🔍 ANALISAR | Diagnóstico: o que é, detalhes, dicas e alertas. |
| 📄 LER E AGIR | Sugere lista de compras, lembrete, contato ou tarefas. **Só faz depois do ✓ CONFIRMAR.** |
| 🌐 PESQUISAR (ou perguntar "quanto custa?") | Preço, onde comprar e avaliações, com as fontes. |
| ✦ HOLOGRAMA (ou "me explica…") | Apresentação animada sobre o que está na foto, com a foto no fundo. |

A foto não é guardada em lugar nenhum. Funciona também fora de casa (nuvem).

### Conexão criptografada / https (V7.7)

1. **No PC:** Configurações › Segurança › **LIGAR HTTPS**. O JARVIS reinicia.
2. **No celular:**
   - abra `http://IP-DO-PC:8000/api/mobile/certificado`;
   - baixe o certificado e instale em Configurações › Segurança › Criptografia e credenciais › Instalar certificado › **Certificado CA**. É uma vez só.
3. **Escaneie o QR code de novo** (Configurações › Acesso Mobile). O endereço agora é `https://IP-DO-PC:5443`.
4. **App Android:** gere o APK de novo (`Gerar-App-Android.bat`) e instale.

Este PC continua em `http://127.0.0.1`. Para voltar ao normal: Configurações › Segurança › DESLIGAR HTTPS.

### Diagnóstico (V7.4)

| Fale / toque | O que acontece |
|---|---|
| 🩺 DIAGNÓSTICO (tela de bloqueio, ao lado do Olho de Deus, CONTROLES, perfil) ou "Jarvis, roda um diagnóstico" | Testa IA, voz, internet, nuvem, disco, dados, erros recentes, conexão com o PC, versão, microfone, câmera e fluidez. Cada item mostra o que fazer. "COPIAR RELATÓRIO" copia o resultado para me mandar. |

### Notas da versão (V7.3)

| Fale / toque | O que acontece |
|---|---|
| 📝 NOTAS (tela de bloqueio, CONTROLES, perfil) ou "Jarvis, o que mudou?" / "novidades" / "notas da versão" | Abre a lista de todas as versões com data e detalhes, com busca. A versão em uso aparece como **INSTALADA**. |
| Depois de atualizar | As notas abrem sozinhas uma vez na versão nova. |

### Otimizar, Branding Book e saudação (V7.2)

| Fale / toque | O que acontece |
|---|---|
| ⚡ OTIMIZAR (perfil, CONTROLES, tela de bloqueio) ou "Jarvis, otimiza o sistema" | Mede a resposta e a fluidez, limpa caches e sobras de áudio, mostra uma nota e liga o **Modo leve** se o aparelho estiver pesado. O Modo leve vale por aparelho e pode ser ligado/desligado ali. |
| 📘 BRANDING (ao lado do Olho de Deus, CONTROLES, perfil, tela de bloqueio) ou "abre o branding book" | Abre o Branding Book ilustrado dentro do JARVIS. |
| Configurações > Bloqueio > Saudação ao desbloquear | **Às vezes** (padrão: 1ª do dia ou depois de 3 h), **Sempre** ou **Nunca**. |

### HOLOGRAMA: pesquisa vira tela viva (V7.1)

| Fale | O que acontece |
|---|---|
| "Me explica como funciona um buraco negro" / "como funcionam as vacinas" / "pesquisa sobre o Egito" / "me ensina…" | Abre o **holograma**: 4 a 6 cenas animadas (ícone, título, legenda palavra a palavra, tópicos e um número marcante que sobe na tela) **narradas pela voz do JARVIS**. Cada cena avança quando ele termina de falar. No fim, um resumo com as cenas para rever. |
| Holograma da apresentação (V8.14) | **Pesquisa na internet** antes de montar (Google, pelo Gemini) e mostra **FONTES DA PESQUISA** com link no fim (sem Gemini, avisa "pode estar desatualizado"). **Abre mais rápido**: a 1ª cena começa enquanto as outras chegam. **Controles**: ← → trocam de cena, espaço pausa, um toque na barra do topo pula para a cena, **1x / 1,25x / 1,5x** muda a velocidade da narração, e no fim **📋 COPIAR** e **⬇ BAIXAR** (.txt com as fontes). |
| "Receita de bolo de cenoura" / "como fazer um brigadeiro" | Abre a **receita viva**: ingredientes para marcar (os que faltam vão para a lista de compras com um toque), passo a passo grande e o **modo cozinha**. A tela não apaga enquanto está aberta. |
| "Próximo passo" / "passo anterior" / "repete" | Com o holograma aberto: anda, volta ou repete (cena ou passo). |
| "Pausa" / "continua" / "fecha" | Pausa a narração, continua ou fecha. |
| ⏱ INICIAR TIMER (no passo) | O passo que tem tempo de forno/descanso ganha o botão do timer. |

Pedidos com YouTube, Google, Maps, música ou notícias continuam no caminho de sempre. Funciona em casa e fora (nuvem). A foto de fundo vem da Wikipédia, quando existe.

### Olho de Deus: trânsito ao vivo (V7)

| Fale / toque | O que acontece |
|---|---|
| "Mostra o trânsito" / "como está o trânsito?" / botão ◉ OLHO DE DEUS | Abre o mapa **ao vivo do Waze** centrado na cidade do clima: lentidão por cor e alertas dos motoristas (acidente, obra, polícia). |
| Busca no topo | Cidade, endereço, bairro ou CEP: o mapa vai até lá. |
| 🏠 MINHA CIDADE · 📍 ONDE ESTOU · ＋/－ | Volta para a sua cidade, centraliza onde você está (pede permissão de localização) e aproxima/afasta. |
| Lugares salvos | Os lugares do agente de rotas viram atalhos no painel. |
| 🧭 IR ATÉ AQUI NO WAZE | Abre a navegação no app do Waze. |

### Modo Desk: Habilidades com botões (V8.11)

No Modo Desk (e no app do Windows), as habilidades novas também funcionam com botões, sem precisar falar. Só no próprio PC do JARVIS.

| Seção | O que dá para fazer |
|---|---|
| 🪟 **Janelas** | Ver o que está aberto em cada monitor; ▦ GRADE e ◫ LADO A LADO; mandar uma janela para o outro monitor (→ 2) ou deixar só ela (⤢ FOCO). **Workspaces**: digite um nome e Enter para guardar o arranjo atual; ▶ MONTAR remonta tudo (e abre o que estiver fechado); ✕ apaga (pergunta antes). |
| 🖥 **Meu PC** | Processador e memória ao vivo (a barra fica âmbar a partir de 70% e vermelha a partir de 90%) e disco livre; 🔎 O QUE ESTÁ PESANDO? lista os programas que mais gastam, com ✕ FECHAR (pergunta antes; nunca fecha programas do Windows nem o JARVIS). Também aparece um resumo no Início. |
| 📅 **Agenda** | A próxima reunião; 🎧 ATIVAR MODO REUNIÃO / ✓ TERMINEI A REUNIÃO; ligar/desligar o aviso antes das reuniões e escolher com quantos minutos (2, 5, 10 ou 15). |
| 🧰 **Ferramentas** | Conversor (digite "5 milhas em km" e Enter); senha forte de 16, 20 ou 32 caracteres (vai direto para a área de transferência); texto copiado (📝 resumir, 💡 explicar, 🌐 traduzir, ✍ corrigir); dossiê (tema e Enter) e a lista dos salvos (▶ LER abre o painel com as fontes). |

No bloqueio do robô também ficaram os botões ⟳ ATUALIZAR (com a bolinha de versões novas) e 📘 BRANDING.

**Bloqueio do robô (V8.16):** só o avatar do JARVIS, com as funções do bloqueio clássico (sem a faixa de cartões, que saiu na V9.1.1 para a tela ficar limpa): o microfone (P) e a Sentinela com a legenda do que ele ouviu, as palmas, o painel do Modo Torcedor e o **⚙ GERENCIAR** (canto de cima) com os atalhos de sempre (visitante, nova pessoa, atualizar, Modo Desk, app Windows, branding, otimizar, notas, diagnóstico), o bloqueio clássico, a foto do rosto, o fundo do Modo Torcedor e o papel de parede do robô. A expressão e o anel de luz em volta dele seguem o estado: ouvindo (verde), falando, pensando (reconhecendo o rosto), liberado, não reconhecido e dormindo de madrugada. O Tamagotchi, o jogo das estrelas e as atividades automáticas (da V8.9 à V8.15) saíram: a tela ficou mais leve.

### Modo Desk e app para Windows (V8.0)

| Fale / toque | O que acontece |
|---|---|
| 🖥 MODO DESK (central, ⚡ CONTROLES, bloqueio) | Troca para o layout de app de assistente; ◐ CENTRAL CLÁSSICA volta. |
| "Marquei o treino de hoje" · "como estão meus hábitos?" | Marca o hábito (sequência de dias) e diz quantos faltam hoje. |
| Modo Desk › Copiados | Histórico do Ctrl+C no PC; toque para copiar de novo (não guarda senha, cartão ou código). |
| Modo Desk › Memória | Mapa das memórias por assunto; tocar mostra e permite esquecer. |
| Modo Desk › Personalizar | Cores e expressão do robô; guarda-roupa (chapéus, rosto, roupas, olhos, efeitos); temas das datas; nome; cor do app. |
| Modo Desk › Cérebro (IA) | Automático grátis (Groq + Gemini, troca sozinho no limite); cole a chave da IA (fica só no .env do PC); testar (V8.2). |
| "Quais são minhas missões?" · "como está minha ofensiva?" | As 3 missões do dia (V8.1) e a ofensiva com recorde e protetores. |
| Modo Desk › Missões | Missões do dia, desafio da semana e 🔥 ofensiva; responda as perguntas "sobre você" ali mesmo. |
| ⬇ APP PARA WINDOWS · Gerar-App-Windows.bat | Instala o atalho **JARVIS** (Área de Trabalho e Menu Iniciar): janela própria, ilha no topo da tela e tecla para falar (PageDown). Sem .exe novo, o antivírus não bloqueia (V8.1.1). |

### Olho de Deus: globo 3D e dados reais (V7.11)

| Fale / toque | O que acontece |
|---|---|
| 🌐 GLOBO (no Olho de Deus) | Globo 3D com radar de chuva, voos, terremotos, queimadas e Estação Espacial ao vivo. Cada camada liga e desliga no painel. |
| "Mostra os voos agora" | Abre o globo nos voos e diz quantos aviões voam perto da sua cidade. |
| "Tem terremoto hoje?" | Quantos terremotos houve em 24 h e qual foi o maior. |
| "Tem queimada perto?" | Focos de queimada a menos de 50 km (e o mais próximo). |
| "Quando a estação espacial passa?" | A próxima passagem visível no seu céu: hora, direção e nuvens. |
| "Mostra o radar de chuva" | Abre o radar animado e diz quando vai chover. |
| Holograma aberto: "espera, o que é…?" (V7.14) | Pausa, responde num balão (e falando) e continua da mesma cena. Também pelo botão ❓. |
| No fim da apresentação: 🧠 QUIZ · "letra B" | 3 perguntas de múltipla escolha, com placar e explicação. |
| ☆ SALVAR · "hologramas salvos" | Guarda a apresentação ou receita; a lista abre também em ⚡ CONTROLES › HOLOGRAMAS SALVOS. |
| "Quanto está o dólar?" · "quem ganhou o jogo?" | Além da resposta, um cartão animado no canto (número com mini-gráfico, placar, foto ou lista). |
| "Qual o próximo lançamento de foguete?" (V7.11.1) | Diz qual é, de qual empresa e quando; no globo, toque na base para ver foto, ▶ ASSISTIR e ↗ SITE. |
| Tocar num ponto | Cartão com os detalhes (voo, altitude, força do terremoto, município da queimada). |
| Avisos (no painel) | Chuva forte chegando · queimada/terremoto perto · ISS visível. Cada um liga e desliga. |

### Central de Agentes (V6.8.3)

Botão 🤖 AGENTES ao lado do Olho de Deus (ou em CONTROLES): exemplos de cada agente, lugares salvos (▶ ROTA, adicionar, apagar) e um chat com os agentes.

### Sub-agentes: rotas e pesquisa (V6.8)

O JARVIS entrega o pedido a um agente especialista. Ele aparece na tela enquanto trabalha ("🧭 Agente de rotas: rota para o trabalho") e abre o resultado **no aparelho de onde veio o pedido** (no celular, o Google Maps/YouTube; no PC, o navegador). Funciona também fora de casa, pela nuvem.

| Diga | O que acontece |
|---|---|
| "Meu trabalho fica na Av. Paulista, 1000" / "o endereço da academia é Rua Augusta, 500" | O agente de rotas guarda o lugar. |
| "Quero ir para o trabalho" / "me leva pra academia" / "rota para o aeroporto de Guarulhos" | Abre o Google Maps com a rota saindo de onde você está. |
| "… a pé" / "de ônibus" / "de bicicleta" | Rota no modo pedido. |
| "Quais são meus lugares?" / "esquece o endereço da academia" | Lista ou apaga. |
| "Abre o YouTube e pesquisa receita de bolo" / "procura lofi no YouTube" | O agente de pesquisa abre a busca no YouTube. |

Se o navegador bloquear a janela nova, aparece um botão "Abrir a rota no Google Maps ›" para tocar.

### Ofensiva da água 🔥 (V6.8)

| Diga | O que acontece |
|---|---|
| "Qual minha ofensiva de água?" | Quantos dias seguidos você bateu a meta, quanto falta hoje para manter e o recorde. |
| (sozinho) | O painel de água mostra "🔥 Ofensiva de N dias"; ao bater a meta ele comemora; depois das 17h o lembrete avisa se a ofensiva está em risco. Fora de casa, a nuvem continua a contagem. |

### Timers e avisos para todos (V6.7.1)

| Diga | O que acontece |
|---|---|
| "Timer de 15 minutos para o arroz" | Timer com nome (pode ter vários ao mesmo tempo). Quando acaba, aparece em todas as telas, fala no PC **e nos celulares com a central aberta**, e o app recebe notificação. |
| "Quanto falta pro arroz?" | Quanto falta daquele timer. |
| "Aumenta 5 minutos no timer do arroz" | Estica o timer. |
| "Cancela o timer do arroz" / "cancela todos os timers" | Cancela só o do arroz, ou todos. Com vários e sem dizer qual, ele pergunta. |
| "Avisa em todos os aparelhos que o almoço está pronto" / "anuncia que estou saindo" | Fala o aviso no PC e nos celulares, mostra em todas as telas e notifica o app. |

Timers continuam correndo depois de o JARVIS reiniciar (cada atualização reinicia); se algum acabou durante o reinício, ele avisa.

### Bem-estar (V6.7)

O JARVIS como um mordomo atento, **não um psicólogo**: ele acolhe, sugere técnicas simples e indica ajuda profissional quando faz sentido. Funciona no PC, no bloqueio e pela nuvem.

| Diga | O que acontece |
|---|---|
| "Exercício de respiração" / "me ajuda a respirar" | Respiração guiada **4-7-8** (três ciclos). "Respiração quadrada" para a 4-4-4-4. |
| "Me ajuda a me acalmar" / "aterramento" | Técnica **5-4-3-2-1** (o que você vê, toca, ouve, cheira e sente). |
| "Meu humor hoje é 3" / "estou me sentindo 4 de 5" / "registra meu humor como bom" | Registra o humor do dia (1 a 5) e responde conforme a nota. |
| "Como foi meu humor essa semana?" | Média dos últimos 7 dias e se está melhorando ou caindo. |
| Desabafos ("tô exausto", "foi um dia difícil") | A IA acolhe primeiro, pergunta e só depois sugere algo prático. Se o mal-estar for persistente, sugere um psicólogo. |
| Frases de crise ("quero morrer", "penso em me machucar") | Resposta fixa e acolhedora com **CVV 188** (24 h, gratuito, chat em cvv.org.br) e **SAMU 192**, sem passar pela IA, até com a central bloqueada. Expressões comuns ("me matar de rir", "morrer de vergonha") não disparam. |

Ao entrar na central: na primeira vez do dia o JARVIS já começa o **briefing**. Nas próximas, pergunta se repete ou pula (botões, Enter/Esc ou "repetir"/"pular").

### Skills: janelas, sistema e agenda (V8.11)

Habilidades plug-and-play (pasta `backend/skills/`). Funcionam pela frase exata **e** pela IA: dá para pedir do seu jeito ("joga o Chrome lá na tela da direita") que a IA chama a skill certa. Ações marcadas com ⚠️ sempre pedem um "sim" antes e só valem no próprio PC.

**Workspace (janelas e monitores, só no Windows)**

| Diga | O que acontece |
|---|---|
| "Quais janelas estão abertas?" | Lista os programas abertos, separados por monitor. |
| "Manda o Chrome pro monitor 2" / "leva o Spotify para a outra tela" / "manda isso pro monitor principal" | Move a janela (mantém maximizada, se estava). "Isso" = a janela da frente. Monitor 1 é o principal. |
| "Organiza as janelas" / "organiza as janelas do monitor 2" | Põe as janelas em grade em cada monitor. |
| "Coloca o Chrome e o VS Code lado a lado" | Divide a tela entre os dois. |
| "Deixa só o Word na tela" | Maximiza o Word e minimiza as outras janelas daquele monitor. |
| "Salva esse layout como estudo" | Guarda onde está cada janela (programa, monitor e tamanho). |
| "Abre o workspace estudo" | Remonta: põe cada janela no lugar e abre os programas que faltam. |
| "Quais são meus workspaces?" / ⚠️ "Apaga o workspace estudo" | Lista ou apaga os salvos. |

**System Guard (o PC)**

| Diga | O que acontece |
|---|---|
| "O que está pesando no PC?" / "quais programas estão usando mais memória?" | Os programas que mais gastam memória e processador agora, com um cartão. |
| "Como está o uso do processador?" / "quanto de memória está usando?" | Processador, memória, disco e bateria. Vale com a central bloqueada. |
| ⚠️ "Fecha o Discord" / "encerra o Spotify" | Pergunta antes e fecha todas as janelas do programa. Programas do Windows, antivírus e o próprio JARVIS nunca são fechados. |
| Sozinho (vigia) | Processador acima de 90% por 2 minutos ou memória acima de 92% por 1 minuto: avisa uma vez (no máximo a cada 30 min), diz o programa que mais gasta e oferece fechar ("sim"). "Desliga o vigia do sistema" / "liga o vigia do sistema". |

**Segurança e otimização (V9.3)** — tudo local: nenhuma foto sai do PC

| Diga | O que acontece |
|---|---|
| "Liga o vigia da câmera" / "desliga o vigia da câmera" (ou Configurações › Bloqueio) | Precisa da foto do rosto cadastrada. **Bloqueada:** olha a cada ~20 s; se alguém que não é de casa aparecer em duas olhadas seguidas, guarda a foto, avisa no celular e na tela e diz "Não reconheço quem está aí". **Liberada:** confere a cada ~60 s; se outra pessoa estiver sozinha na frente do PC, bloqueia a central (com foto); se o senhor sair por 2 a 15 minutos (escolha), bloqueia sozinho (e o Windows também, se marcado). A luz da câmera acende rapidinho a cada olhada. |
| "Relatório de segurança" / "alguém tentou entrar?" / "alguém mexeu no meu PC?" | Fala o resumo e abre a janela **🛡️ SEGURANÇA**: quem tentou entrar ou apareceu sem ser reconhecido (com a foto; toque para ampliar), pendrives ligados, bloqueios automáticos e a otimização do dia (com **VER E LIMPAR**). Ao entrar na central, ela **abre sozinha** quando há novidade. Também na paleta Ctrl+K. |
| "Há quanto tempo eu estou no PC?" / "o que eu estou fazendo?" | Com o vigia ligado: há quanto tempo o senhor está na frente do PC e quantas vezes saiu hoje (sugere uma pausa depois de 1 h 30). Não descreve a cena (nada vai para a IA). |
| Sozinho: pendrive | Um pendrive ou HD externo ligado no PC vira aviso na tela e no celular, com a letra e o tamanho, e entra no relatório. |
| Sozinho: otimização do dia | 1 vez por dia, com o PC parado há 10 min (das 9h às 23h), faz a varredura. Se achar temporários, lixeira cheia, muitos programas abrindo com o Windows ou disco quase cheio, deixa a sugestão no relatório. Nada é apagado sem o senhor mandar. |

Uma tentativa de entrar pelo rosto que falha também entra no relatório (com foto, se o vigia estiver ligado).
Desde a V9.4, a foto de quem tenta entrar vem ligada (Configurações › Bloqueio › "Guardar o rosto de quem tentar entrar") e também vale para o **PIN errado digitado no PC** e para **teclas erradas** com a tecla de acesso ligada. Se a câmera reconhecer o próprio senhor (errou o PIN), nada é registrado.

**Tela de bloqueio, tecla de acesso e avatar (V9.4)**

| Diga / faça | O que acontece |
|---|---|
| "Deixa o clima sempre aparecer na tela de bloqueio" / "coloca o clima e a água na tela de bloqueio" / "mostra o relógio no bloqueio" | Fixa o widget no bloqueio (relógio, clima, Spotify, água de hoje, próximo jogo). Ele entra com uma animação, e o clima ganha a animação do tempo de agora: sol girando, lua e estrelas, nuvens, chuva, raio, neblina ou neve. Muda na hora, sem recarregar. |
| "Tira a água da tela de bloqueio" / "não quero o Spotify no bloqueio" | Esconde o widget. |
| "Coloca meu avatar na tela de bloqueio" / "tira o avatar da tela de bloqueio" (ou Configurações › Bloqueio) | O PC transforma a foto do seu rosto num **holograma** (ciano, com linhas de varredura), salvo em `data/avatar_holo.png`, e ele aparece no centro do bloqueio, no lugar do reator/orbe. Flutua, um feixe passa por ele, acelera ao verificar, fica verde ao reconhecer e treme em vermelho se não reconhecer. É refeito sozinho quando a foto do rosto muda. |
| Configurações › Bloqueio › **Tecla de acesso** | Escolha uma tecla (letra, número ou F1–F12; espaço, Enter, Esc e P não valem). Com ela ligada, a câmera **só começa a verificar o rosto depois dessa tecla**: espaço, clique, palmas e "abrir central" não abrem mais a câmera. Rosto reconhecido entra direto. A tela bloqueada mostra só "⌨ TECLA DE ACESSO", nunca qual é. 6 teclas erradas seguidas = tentativa no relatório (com foto) e a tecla fica 2 minutos sem valer. O PIN continua funcionando. |

**Analisar imagem (V9.4)**

| Diga | O que acontece |
|---|---|
| "Analisa essa imagem" / "o que tem nessa foto?" / "analisa o print que eu tirei" / "analisa a imagem que eu copiei" / "lê essa imagem" | Pega a imagem copiada (Ctrl+C numa imagem, Win+Shift+S ou um arquivo de imagem copiado no Explorer) ou, sem ela, a imagem mais nova dos últimos 30 minutos em Downloads, Área de Trabalho, Imagens ou capturas de tela. Manda para a IA com o seu pedido, fala a resposta curta e mostra o cartão **ANÁLISE DA IMAGEM**. Nada é guardado. Só no próprio PC. |
| **Ctrl+V** com uma imagem na central | Abre a janela da foto (analisar, ler, pesquisar, holograma), igual a arrastar a imagem. |

Para copiar só o texto de uma imagem, sem IA, continue usando "copia o texto da imagem que eu copiei".

**Modo gravar (V9.4)** — ensinar o JARVIS a fazer uma sequência

| Diga | O que acontece |
|---|---|
| "Modo gravar" / "vou te ensinar uma rotina chamada estudo" / "começa a gravar" | Começa a gravar e mostra **⏺ GRAVANDO** no topo da central, com o número de passos. |
| (os pedidos, normalmente) | Cada pedido que deu certo vira um passo: "abre o Spotify", "organiza as janelas lado a lado", "volume 30"… O que a IA só respondeu (conversa, pesquisa) não entra. Até 15 passos. |
| "Para de gravar" / "salva como estudo" / tocar em **PARAR** | Salva a rotina (com o nome do começo ou o que o senhor disser; sem nome, vira "rotina 1"). |
| "Estudo" (o nome sozinho) / "executa a rotina estudo" | Refaz tudo, na ordem, com as mesmas regras de sempre. Uma ação que pede "sim" pergunta de novo. Se um passo falhar, ele diz qual. |
| "Quais são as minhas gravações?" / ⚠️ "Apaga a rotina estudo" / "cancela a gravação" | Lista, apaga (pede "sim") ou descarta a gravação em andamento. |

**Auto-análise (V9.2)**

| Diga | O que acontece |
|---|---|
| "Faz uma auto análise" / "analisa o meu PC" / "faz um diagnóstico do sistema" | O JARVIS examina o PC agora e responde com o estado e a sugestão principal. Também mostra o cartão **AUTO-ANÁLISE** com o que olhou e até 4 sugestões. Ele olha: memória e processador, o navegador com muitas abas (conta as do navegador do JARVIS), programas em segundo plano gastando memória (Teams, Discord, Steam, OneDrive…), ele mesmo, há quantos dias o PC não reinicia, se o Windows está usando o disco como memória e o espaço livre no disco. |
| "Por que a memória está alta?" / "por que o processador tá no talo?" / "como liberar memória?" / "como melhorar o desempenho?" | O mesmo diagnóstico. Com a memória a partir de 80%, oferece ⚠️ fechar o programa mais pesado que é seguro fechar (nunca o navegador, programas do Windows nem o próprio JARVIS) e só fecha depois do "sim". |
| Botão **⚡ ANALISAR** na central | Aparece embaixo de PROCESSADOR ou MEMÓRIA quando o uso fica no amarelo (70% ou mais) ou no vermelho (90% ou mais). Um toque pede a auto-análise. (Até a V9.3 o botão aparecia mas não respondia ao clique; corrigido na V9.4.) |
| Sozinho (aviso calmo) | Memória acima de 85% por 3 minutos: aviso na tela e no celular, com a sugestão principal, no máximo 1 vez por hora e sem voz. Acima de 92%, continua o aviso falado do vigia, que oferece fechar o que mais gasta. |

Para a varredura completa (temporários, lixeira, inicialização), continue usando "meu PC está lento".

**Context Autopilot (agenda)**

| Diga | O que acontece |
|---|---|
| Sozinho, 5 min antes de cada compromisso com horário | "Senhor, Daily do time começa em 5 minutos. Quer que eu ative o modo reunião e abra o link da chamada?" Com a central bloqueada, o aviso vai só para o celular. |
| "Sim" (ao aviso) / "ativa o modo reunião" / "vou entrar em reunião" | Pausa o Spotify, abre o link (Meet, Zoom, Teams, Webex, Jitsi), monta o workspace "reuniao" se você tiver salvo um e o JARVIS fica em silêncio. |
| "Terminei a reunião" / "sai do modo reunião" | Volta a falar. Também sai sozinho quando o evento acaba. |
| "Qual minha próxima reunião?" | O próximo compromisso com horário e se tem link de chamada. |
| "Me avise 10 minutos antes das reuniões" / "desliga o piloto automático da agenda" | Ajusta a antecedência (1 a 30 min) ou liga/desliga os avisos. |

**Deep Brief (dossiê com pesquisa a fundo)**

| Diga | O que acontece |
|---|---|
| "Faz um dossiê sobre carros elétricos no Brasil" / "monta um relatório sobre a reforma tributária" / "prepara um resumo completo sobre o James Webb" | Divide o tema em até 4 ângulos, pesquisa todos no Google ao mesmo tempo, fala um resumo de 3 a 5 frases e abre o cartão **DOSSIÊ** (painel com tópicos e fontes). Leva de 20 s a 1 min; o progresso aparece na tela. O dossiê completo fica em `data/dossies/` (Markdown). Usa 1 da cota diária da pesquisa profunda; se ela estiver desligada, pergunta se libera só desta vez. |
| "Quais são meus dossiês?" | Os salvos, do mais recente para o mais antigo. |
| "Lê o dossiê sobre carros elétricos" / "abre o dossiê da reforma tributária" | Fala o resumo de novo e mostra o painel. |

**Abrir programas desconhecidos (Q8)**

| Diga | O que acontece |
|---|---|
| "Abre o Discord" (está no Menu Iniciar) | Abre direto, como antes. |
| "Abre o winword" (só no PATH ou no registro do Windows) | ⚠️ "O Winword não está nos seus atalhos. Abro o programa WINWORD.EXE?" e só abre depois do "sim". |
| "Abre o prompt de comando" / "abre o PowerShell" / "abre o regedit" | ⚠️ Sempre pede o "sim" ("executa comandos no sistema"), mesmo vindo do Menu Iniciar. Pedido feito pelo celular: recusado. |

**Texto copiado (Clipboard AI, só no Windows)**

| Diga | O que acontece |
|---|---|
| "Resume o que eu copiei" / "explica o texto copiado" | Fala o resumo (ou a explicação) do que está na área de transferência e mostra um cartão. |
| "Traduz o que eu copiei" / "traduz o que copiei para o espanhol" | Traduz (português ↔ inglês por padrão) e deixa a tradução copiada: é só colar com Ctrl+V. |
| "Corrige o texto que eu copiei" / "revisa o que copiei" | Corrige ortografia e gramática e deixa o texto corrigido copiado. |

**Dia a dia**

| Diga | O que acontece |
|---|---|
| "Quanto é 5 milhas em km" / "converte 350 Fahrenheit para Celsius" / "2 xícaras em ml" / "1,5 GB em MB" / "100 km/h em mph" | Conversão na hora, sem internet e sem IA (vale com a central bloqueada): comprimento, peso, volume de cozinha, temperatura, velocidade e dados. |
| "Gera uma senha forte" / "cria uma senha de 16 caracteres" | Copia uma senha aleatória (maiúsculas, minúsculas, números e símbolos, sem O/0/I/l/1) para a área de transferência do PC. A senha nunca é falada nem mostrada. |
| "Que dia vai ser daqui a 45 dias?" / "que dia foi há 10 dias?" / "daqui a 2 meses" (V8.13) | Calculadora de datas, na hora e sem IA: diz o dia da semana e a data. |
| "Quantos dias se passaram desde 10 de março?" / "há quantos dias foi o carnaval?" (V8.13) | Dias (e semanas) desde a data. Entende 10/03, 10/03/2025, "10 de março de 2025", hoje, ontem, amanhã, Natal, Páscoa, Carnaval e outros feriados. "Quanto falta para…" continua com a contagem regressiva. |
| "Que dia da semana cai o Natal?" / "7 de setembro de 2022 foi em que dia da semana?" / "quantos dias entre 10/03 e 25/12?" (V8.13) | Dia da semana de uma data e dias entre duas datas. |
| "Cara ou coroa" / "joga dois dados" / "joga um dado de 20 lados" / "sorteia um número de 1 a 100" / "escolhe entre pizza, hambúrguer ou sushi" (V8.13) | Sorteio de verdade, na hora. |
| "Toca a música do Homem de Ferro" / "toca Back in Black" / "modo Homem de Ferro" (V8.13) | Toca a música de entrada (padrão: Back in Black, do AC/DC) no seu Spotify. Ela também toca ao entrar na central, ao abrir o botão **VOZ** do topo e na **inicialização do dia** (V8.14.1): no briefing de "bom dia" ela começa baixinho, como trilha, e sobe no fim (uma vez por dia; não interrompe música que já está tocando). Tudo desligável no próprio botão VOZ. Precisa do Spotify conectado. No painel VOZ há também a **barra de volume da música** (V8.15.1): muda o Spotify na hora e fica guardada (o Back in Black e o fim do briefing usam esse volume). |
| Briefing com música tocando (V8.15.1) | O JARVIS **pausa o Spotify** enquanto lê o briefing (bom dia, boa tarde, boa noite ou por assunto) e **continua a música** no fim, de onde parou. Não retoma se você trocou de música no meio. Desligável no botão VOZ ("Pausar a minha música durante o briefing"). |
| "Quais são suas habilidades?" | Diz o que está ligado e abre a aba **⚡ HABILIDADES** da Central de Agentes. |

**Memória pesquisável (V9.0)**

| Diga | O que acontece |
|---|---|
| "O que eu te falei sobre a viagem?" / "o que eu anotei sobre o dentista?" / "o que eu copiei sobre o hotel?" | Procura em TODAS as conversas com o JARVIS (não só as últimas), nas memórias ("lembre que…"), tarefas, lembretes e copiados. Na hora, sem internet e sem IA; ignora acentos e aceita o começo das palavras ("viag" acha "viagem"). |
| "Procura na memória sobre o carro" / "busca nas minhas conversas a senha do wifi" / "quando eu falei do aniversário da minha mãe?" | O mesmo, com o trecho mais relevante falado e os outros num cartão **MEMÓRIA**. O índice fica em `data/memoria_busca.db` e não sai do PC. |

**Copiar e colar por voz (V9.0, só no Windows)**

| Diga | O que acontece |
|---|---|
| "O que eu copiei?" / "qual foi a última coisa que eu copiei?" / "mostra os copiados" | Fala o último e mostra os 5 mais recentes. |
| "Copia de novo o último link" / "copia de novo o penúltimo" / "cola o e-mail que eu copiei" / "copia de novo o endereço" / "copia de novo o número" | Devolve o item à área de transferência: é só colar (Ctrl+V). |
| "Fixa o último copiado" | ★ Fixa: não sai por limite nem no LIMPAR. Também dá para fixar com a ★ na lista de Copiados do Modo Desk. |
| ⚠️ "Apaga os copiados" | Pergunta antes; os fixados ficam. |

**Tempo de tela e resumo da semana (V9.0, só no Windows)**

| Diga | O que acontece |
|---|---|
| "Quanto tempo eu fiquei no Chrome hoje?" / "quanto tempo passei no Discord ontem?" / "… essa semana?" | O tempo com o programa em primeiro plano. Só conta o NOME do programa (nunca o título da janela) e para de contar depois de 5 min sem mexer no teclado e no mouse. |
| "Meu tempo de tela hoje" / "quais programas eu mais usei essa semana?" | O total e os programas mais usados, com cartão. |
| "Resumo da semana" / "como foi minha semana?" | Tarefas feitas, dias com a meta de água, ofensiva, XP ganho e os programas mais usados nos últimos 7 dias. |
| "Para de medir meu tempo de tela" / "volta a medir meu tempo de tela" | Liga e desliga a medição (60 dias ficam guardados em `data/tempo_de_tela.json`). |

**Ler o texto da tela, offline (V9.0, só no Windows)**

| Diga | O que acontece |
|---|---|
| "Copia o texto da tela" / "pega o texto dessa janela" / "o que está escrito na tela?" | Reconhece o texto da tela com o OCR do próprio Windows (sem internet nem IA), deixa copiado (é só colar) e mostra as primeiras linhas num cartão. A imagem usada é apagada na hora. |
| "Copia o texto da imagem que eu copiei" / "lê o texto do print que eu copiei" | O mesmo, com a imagem que está na área de transferência (um print com Win+Shift+S, por exemplo). |

Precisa do pacote de idioma português do Windows (Configurações > Hora e idioma). "Leia a tela" / "explica a tela" continuam com a IA olhando a tela.

**Navegador (V9.0, Chrome ou Edge do PC)**

| Diga | O que acontece |
|---|---|
| "Salva as abas como sessão trabalho" | Guarda os sites abertos no navegador do JARVIS com esse nome. |
| "Abre a sessão trabalho" / "quais sessões do navegador eu tenho?" | Reabre todos os sites de uma vez (liga o navegador se precisar) ou lista as sessões. |
| "Quantas abas estão abertas?" / "vai para a aba do gmail" | Conta as abas (e de quais sites) ou traz a aba do site para a frente. |
| "Fecha as abas do youtube" / "reabre as abas que você fechou" | Fecha todas as abas daquele site e guarda os endereços para reabrir depois. |
| "Roda a macro bater ponto" / "quais macros eu tenho?" | Roda uma macro de passos (abrir site, esperar, clicar, digitar), com o progresso na tela. |
| "Resume essa página" | A IA lê a aba aberta e resume em poucas frases. |

O JARVIS abre o navegador com um **perfil próprio** (`data/chrome_jarvis`) e a porta de depuração só no próprio PC (127.0.0.1): na primeira vez, entre nos seus sites nesse navegador e eles ficam guardados. As macros ficam em `data/navegador.json`, na chave `macros`; cada passo é um de `{"abrir": "https://..."}`, `{"esperar": 2}` (até 10 s), `{"clicar": "seletor CSS"}` ou `{"digitar": "seletor CSS", "texto": "..."}` (até 30 passos). Exemplo:

```json
{"macros": {"bater ponto": {"passos": [
  {"abrir": "https://ponto.exemplo.com"}, {"esperar": 2},
  {"digitar": "#usuario", "texto": "meu.usuario"}, {"clicar": "button[type=submit]"}]}}}
```

**Na central (V9.0)**

- **Paleta de comandos: Ctrl+K** (ou o botão **⌕ COMANDOS** no rodapé). Procure qualquer coisa: telas (configurações, finanças, sistema, água, logs…), as frases das habilidades, o que você falou ou copiou (memória e copiados). Setas escolhem, **Enter** executa (memória e copiados: Enter copia o trecho) e **Esc** fecha. O que não bater com nada vira pergunta para o JARVIS.
- **A voz começa antes**: numa resposta longa, o JARVIS já fala as primeiras frases enquanto a IA ainda escreve o resto (antes, esperava a resposta inteira).
- **Fila de pedidos**: pedido feito enquanto ele pensa em outro não se perde mais (antes era ignorado ou "ocupado"). Ele espera a vez (até 3 na fila, aparece **NA FILA** embaixo) e é atendido na ordem, depois da resposta anterior. Vale para a voz do ouvido, o celular e a central. Cancelar (Esc, o botão ou "Jarvis, para") esvazia a fila.
- **Visual 9.0**: a central muda de clima com a hora do dia (mais clara de manhã, mais funda à noite, quase apagada de madrugada), com transição suave das cores, e os painéis entram em sequência ao abrir (some com "reduzir movimento").

**Visual 9.1: vidro**

- Toda a interface usa o mesmo vidro (glassmorphism): painéis, menus, janelas, Modo Desk e Configurações. Com "alto contraste" (Configurações › Acessível) o vidro sai e tudo fica sólido.
- **Janela do Spotify** (cartão do Spotify, botão SPOTIFY do topo ou "ESCOLHER MÚSICA"): capa desfocada no fundo, controles, volume, busca de música ou playlist (botão ≡) e os atalhos de clima 🎧 Lo-fi para focar, 🌙 Relaxar, 🎷 Jazz calmo e 🌧 Chuva (um toque toca uma playlist).
- **Configurações**: seções no menu lateral (no celular, numa faixa que rola); clique fora ou ✕ fecha.

**Aba ⚡ HABILIDADES (Central de Agentes)**: todas as skills por grupo, com o nível de permissão (LEITURA, AÇÃO, CRÍTICA), liga/desliga, quantas vezes foram usadas, falhas e tempo, e os exemplos: um toque manda a frase para o JARVIS. Também abre pelo botão da Central de Agentes.

**Melhorias de velocidade e honestidade (V8.11)**: a pesquisa no navegador consulta Google, Bing e DuckDuckGo ao mesmo tempo (no máximo 7 s); "próxima aba", "fecha a aba", "nova aba" e "reabre a aba" respondem na hora, conferem que o navegador veio para a frente e nunca fecham a aba da central; e quando a IA falha, o JARVIS diz o motivo (sem chave, sem internet, recusa) em vez de um erro técnico.

Para desligar uma skill inteira: na aba ⚡ HABILIDADES, ou `POST /api/skills/<nome>/toggle` com `{"enabled": false}` (a lista com os nomes está em `GET /api/skills`).

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
