# Changelog

Mudanças do JARVIS por versão, da mais nova para a mais antiga.

## 8.6.1 — 16 de novembro de 2026

**📐 Telas que se adaptam a qualquer tamanho (bloqueio e central)**
- **Tela de bloqueio (Sentinela e Clássica):**
  - em telas mais baixas (ex.: 1920×860, 1366×768), a faixa "MIC SILENCIADO · ESPAÇO = LIBERAR" ficava em cima dos botões. Agora ela vem **logo abaixo dos botões**, junto com o "alterar foto";
  - o relógio, o orbe e os espaços encolhem conforme a **altura** da tela, não só conforme a largura;
  - o conteúdo nunca passa por baixo dos botões do rodapé (Áudio, Fundo, Modo Torcedor, Celular) e, se não couber, **rola**;
  - em telas estreitas ou baixas, o rodapé e o carimbo entram no fim da página, em vez de flutuar por cima dos cartões;
  - com os cartões nas laterais, os botões do meio ficam no espaço entre as duas colunas (em 1280 px, "NOVA PESSOA" ficava embaixo do cartão do Spotify).
- **Central desbloqueada:**
  - em telas até 1100 px, os painéis ficavam uns por cima dos outros no rodapé. Agora vira uma coluna só, que rola, com cada painel na altura dele;
  - em telas até 1000 px, o cabeçalho quebra em duas linhas, em vez de cortar o perfil e o BLOQUEAR.
- Conferido em 1920×1080, 1917×862, 1600×900, 1366×768, 1280×720, 1100×700 e 900×700.

## 8.6.0 — 16 de novembro de 2026

**😈 Modo Pac-Man, avatar "vivo" e avatar maior na pílula**
- **Modo Pac-Man:** cutuque o avatar 5 vezes seguidas, no topo da ilha aberta ou na barra lateral do app. Ele fica surpreso, depois bravo e, na 5ª:
  - sai da ilha numa janelinha transparente e **corre atrás do seu mouse** com a boca abrindo e fechando, virando para o lado certo;
  - começa devagar (dá para fugir um pouco), vai acelerando e sempre alcança em até 12 s;
  - quando pega, **"come" o mouse**: segura o cursor na boca por 2,6 s mastigando ("nhac nhac!" e migalhas);
  - depois devolve o mouse, feliz, e volta para a ilha;
  - **Esc** para tudo na hora e solta o mouse;
  - no navegador (fora do app do Windows), ele só fica bravo e avisa.
- **Avatar "vivo" quando parado:** ele "respira" de leve o tempo todo. As brincadeiras começam bem mais cedo (25 s parado, antes era 1 min 30 s) e ganharam o **pulinho** e o **sorriso**. Ele cochila depois de 8 min.
- **Brincadeiras na ilha:** no app do Windows, o tempo parado agora é o do **PC inteiro** (o Windows informa a última vez que você mexeu no mouse ou no teclado). Antes a ilha só via o mouse passando por cima dela.
- **Avatar maior na pílula:** a ilha ficou um pouco mais alta (56 px na média) e o avatar aparece em **close no rosto** (50 px), para dar para ver a expressão.

## 8.5.0 — 16 de novembro de 2026

**🔄 Atualização automática, pílula nova da ilha, zoom e tamanho do painel**
- **Atualiza sozinho (sem pasta nem CMD):**
  - a cada 30 minutos o JARVIS confere se tem versão nova;
  - se tiver, espera um momento em que ele está parado (nada rodando e ninguém falou com ele nos últimos 5 minutos) e atualiza igual ao botão ATUALIZAR, mas sem falar: só avisa na ilha ("⬆ Atualizando o JARVIS para a versão …");
  - a interface nova vem pronta do site, a ilha e a janela se recarregam sozinhas, e o **app do Windows se reabre sozinho** quando o código dele mudou (espera o JARVIS voltar e a ilha estar fechada);
  - liga/desliga em Configurações › Atualizações (vem ligado).
- **Pílula da ilha mais bonita:**
  - avatar à esquerda, estado no meio (ou a música, com equalizador) e a hora à direita;
  - "Pensando" com pontinhos e contorno amarelo, "Falando" com ondas na cor do app.
- **Corrigido:**
  - **"Pensando…" preso:** se o aviso de "parado" se perde (por exemplo, numa falha da voz), depois de 45 s sem nada rodando a ilha volta ao normal.
  - **Pílula com cantos cortados:** o recorte era feito antes de o Windows terminar de mudar o tamanho da janela. Agora é refeito logo depois.
- **Zoom do painel:** A− e A+ na barra de cima da ilha aberta, e um controle em Configurações › Ilha (70% a 140%; começa em 90%, para a Personalização não ficar tão "perto").
- **Tamanho do painel aberto:** Compacto (860×540), Médio (980×600) ou Grande (1200×740), em Configurações › Ilha, mais um botão **⟲ Centralizar**.
- O fluxo de atualização virou uma função só (`perform_update`), usada pelo botão e pelo automático.

## 8.4.1 — 16 de novembro de 2026

**🏝️ A ilha abre o app inteiro, igual ao vídeo, e dá para arrastar para os lados**
- **Clique na pílula:** desce do topo um painel largo (980×600) com o **Modo Desk inteiro**, como no vídeo:
  - à esquerda, a barra lateral com avatar, nível, ofensiva e os menus (Início, Conversa, Memória, Tarefas, Lembretes, Missões, Hábitos, Timers, Música, Copiados, Rotinas, Meu PC);
  - as **Configurações** (Personalizar, Cérebro, Funções, Voz, Ilha, Atualizações...);
  - à direita, as mesmas telas do app.
  - Substitui o painel simplificado da 8.3.0, que não tinha Personalizar.
- **Arrastar:** segure a pílula, ou a barra de cima do painel aberto, e arraste para a esquerda ou a direita. A ilha lembra onde ficou (`ilha.posicao`). Dois cliques num espaço vazio da barra levam de volta ao centro.
- **Barra de cima do painel:** estado (ou a música tocando), hora, 🖥 janela grande, ⏻ sair e ✕ fechar.
- **Fecha** no ✕, com Esc, clicando fora ou depois de 2 minutos parada. Não fecha mais ao perder o foco, porque escolher uma cor abre uma janelinha do Windows.
- **Cliques:** o clique na pílula agora vale ao **soltar** o botão, para dar para arrastar. Com o painel aberto, o mouse vai direto para o app (seletores, cores e controles deslizantes funcionam). Dois cliques na pílula continuam abrindo a janela grande.
- As respostas que o JARVIS dá por outro caminho (voz "Jarvis, …", celular) também aparecem na conversa da ilha.

## 8.4.0 — 16 de novembro de 2026

**⚡ Modo leve, 🎙 voz pela Groq, 😴 brincadeiras do avatar e 👁 piscar liga/desliga (ideia 10)**
- **Modo leve** (Personalizar › Animações e desempenho): Automático, Sempre ligado ou Desligado.
  - Ligado: sem animações nem transições, o avatar só mexe a boca quando fala e a ilha atualiza mais devagar (a cada 3,5 s em vez de 1,2 s).
  - No Automático, liga sozinho quando o notebook está na bateria.
- **Voz pela Groq na ilha e no app do Windows:**
  - O 🎙 grava o pedido e para sozinho quando você para de falar. O limite do que conta como fala se ajusta ao ruído do ambiente, para pegar microfones baixinhos.
  - O PC manda o áudio para a Groq (Whisper, grátis com a mesma chave do Cérebro) e envia o texto ao JARVIS.
  - O áudio não é guardado, e a rota `/api/voice/transcribe` só atende este PC.
  - Sem a chave da Groq, aparece "conecte a Groq em Cérebro (IA)".
  - A tecla de atalho do app já começa a gravar.
- **Brincadeiras quando parado** (só visual, sem som): depois de 1 min 30 s sem mexer no PC, o avatar às vezes olha em volta, dá uma piscadinha ou boceja. Depois de 6 min, cochila com "zzz" e acorda quando você mexe. Dá para desligar, e o modo leve também desliga.
- **Piscar sozinho:** agora dá para desligar.

## 8.3.2 — 16 de novembro de 2026

**🔍 Revisão de erros antes do teste (ilha e interface nova) e os avisos do log**
- **Interface pronta no OneDrive:** a instalação renomeava a pasta `dist` inteira. Numa pasta do OneDrive isso dá "Acesso negado" no último passo, e o download falhava mesmo com tudo baixado. Agora:
  - troca **arquivo por arquivo**, com o `index.html` por último, e tenta de novo se o arquivo estiver preso;
  - apaga os arquivos antigos que sobraram;
  - o `curl.exe` do Windows não checa revogação do certificado (`--ssl-no-revoke`), que o antivírus costuma quebrar.
- **Dois cliques na pílula voltaram a abrir o JARVIS.** O 1º clique já abria os menus e o 2º caía dentro deles.
- **Foco da ilha sem apertar o Alt de mentira:** o jeito antigo podia abrir o menu do programa que estava na frente. Agora usa `AttachThreadInput`.
- **JARVIS bloqueado:** os menus da ilha mostram "🔒 O JARVIS está bloqueado. Toque aqui para desbloquear", em vez de "Erro 403".
- **Copiar pela ilha:** o JARVIS confere se o Windows separou a memória antes de copiar.
- **"Falha ao salvar cache de partidas: Acesso negado" (fan_cache.json):** nova gravação que resiste ao OneDrive (`core/safe_io.py`). Ela tenta de novo por um instante e, se o arquivo continuar preso, escreve por cima. Vale também para missões, rosto, PIN e perfis.
- **"Modo nuvem: não consegui sincronizar (SSL EOF)":** a sincronização usa uma conexão reaproveitada e tenta até 3 vezes (com pausas de 1,5 s e 4 s) antes de desistir da rodada.

## 8.3.1 — 16 de novembro de 2026

**📦 A interface nova chega no PC (a ilha nova não aparecia)**
- **O problema:** depois de atualizar, a interface nova não chegava no PC do Patrick, e a ilha continuava a antiga:
  - o download da interface pronta do site falhava;
  - a montagem no próprio PC leva mais de 10 minutos.
- **Corrigido:**
  - Quando o Python não consegue baixar do site (o antivírus corta a conexão segura dele: "SSL EOF" no log), o JARVIS baixa pelo **curl.exe do próprio Windows**, que usa a mesma conexão do navegador.
  - A interface pronta vale quando o PC está no **mesmo commit** que o site montou, mesmo que algum arquivo tenha mudado no PC (por exemplo, o `npm install` mexe no `package-lock.json`).
  - A montagem em segundo plano agora **espera a interface pronta do site por até 10 minutos** (o site leva 1 a 3 minutos para ficar pronto depois de uma versão nova) e só monta no PC se ela não vier.
  - A **ilha e a janela do app se recarregam sozinhas** quando a interface nova chega. A ilha recarrega fechada, e a janela recarrega escondida. Não precisa mais fechar e abrir o app.
  - Registro do download em `logs/prebuilt.log`.

## 8.3.0 — 16 de novembro de 2026

**🏝️ Menus direto na ilha, sem abrir o app (ideia 9)**
- **Clique na ilha:** ela **cresce para baixo** e vira um painel arredondado no topo da tela (440×560), como no vídeo. Em cima ficam os ícones dos menus e embaixo o conteúdo.
- **Primeira tela (Resumo do dia):** próximo lembrete, tarefas pendentes, missões e ofensiva 🔥, hábitos de hoje, a música tocando e o botão **🎙 FALAR**.
- **Menus na própria ilha:**
  - 💬 **Conversa:** escrever ou falar e ler a resposta ali mesmo;
  - ☰ **Tarefas:** ver, concluir e adicionar;
  - 🔔 **Lembretes:** ver, apagar e criar (com data, ou escrevendo "amanhã 9h dentista");
  - ♫ **Música:** capa grande, ⏮ ⏯ ⏭ e volume;
  - ⏱ **Timers:** os timers rodando e atalhos de 5, 10 e 25 minutos;
  - 🎯 **Missões:** missões do dia, ofensiva, FEITO e responder;
  - ◆ **Hábitos:** marcar os de hoje;
  - ⧉ **Copiados:** tocar copia de novo (pelo Windows, mesmo sem foco).
- **Fecha** ao clicar fora, no ✕, com Esc ou depois de 1 minuto parada. Dois cliques na pílula ou **🖥 ABRIR JARVIS** ainda abrem a janela completa. Com os menus abertos, cliques rápidos não abrem o JARVIS por engano.
- **Digitar na ilha:** ao abrir os menus, a ilha pega o foco do teclado. Tocar num campo só dá o foco, sem clicar.
- Tudo usa as mesmas rotas do Modo Desk: o que você faz na ilha aparece no app, na central e no celular.

## 8.2.4 — 16 de novembro de 2026

**🛠️ O Iniciar-JARVIS.bat volta a ligar o JARVIS (parava com "... foi inesperado neste momento")**
- **Corrigido:** desde a 8.1.5, uma frase de aviso do Iniciar-JARVIS.bat tinha um parêntese sem proteção: "(edge-tts)". O Windows lia esse `)` como o fim de um bloco e parava o arquivo logo depois do título, **antes de ligar o JARVIS**. Por isso as atualizações ficavam paradas em "Reiniciando" (90%) e o JARVIS não voltava nem abrindo o .bat na mão. O parêntese agora está protegido: `^(edge-tts^)`.
- **Novo teste** (`backend/tests/test_bat_syntax_824.py`): verifica todos os .bat do projeto e falha se aparecer um parêntese sem proteção dentro de um bloco, ou um .bat sem final de linha do Windows (CRLF).
- Os arquivos `Empacotar-Projeto.bat`, `Gerar-App-Android.bat` e `Iniciar-JARVIS-Rede.bat` passaram para o final de linha do Windows.

## 8.2.3 — 16 de novembro de 2026

**⚡ O JARVIS liga na hora depois de atualizar (não espera mais montar a interface)**
- **Corrigido:** depois de atualizar, o Iniciar-JARVIS.bat só ligava o JARVIS **depois** de montar a interface nova. No PC do Patrick isso levava de 7 a 12 minutos, e a tela ficava parada em "Reiniciando" (90%).
- **Agora:**
  - o JARVIS **liga em segundos** com a interface que já estava no PC;
  - a interface nova é montada em **segundo plano** (`scripts/build_background.py`, com registro em `logs/build.log`), sem rodar duas montagens ao mesmo tempo;
  - a central aberta pelo site não depende dessa montagem.
- Antes de tudo, continua tentando baixar a interface pronta do site, esperando no máximo 20 s no Iniciar e 45 s no botão ATUALIZAR.
- O botão ATUALIZAR não monta mais a interface antes de reiniciar.
- Só na primeira instalação, quando ainda não existe nenhuma interface montada, ela é montada antes de ligar.

## 8.2.2 — 16 de novembro de 2026

**⚡ Atualização em segundos: o PC baixa a interface pronta (não monta mais)**
- **Por que era lento:** a cada versão nova, o PC montava a interface (`npm run build`). Isso lê milhares de arquivos do `node_modules` e, numa pasta do OneDrive com o antivírus olhando cada arquivo, levava minutos. Isso valia tanto pelo botão ATUALIZAR quanto pelo Iniciar-JARVIS.bat.
- **Agora:** o site do JARVIS (Netlify) já monta a interface a cada versão. O PC **baixa ela pronta**: no teste, 65 arquivos em menos de 1 segundo.
  - Antes de baixar, confere que é a mesma versão do código que está no PC, pela "impressão digital" do código da interface.
  - Confere também o sha256 de cada arquivo e troca a pasta de uma vez. Se algo não bater, nada é trocado.
  - Logo depois de uma versão nova, o site leva 1 a 3 minutos para ficar pronto. O atualizador espera um pouco e, se mesmo assim não der, monta no PC como antes.
- Vale para o botão ATUALIZAR e para o Iniciar-JARVIS.bat.

## 8.2.1 — 16 de novembro de 2026

**⬆ Corrigido: atualização presa em "Montar a interface nova"**
- Na 8.1.7, a interface nova passou a ser montada com o JARVIS ainda ligado. No Windows, porém, o JARVIS esperava fechar a saída do processo de montagem, e um processo auxiliar dele mantinha essa saída aberta. Resultado: a atualização podia ficar parada até 10 minutos.
- Agora o JARVIS espera só a montagem terminar, e a saída dela vai para `logs/build.log`.
- Se a montagem passar de 4 minutos, ela é encerrada e o Iniciar-JARVIS.bat faz a montagem do jeito antigo.
- Depois de 2min30, a tela de atualização avisa o que fazer se demorar demais.

## 8.2.0 — 16 de novembro de 2026

**🧠 Cérebro automático grátis e 🤖 avatar mais estiloso (ideia 8 do documento de atualização, vídeo 5)**
- **⚡ Automático grátis** (Modo Desk › Cérebro (IA)): a **Groq**, que é grátis e muito rápida, responde como principal e o **Gemini** grátis fica de reserva.
  - Quando uma chega no limite do dia, ela fica de lado e a outra responde sozinha. Antes, com o Gemini grátis no limite de 20 pedidos por dia, o JARVIS ficava sem IA.
  - Pesquisa no Google e imagens da câmera vão primeiro para o Gemini, que sabe fazer isso.
  - No topo aparece "✓ Funcionando no automático grátis".
  - "Eu escolho a IA" continua disponível, agora também com a Groq.
- **🔑 Conectar as IAs grátis:** um cartão para a Groq e outro para o Gemini, com o passo a passo, o link e o campo **Cole a chave aqui**.
  - A chave é salva **só no `.env` deste PC**: não vai para a nuvem, não aparece de novo na tela e não entra no log.
  - Só dá para colar no próprio PC, com a central liberada.
  - Ao conectar a Groq, o Automático grátis já liga.
  - **TESTAR ESTA IA** mostra qual IA respondeu e em quanto tempo.
- **🤖 Avatar mais estiloso:**
  - **Visual:** bochechas rosadas, olhos maiores, reflexo no visor e sombra suave.
  - **7 expressões novas:** Repouso, Rindo, Carinho (com coraçãozinho), Descolado, Bravo, Chorando (com lágrimas) e Conseguiu (olhos de estrela).
  - **Acessórios novos:** Auréola, Chifrinhos, Chapéu de festa, Flor e Boné do time, mais o liga/desliga da **Antena**.
  - **Personalizar:** a prévia ficou bem maior, com todas as expressões em botões.
- **👀 Jeito de ser › Olhos seguem o mouse**, com a velocidade ajustável (0,25x a 2x). Dá para desligar.
- **Corrigido:** um teste de contagem regressiva quebrava conforme a data do dia.

## 8.1.7 — 16 de novembro de 2026

**⬆ Atualização mais rápida e tela nova de ATUALIZANDO**
- **Mais rápido:**
  - O aviso por voz não segura mais o reinício (antes esperava a fala inteira, e com a voz falhando a tela parava em "Preparando").
  - A interface nova agora é montada com o JARVIS ainda ligado. Antes era montada depois de desligar, com o JARVIS fora do ar por mais tempo.
  - A montagem ficou mais leve: não calcula mais o tamanho compactado de cada arquivo.
- **Tela nova de atualização**, com as etapas de verdade vindas do PC:
  - ⬇ Baixar a versão nova;
  - 🧩 Montar a interface nova;
  - ⟳ Reiniciar os sistemas;
  - ✓ Abrir a versão nova.
- A tela também mostra o tempo passando, de qual versão para qual e **O QUE MUDOU**.

## 8.1.6 — 16 de novembro de 2026

**🏝 App para Windows: fim do "Python não está respondendo" e da ilha que não respondia**
- **Corrigido:** a causa de verdade da ilha não responder e do app travar estava na ponte entre a página e o Windows.
  - O pywebview entrega à página tudo o que é público nessa ponte, entrando em cada objeto.
  - A ponte guardava as próprias janelas, então ele saía varrendo os objetos internos do Windows. A janela travava ("Python não está respondendo") e a página ficava sem as funções: abrir, falar, sair, mudar o tamanho da ilha.
  - Isso acontecia desde a 8.0.
  - Agora a ponte só expõe as funções, e o estado fica escondido.
- Um teste novo garante que a ponte nunca mais exponha nada além de funções.

## 8.1.5 — 16 de novembro de 2026

**🔊 Voz de volta e ⬆ ATUALIZAR no Modo Desk**
- **Corrigido: o JARVIS parou de falar.**
  - Causa: a biblioteca da voz da Microsoft (edge-tts) instalada no PC era antiga. A Microsoft mudou o serviço e ela passou a receber "No audio was received" e "403".
  - O Iniciar-JARVIS.bat só instalava dependências que faltavam, então ela nunca era atualizada.
  - Agora ele confere a versão e atualiza sozinho (edge-tts 7.3 ou mais nova).
- **Voz reserva:** se a voz da Microsoft não responder (sem internet ou com o serviço fora), o JARVIS fala com a voz do próprio Windows em vez de ficar mudo. Na próxima fala, ele tenta a voz normal de novo.
- **⬆ ATUALIZAR no Modo Desk.** Antes o botão só existia na central clássica e no bloqueio. Agora aparece em três lugares:
  - um aviso no Início quando tem versão nova;
  - o botão **⬆ ATUALIZAR** com o número de mudanças na barra lateral;
  - a seção **Configurações › Atualizações**, com a versão atual, o que mudou, **VERIFICAR AGORA** e **ATUALIZAR AGORA**.

## 8.1.4 — 16 de novembro de 2026

**🏝 Ilha do app para Windows: clique e recorte que não dependem do .NET**
- **Corrigido:** a ilha continuava sem responder ao clique e sem o formato de pílula, com cantos de retângulo.
  - O app procurava a janela da ilha por um caminho do .NET que podia falhar fora da linha principal, e o erro era engolido em silêncio.
  - Agora ela é achada pelo título, direto no Windows, com tipos de 64 bits corretos.
  - O recorte em pílula é refeito depois que a janela existe de verdade.
- **Dois cliques na ilha** abrem a janela do JARVIS pelo próprio app, mesmo que a página da ilha não responda.
- **⏻ Sair do app** também na barra lateral do Modo Desk, no app para Windows.
- O registro `%APPDATA%\JARVIS\app.log` agora anota cada passo: recorte, cliques, modo da ilha e abertura da janela.

## 8.1.3 — 16 de novembro de 2026

**🏝 App para Windows: abre só pela ilha, e o clique na ilha é garantido**
- **A janela do JARVIS só aparece quando você pede pela ilha:**
  - pelo botão **🖥 ABRIR JARVIS** do cartão;
  - com **dois cliques** na pílula;
  - pela tecla de atalho para falar.
- Ao abrir o app, aparece só a ilha no topo da tela.
- Fechar a janela no **X** só a esconde; a ilha continua.
- Para sair de vez, use **⏻** no cartão da ilha. O JARVIS continua rodando no PC.
- **Corrigido:** em alguns PCs, o WebView2 de uma janela pequena, sem moldura e sempre no topo não recebia o mouse.
  - Agora o app também percebe o clique pelo Windows, quando o botão do mouse desce em cima da ilha, e repassa para ela.
  - O clique não conta duas vezes.
- **Corrigido:** a ilha ficava esticada com 100 px de altura, que é o tamanho mínimo padrão de janela do pywebview.
- **Diagnóstico:** o app grava um registro em `%APPDATA%\JARVIS\app.log` (cliques na ilha e erros), para investigar se algo ainda falhar.

## 8.1.2 — 16 de novembro de 2026

**🏝 Ilha do app para Windows: agora dá para clicar (e ela abre, como a ilha dinâmica)**
- **Corrigido:** o clique na ilha passava direto para o que estava atrás.
  - Causa: a janela usava a "transparência por cor-chave" do Windows, que com o WebView2 deixa a janela atravessável.
  - Agora a janela é normal e o Windows recorta o formato de pílula, então a ilha inteira é clicável.
- **Clicar abre a ilha num cartão**, que cresce para os dois lados e continua centralizada:
  - o avatar, o estado e a hora;
  - a música com a capa e os botões ⏮ ⏯ ⏭;
  - a última resposta do JARVIS;
  - **🎙 FALAR**, que abre o JARVIS já ouvindo;
  - **🖥 ABRIR JARVIS**.
- O cartão fecha no ✕, ao clicar fora dele ou sozinho depois de uns segundos sem mexer.
- Ao passar o mouse, a pílula acende na cor do app.
- Para aparecer: feche o app e abra de novo pelo atalho **JARVIS**. Não é preciso rodar o Gerar-App-Windows.bat de novo.

## 8.1.1 — 15 de novembro de 2026

**🛡 App para Windows sem alerta de vírus (McAfee)**
- **Corrigido:** o McAfee acusava o JARVIS.exe como vírus. Era um falso positivo. O exe era montado pelo PyInstaller no modo "arquivo único", e esse tipo de exe novo e sem assinatura, que se descompacta na pasta TEMP e liga programas com a janela escondida, é exatamente o que os antivírus vigiam.
- **Agora não existe mais JARVIS.exe.** O **Gerar-App-Windows.bat** instala o atalho **JARVIS** na Área de Trabalho e no Menu Iniciar, com o ícone do robô.
  - O atalho abre o app com o **pythonw.exe oficial do Python**, assinado pela Python Software Foundation e conhecido pelos antivírus.
  - Continuam iguais: a janela própria, a ilha no topo e a tecla para falar.
  - Não é preciso desativar o antivírus.
- Quando o app liga o JARVIS sozinho, a janela do Iniciar-JARVIS aparece minimizada em vez de escondida.
- **⬇ APP PARA WINDOWS** agora mostra se o app está instalado e tem o botão **▶ ABRIR O APP DO JARVIS**, que funciona no próprio PC.
- O instalador apaga o JARVIS.exe antigo.

## 8.1.0 — 15 de novembro de 2026

**🎯 Missões, 🔥 Ofensiva e guarda-roupa do robô (ideia 7 do documento de atualização)**
- **👕 Guarda-roupa** em Modo Desk › Personalizar, com abas e prévia de cada item:
  - **Chapéus:** gorro de Natal, boné, fone, cartola, tiara de gatinho, chapéu de bruxa, headset e coroa.
  - **Rosto:** óculos, laço, bigode e óculos escuros.
  - **Roupas:** cachecol, gravata-borboleta, camisa do time, capa de herói e colete de armadura.
  - **Olhos:** arco-reator, coração, estrela e pixel.
  - **Efeitos:** brilho, neve e faíscas.
  - Itens bloqueados mostram 🔒 e como liberar ("Nível 5", "7 dias de ofensiva").
  - O acessório escolhido no 8.0 passa sozinho para o chapéu ou o rosto.
- **🎉 Temas das datas** (dá para desligar), por cima do visual escolhido, que volta depois da data:
  - Natal (1 a 26/12): gorro e neve.
  - Halloween (25 a 31/10): abóbora.
  - Carnaval: confete.
  - Dia de jogo do Palmeiras: camisa do time.
- **🎯 Missões** (seção nova e cartão no Início): todo dia 3 missões novas, sem repetir as de ontem:
  - **usar o JARVIS:** completa sozinha quando você faz (conversar, concluir tarefa, criar lembrete, rodar rotina, abrir o Holograma ou o Olho de Deus…);
  - **sobre você:** uma pergunta respondida ali mesmo; a resposta vai para a memória;
  - **bem-estar:** beber água, alongar, caminhar… você marca FEITO.
  - Mais o **🏆 desafio da semana** (150 XP).
- **🔥 Ofensiva:** dias seguidos com pelo menos 1 missão feita, com o recorde. Aparece na barra lateral e na seção Missões.
  - **🛡 Protetor:** você ganha 1 por semana e guarda até 2. Se perder um dia, o protetor segura a ofensiva.
- **🎁 Aviso de item novo:** quando subir de nível ou bater um recorde, aparece "Item novo liberado: capa de herói!".
- **Por voz:** "quais são minhas missões?" e "como está minha ofensiva?".
- **Fora de casa (nuvem):** ver as missões e a ofensiva e marcar as de bem-estar; o PC aplica na sincronização.

## 8.0.1 — 15 de novembro de 2026

**🖥 Modo Desk e JARVIS.exe: botões que faltavam**
- **Corrigido:** no bloqueio, o 🖥 MODO DESK só ligava o modo e nada mudava na tela. Agora o botão **🖥 ENTRAR NO MODO DESK** já começa a entrada (rosto ou PIN), e a central abre no Modo Desk. Com ele ligado, o botão mostra **MODO DESK: LIGADO**; tocar de novo desliga.
- **⬇ APP WINDOWS** agora aparece também na central clássica (ao lado do 🖥 MODO DESK), no ⚡ CONTROLES (APP PARA WINDOWS) e na barra lateral do Modo Desk (⬇). Antes ficava só em Modo Desk › Ilha e no bloqueio.

## 8.0.0 — 15 de novembro de 2026

**🖥 JARVIS 8: Modo Desk, o JARVIS como app de assistente pessoal (ideia 6 do documento de atualização)**
- **Botão 🖥 MODO DESK** (na central, no ⚡ CONTROLES e no bloqueio): um layout novo, inspirado nos vídeos do Patrick. A central clássica continua a um toque (◐ CENTRAL CLÁSSICA). O aparelho lembra a escolha.
  - Barra lateral com o avatar, o estado (Pronto, Ouvindo, Pensando, Falando) e o nível.
  - Seções: Início, Conversa, Memória, Tarefas, Lembretes, Hábitos, Timers, Música, Copiados, Rotinas e Meu PC.
  - Configurações com busca: Personalizar, Cérebro (IA), Funções, Voz, Ilha, Celular e agendas, Proteção com rosto e Atalhos.
  - **Início:** "Boa noite, Patrick!", falar ou escrever, a conversa, a música e os contadores de lembretes, tarefas e hábitos.
- **🤖 Avatar robô JARVIS:**
  - cabeça arredondada, visor escuro e olhos de luz em forma de arco-reator;
  - reage sozinho: ouvindo, pensando e falando (e pisca);
  - **Personalizar:** cor do corpo, do visor e dos olhos; expressão (feliz, pensando, falando, ouvindo, dormindo, surpreso, piscando); acessório (fone, óculos, gorro de Natal, coroa); o nome; e a **cor principal do app** (ciano, verde-limão, roxo, laranja… ou qualquer cor).
- **🧠 Cérebro (IA):** escolher a IA em cartões, ver se ela chegou no limite e **TESTAR ESTA IA** (a resposta e o tempo).
- **🧩 Funções:** catálogo do que dá para falar, com exemplos que testam com um toque, e os seus atalhos ("abre o meu trabalho").
- **🖥 Meu PC:** a verificação do PC com o avatar no centro do anel.
- **Recursos novos:**
  - **◆ Hábitos:**
    - marque o dia e veja a sequência (🔥) e os últimos 7 dias;
    - lembrete no horário;
    - por voz: "marquei o treino de hoje", "como estão meus hábitos?";
    - fora de casa, dá para marcar pelo celular.
  - **⧉ Copiados:**
    - o que você copia no PC (Ctrl+C) fica num histórico (as últimas 50), para copiar de novo com um toque;
    - fica só no PC; o que parece senha, cartão, chave ou código não é guardado;
    - dá para pausar e apagar.
  - **⭐ Nível e XP:** o JARVIS ganha XP com conversas, tarefas feitas, hábitos, rotinas, lembretes e memórias (com teto por dia) e sobe de nível.
  - **✳ Memória em mapa:** você no centro, os assuntos em volta (Pessoas, Gostos, Casa, Trabalho, Saúde, Dinheiro…) e cada memória ligada ao seu assunto. Tocar mostra a memória e dá para esquecer; o campo embaixo guarda uma nova.
- **⬇ JARVIS.exe, o app para Windows** (no bloqueio e em Modo Desk › Ilha):
  - **Gerar-App-Windows.bat** monta o executável no seu PC, uma vez, e cria o atalho "JARVIS" na Área de Trabalho;
  - janela própria com o Modo Desk;
  - **a ilha no topo da tela**, sempre visível: o avatar e a hora, a música tocando e as respostas do JARVIS. Tocar nela abre a janela;
  - **tecla para falar** de qualquer lugar (PageDown, F9 ou Ctrl+Espaço, em Ilha);
  - se o JARVIS estiver desligado, o app liga sozinho;
  - na janela do app, para falar, diga "Jarvis, …" (o ouvido do PC atende) ou escreva.

## 7.14.2 — 15 de novembro de 2026

**📱 App Android: sem a página de erro "Página da Web não disponível"**
- **Corrigido:** quando o PC não respondia na rede de casa, o app podia mostrar a página de erro do Android ("net::ERR_CONNECTION_TIMED_OUT") e ficar nela. Agora:
  - antes de abrir o PC, o app confere também se a **tela** da central responde (porta 5443 ou 5173), não só o backend;
  - se a central do PC não abrir em **15 segundos**, o app cancela e vai para o **modo nuvem** (e continua conferindo o PC em segundo plano, como antes).
- Para receber no celular: rode **Gerar-App-Android.bat** no PC; o celular se atualiza a partir do PC.

## 7.14.1 — 15 de novembro de 2026

**📱 Correções no celular**
- **Corrigido:** no celular fora de casa (modo nuvem), o 🔒 BLOQUEAR levava ao bloqueio de rosto do PC, que não funciona longe do notebook. O celular ficava preso em "isso precisa do notebook ligado". Agora bloquear pede o **PIN da nuvem** de novo.
- **Corrigido:** na Central de Agentes, no celular, o botão 🗑 LIMPAR CONVERSA ficava por cima da conversa.

## 7.14.0 — 15 de novembro de 2026

**🔒 Bloqueio: volta o layout clássico, com a verificação nova**
- A pedido do Patrick, o bloqueio voltou a ser o **clássico**, mas a identificação facial é a nova:
  - durante a verificação, o rosto aparece num círculo com a máscara de pontos, a varredura e "ESCANEANDO · %";
  - ao reconhecer, o anel fica verde: **IDENTIDADE CONFIRMADA**.
- O estilo ORBE continua como opção: no bloqueio, botão **◐ ESTILO**.
- Corrigido: no ⚙ GERENCIAR HUB do estilo ORBE, os textos do carimbo ficavam por cima dos botões.

**✨ Holograma, parte 2 (ideia 5)**
- **❓ Perguntar no meio da apresentação:** "espera, o que é horizonte de eventos?" (por voz) ou pelo botão ❓.
  - A apresentação pausa e a resposta aparece num balão, também falada.
  - Depois ela continua da mesma cena.
- **🧠 Quiz no final:** 3 perguntas de múltipla escolha sobre o que foi mostrado.
  - Responda tocando ou falando "letra B".
  - Tem placar e a explicação de cada resposta.
- **⭐ Salvar e rever:** ☆ SALVAR guarda a apresentação ou a receita (até 30), e rever não gasta IA.
  - "hologramas salvos" ou ⚡ CONTROLES › HOLOGRAMAS SALVOS abre a lista; apagar pede confirmação.
  - Os salvos vão para a nuvem, para rever no celular fora de casa.
- **Cartão animado nas perguntas rápidas**, no canto, que some sozinho:
  - **placar** ("quem ganhou o jogo?");
  - **número com mini-gráfico** ("quanto está o dólar?" mostra a semana);
  - **foto + fato** e **lista curta**.
  - ▶ VER NO HOLOGRAMA abre a apresentação completa.

## 7.13.0 — 15 de novembro de 2026

**✨ Holograma com animação em cada cena (ideia 5, parte 1)**
- **Cada cena ganha a animação certa** (a IA escolhe; sem dado confiável, a cena fica como antes):
  - 📊 **gráficos** que crescem na tela: barras ou linha, com os valores (preços, população, recordes);
  - 🕰 **linha do tempo** que acende cada data e marco;
  - 🌍 **mapa**: o globo neon do Olho de Deus voa de lugar em lugar, com marcadores e rota tracejada;
  - 🪐 **ciência**: Sistema Solar girando, átomo, ciclo da água, coração batendo, camadas da Terra, DNA e célula.
- **Fotos reais nas cenas** (Wikipédia), com o crédito embaixo.
- **🔈 Trilha ambiente** baixinha, gerada no próprio aparelho (sem música de terceiros):
  - abaixa quando o JARVIS fala;
  - o botão TRILHA liga e desliga, e a escolha fica lembrada;
  - no celular começa desligada.
- Funciona igual fora de casa (nuvem).
- **Corrigido:** no celular, tocar num botão do Holograma podia empurrar a tela para o lado.

## 7.12.0 — 15 de novembro de 2026

**🔵 Tela de bloqueio nova, igual ao vídeo (estilo ORBE)**
- **Orbe de linhas entrelaçadas** no centro de um azul royal com grade. As linhas ondulam e giram, com pontos de energia correndo por elas, e reagem ao estado:
  - **EM ESPERA**: respira devagar;
  - **OUVINDO**: abre um pouco;
  - **FALANDO**: pulsa como voz;
  - **ESCANEANDO**: gira mais rápido.
- O estado aparece em cima, com a linha pontilhada animada.
- **Identificação facial dentro do orbe**: a câmera aparece num círculo, com a máscara de pontos, a linha de varredura e "ESCANEANDO · 40%". Quando reconhece, fica verde: **IDENTIDADE CONFIRMADA**.
- **Cartões passando numa faixa** (sistemas, relógio, clima, mercado, manchete, Spotify, água…). Param quando o mouse passa por cima, e tocar num cartão abre os detalhes, como antes.
- Botão redondo embaixo para entrar (ou espaço, ou palmas, como antes).
- **Todas as funções continuam**, guardadas no **⚙ GERENCIAR HUB** (no topo):
  - PIN, visitante, nova pessoa e atualizar;
  - Branding, Otimizar, Notas e Diagnóstico;
  - fundo, áudio, Modo Torcedor e alterar a foto do rosto.
- Quando o rosto não é reconhecido, USAR PIN e CRIAR PERFIL aparecem na hora, fora do hub.
- Quer o bloqueio antigo? ⚙ GERENCIAR HUB › **◐ ESTILO** troca entre ORBE e CLÁSSICO (vale para este aparelho).
- No celular: menos linhas e animação mais leve.

## 7.11.1 — 15 de novembro de 2026

**🌐 Olho de Deus: visual novo e sem chave de mapa**
- **Corrigido:** o mapa escuro do globo passou a pedir chave ("API KEY REQUIRED"). Agora o globo é desenhado no próprio JARVIS, sem nenhuma chave:
  - oceano azul, continentes e contornos em neon, com brilho de atmosfera;
  - ao aproximar, aparecem as ruas;
  - a visão satélite continua.
- **🚀 Lançamentos de foguetes** (nova camada): os próximos e os mais recentes do mundo inteiro, na base de lançamento (dados públicos do The Space Devs). Toque num lançamento e abre um cartão com:
  - foto, situação (confirmado, sucesso, falhou), foguete, empresa, órbita, base e chance de tempo bom;
  - botões ▶ ASSISTIR e ↗ SITE.
- "Qual o próximo lançamento de foguete?" responde e abre o globo nessa camada.
- Aviões e queimadas com cores mais fortes, como no vídeo.

## 7.11.0 — 15 de novembro de 2026

**🌐 Olho de Deus com globo 3D e dados reais (ideia 4 do documento de atualização)**
- **Globo 3D de verdade** no lugar do desenho: gira, dá zoom até a rua e voa até a sua cidade. Visão escura (HUD) e satélite; 🌍 MUNDO, 🏠 MINHA CIDADE e 📍 ONDE ESTOU. O trânsito do Waze continua na aba 🚦.
- **Camadas ao vivo, de fontes públicas e sem chave** (cada uma liga e desliga e mostra quando atualizou):
  - ☁ **radar de chuva** das últimas 2 h, animado (RainViewer), e o gráfico da chuva das próximas 3 h na cidade (Open-Meteo);
  - ✈ **voos** num raio de 150 km: voo, modelo, altitude, velocidade e rumo (ADS-B público), a cada 15 s;
  - 🌎 **terremotos** das últimas 24 h no mundo (USGS), o tamanho mostra a força;
  - 🔥 **queimadas** no Brasil nas últimas 24 h (INPE), com quantas estão a menos de 50 km;
  - 🛰 **Estação Espacial**: onde está agora, a órbita e as próximas passagens visíveis no seu céu, com a previsão de nuvens.
- **Toque num ponto** (avião, terremoto, foco de fogo, ISS) e aparece um cartão com os detalhes.
- **Faixa "o que está acontecendo"** no topo: "Sem chuva nas próximas 3 h · 42 voos por perto · ISS passa visível hoje às 19:42".
- **Avisos automáticos** (voz no PC e notificação no celular), cada um com botão para desligar no painel:
  - chuva forte chegando ("em uns 30 minutos");
  - queimada a menos de 50 km ou terremoto de força 5 ou mais na América do Sul;
  - Estação Espacial visível, 10 minutos antes, só com céu limpo.
- **Voz**: "mostra os voos agora", "tem terremoto hoje?", "tem queimada perto?", "quando a estação espacial passa?". O JARVIS responde e abre o globo na camada certa.
- **Fora de casa** funciona igual, pela nuvem. Os avisos saem do PC.
- Saíram as categorias sem dados (navios, Starlink, câmeras, rádios) e os leitores de placa (privacidade).
- No celular: menos pontos e animação mais leve.

## 7.10.0 — 15 de novembro de 2026

**💰 Agente de finanças completo: controle de dívidas (ideia 3.1 do documento de atualização)**
- **Dívidas e parcelamentos**: credor, saldo, parcelas (7 de 12), valor da parcela, juros ao mês e dia do vencimento. "Paguei a parcela do carro", "paguei R$ 500 a mais", "quitei o empréstimo": o saldo cai e o histórico fica guardado.
- **Contas fixas do mês**: aluguel, luz, internet…, com vencimento, "paga" em cada mês e o que falta pagar.
- **Cartão de crédito**: fechamento e vencimento; compras à vista ou parceladas caem nas faturas certas ("quanto está minha fatura?").
- **Orçamento e metas**: limite por categoria, com aviso a 80% e 100%; metas como a reserva de emergência.
- **Plano para sair das dívidas**: compara "menor dívida primeiro" × "maior juros primeiro" (em quantos meses quita e quanto paga de juros), simula um valor extra por mês e recomenda um, dizendo qual dívida atacar primeiro.
- **Avisos 3 dias antes e no dia** do vencimento (dívidas, contas e faturas), por voz no PC e notificação no celular. Avisa também de orçamento estourando e de conta atrasada.
- **Painel na aba 💰 da Central de Agentes**:
  - total devido, parcelas por mês, a pagar no mês e atrasados;
  - próximos vencimentos com ✓ PAGO;
  - cada dívida com barra de progresso e PAGAR PARCELA;
  - contas do mês, faturas do cartão, orçamento, metas e o plano com controle de "quanto posso pagar a mais".
- **Segurança**:
  - tudo fica só no PC;
  - quitar, apagar, mudar dados de uma dívida e pagamentos acima de R$ 1.000 pedem **✓ CONFIRMAR**;
  - **fora de casa** o celular vê só o **resumo** e **anota** gastos e pagamentos, que o PC aplica na sincronização.
- Central de Agentes: abas não encolhem mais e, no celular, tudo cabe na largura da tela.

## 7.9.0 — 15 de novembro de 2026

**Conversa direta com os agentes (ideia 3 do documento de atualização)**
- **Seis agentes**, cada um especialista e só com os dados da área dele:
  - 🧭 `@rotas`;
  - 🔎 `@pesquisa`;
  - 🛒 **`@mercado`** (novo): lista de compras, receitas com o que tem em casa e quantidades;
  - 💰 **`@financas`** (novo): anota gastos e entradas e resume o mês por categoria;
  - 📅 **`@secretario`** (novo): agenda, lembretes e tarefas num lugar só;
  - 🧠 **`@professor`** (novo): explica matérias, abre o Holograma e faz perguntas tipo prova.
- **Três jeitos de falar com eles**:
  - **Central de Agentes**, agora com **uma aba por agente**;
  - **`@` no campo de conversa** (aparece a lista dos agentes; a mensagem vai só para o escolhido e a resposta vem com o ícone dele);
  - **voz**: "agente mercado, monta a lista da semana", "pergunta pro agente de finanças quanto gastei", "fala com o professor: me explica frações".
- **Memória por agente**: cada um lembra as últimas 30 mensagens (salvas no PC). Um não vê a conversa do outro, e o **LIMPAR** apaga só a daquele agente.
- **Ações**:
  - as simples acontecem na hora e aparecem na resposta (✓ adicionado, ✓ anotado);
  - as maiores (tirar os comprados da lista, concluir tarefa, mais de 8 itens) esperam o **✓ CONFIRMAR**;
  - um agente não consegue fazer ações de outra área.
- **Fora de casa** (nuvem): Mercado, Secretário (lembretes e tarefas) e Professor. Finanças, Rotas e Pesquisa pedem o PC ligado.
- Valores em reais no padrão brasileiro (R$ 1.234,50).

## 7.8.0 — 15 de novembro de 2026

**Foto da galeria (ideia 1 do documento de atualização)**
- **Três jeitos de mandar uma foto**: 🖼 **GALERIA** na janela da câmera, **📎** no campo de conversa e **arrastar a imagem** para a central no PC ("SOLTE A IMAGEM AQUI").
- **Antes de sair do aparelho**, a foto é reduzida (no máximo 1600 px) e regravada: isso **apaga a localização (GPS)** e os outros dados escondidos (no teste, 164 KB viraram 33 KB, sem o GPS).
- **Janela FOTO ENVIADA** com pergunta opcional e 4 botões (com uma pergunta escrita, o JARVIS escolhe sozinho):
  - **🔍 ANALISAR**: o diagnóstico da câmera (o que é, detalhes, dicas e alertas);
  - **📄 LER E AGIR**: lê o texto e **sugere** ações (receita → lista de compras, conta → lembrete no vencimento, cartão de visita → contato, lista escrita → tarefas). **Nada acontece sem o CONFIRMAR**, e o PC confere a ação de novo antes de fazer;
  - **🌐 PESQUISAR**: identifica o item e pesquisa preço, onde comprar e avaliações, com as **fontes**;
  - **✦ HOLOGRAMA**: identifica o assunto e abre a apresentação animada com **a sua foto no fundo**.
- **Segurança**:
  - a foto **nunca é gravada** (nem no PC, nem na nuvem, nem nos registros);
  - só com a central desbloqueada, no máximo 10 fotos por minuto por aparelho;
  - a IA é instruída a **não obedecer textos escritos na foto**.
- **Fora de casa** funciona pela nuvem, sem guardar nada. Lá a pesquisa é uma estimativa da IA (sem busca ao vivo) e salvar contato fica só com o PC ligado.

## 7.7.0 — 15 de novembro de 2026

**Segurança, parte 2: conexão criptografada (https) na rede de casa** (ideia 2 do documento de atualização)
- **Liga em Configurações › Segurança › LIGAR HTTPS** (só pela tela do PC; o JARVIS reinicia sozinho). Começa **desligado**, para nada mudar até você ativar.
- O JARVIS cria o **próprio certificado** ("JARVIS · rede de casa") e o do PC para os endereços dele na rede, e refaz sozinho quando o endereço muda.
- Com https ligado:
  - celulares, tablets e TVs entram por **https://IP-DO-PC:5443** (backend na 8443);
  - **a chave de acesso e o PIN nunca viajam por http** na rede (o PC recusa com "abra por https");
  - quem abrir o endereço antigo (http …:5173) é levado para o https;
  - o QR code e o pareamento do app passam a usar https.
- **Este PC continua em http://127.0.0.1** (não sai do computador): a central do PC e o site do Netlify não mudam.
- **Página do certificado** (no celular: http://IP-DO-PC:8000/api/mobile/certificado), com o passo a passo para Android e iPhone e a impressão digital para conferir.
- **App Android**: passa a confiar no certificado instalado pelo dono e entende as portas https. É preciso **gerar o APK de novo** (Gerar-App-Android.bat).
- **🩺 Diagnóstico** avisa quando há aparelhos conectados e o https está desligado.
- `Iniciar-JARVIS.bat` sobe o backend pelo novo `run_server.py` (o mesmo backend, mais o https quando ligado) e instala a biblioteca do certificado (`cryptography`).

## 7.6.0 — 15 de novembro de 2026

**Segurança (ideia 2 do documento de atualização, parte 1)**
- **Uma chave por aparelho**: o QR code virou só a "chave de pareamento". Cada celular, tablet, TV ou outro PC pede a **própria chave** ao abrir o JARVIS, e ela fica guardada só nele (o PC guarda apenas uma impressão dela).
- **Aparelho novo precisa da sua aprovação**: depois de escanear o QR, ele mostra "AGUARDANDO APROVAÇÃO" e o PC mostra um cartão **PERMITIR / RECUSAR** (e avisa por voz). Só a tela do próprio PC aprova. O pedido expira em 2 minutos.
- **Migração sem dor**: nos primeiros 14 dias, os aparelhos que já usavam o JARVIS ganham a própria chave sozinhos, sem escanear de novo. Dá para encerrar antes em Configurações > Segurança.
- **Configurações > Segurança**: aparelhos conectados (último acesso e endereço) com **REMOVER**, **DESCONECTAR TODOS E TROCAR O QR CODE**, e o que aconteceu nas últimas 24 h.
- **Tentativas suspeitas**: 5 erros (chave errada, aparelho removido tentando voltar ou PIN do pareamento errado) em 10 minutos **bloqueiam aquele aparelho por 15 minutos**, e o tempo dobra a cada nova vez. O JARVIS **avisa por voz no PC**, manda **notificação para o celular** e registra no 🩺 Diagnóstico. O PIN da tela de bloqueio travado também gera o aviso.
- **Tela de bloqueio**: ⚡ Otimizar e 🩺 Diagnóstico rodam no máximo 1 vez por minuto enquanto a central está bloqueada.
- **🩺 Diagnóstico** ganhou o item **Segurança**: alertas das últimas 24 h, aparelhos sem uso há mais de 30 dias e migração ligada.
- A conexão criptografada (https) na rede de casa fica para a **parte 2**.

## 7.5.0 — 14 de novembro de 2026

- **Erro de voz no holograma corrigido** ("No audio was received"): o serviço de voz da Microsoft às vezes responde sem áudio quando várias falas são pedidas em sequência. Agora a voz **tenta de novo** sozinha (até 2 vezes), ignora pedaços sem nada para falar (só emoji/pontuação) e, se mesmo assim falhar, avisa em português em vez da mensagem técnica em inglês.
- **Holograma mais animado**:
  - constelação de partículas no fundo, que acelera enquanto o JARVIS fala;
  - feixe de projetor e uma esfera holográfica 3D girando atrás da cena;
  - **ondas de voz** que pulsam só enquanto ele fala, e o ícone ganha órbitas com pontos de luz;
  - títulos que se "decodificam" letra por letra; cada cena **liga como um holograma** e a anterior se dissolve;
  - número em destaque com anel medidor; tópicos chegando de lados diferentes;
  - carregamento com barra de varredura.
- **Receita viva mais animada**: faíscas ao marcar um ingrediente, comemoração "TUDO SEPARADO!", anel de progresso do passo, entrada do passo pela direção certa, aviso de último passo e o botão do timer pulsando.
- **Sem pausa entre as cenas**: as falas do holograma são geradas antes (enquanto a primeira cena aparece).
- O cartão da resposta anterior (ex.: clima) não fica mais junto quando o holograma abre.

## 7.4.1 — 13 de novembro de 2026

- Central: os atalhos **◉ OLHO DE DEUS · 🤖 AGENTES · 📘 BRANDING · 🩺 DIAGNÓSTICO** saíram de cima do orbe (ficavam no meio dele, quase invisíveis) e agora ficam **logo abaixo do orbe**, como botões mais legíveis. No celular continuam em CONTROLES.

## 7.4.0 — 13 de novembro de 2026

- **🩺 DIAGNÓSTICO** (tela de bloqueio, ao lado do Olho de Deus, CONTROLES, perfil ou "Jarvis, roda um diagnóstico"): testa de verdade a IA (pergunta mínima, mede o tempo), a voz (gera um áudio), a internet, a sincronização com a nuvem, o espaço em disco, os arquivos de dados, os erros das últimas 24 h e, no aparelho, a conexão com o PC, o tempo real, a versão da tela e do PC, o microfone, a câmera e a fluidez. Cada item diz ok / atenção / falha e **o que fazer**. "COPIAR RELATÓRIO" copia tudo em texto (sem dados pessoais).
- **Varredura completa antes da apresentação**:
  - **Esc não fechava** as janelas novas (Agentes, Branding, Notas, Otimizar, Olho de Deus, perfil) quando um botão estava focado, e ainda mostrava "Ação cancelada". Agora o Esc fecha a janela de cima e não cancela nada;
  - o **Otimizar** podia ligar o Modo leve por uma medição feita com a tela ainda carregando: agora confirma com uma segunda medição;
  - o **Holograma** não pega mais pedidos pessoais ("me fala sobre minha agenda", "como funciona meu alarme");
  - tela de bloqueio no celular: o título **J.A.R.V.I.S.** cortava nas laterais e o rodapé cobria o cartão do Spotify;
  - o botão de entrar podia usar um microfone antigo depois de trocar o microfone no bloqueio;
  - novo teste automático que chama **todas as 73 rotas** do PC e garante que nenhuma dá erro interno.

## 7.3.0 — 13 de novembro de 2026

- **📝 NOTAS DA VERSÃO**: botão na tela de bloqueio, em CONTROLES e no menu do perfil (ou "Jarvis, o que mudou?" / "novidades"). Mostra todas as versões do JARVIS com a data e cada detalhe do que mudou, com busca (ex.: "câmera", "trânsito", "voz") e a marca **INSTALADA** na versão que está rodando. No celular, lista e detalhe ficam em telas separadas.
- Depois de cada atualização, as notas abrem **sozinhas uma vez**, já na versão nova (marcada como **NOVA**).
- As notas são o próprio histórico do projeto (CHANGELOG.md), então estão sempre em dia com o que foi publicado.

## 7.2.0 — 13 de novembro de 2026

- **JARVIS mais rápido**:
  - a resposta da IA aparece e começa a ser falada na hora; os cartões (clima, notícias, cotações) chegam em paralelo (antes a resposta esperava esses dados da internet);
  - o aviso "só um minutinho" é cortado quando a resposta chega (antes a resposta esperava ele terminar);
  - o microfone envia o pedido ~1 s depois que você para de falar quando a frase já foi entendida (antes, sempre 2,2 s);
  - o PC registra no log quanto a IA levou em cada resposta.
- **⚡ OTIMIZAR** (perfil, CONTROLES, tela de bloqueio ou "Jarvis, otimiza o sistema"): mede a resposta do JARVIS e a fluidez da tela, limpa caches antigos do navegador e sobras de áudio no PC, dá uma nota e liga o **Modo leve** sozinho se o aparelho estiver pesado (sem o vidro desfocado, que é o que mais pesa no celular).
- **📘 BRANDING BOOK** dentro do JARVIS: botão ao lado do Olho de Deus e dos Agentes, em CONTROLES, no perfil e na tela de bloqueio (ou "abre o branding book").
- **Saudação só às vezes**: o desbloqueio cumprimenta na 1ª vez do dia ou depois de 3 horas; nas outras vezes entra em silêncio. Configurações > Bloqueio > Saudação ao desbloquear (Às vezes / Sempre / Nunca). O aviso de tentativas não reconhecidas continua sendo falado.
- **Site (Netlify)**: câmera e localização liberadas para a própria central (a câmera e o "ONDE ESTOU" fora de casa estavam bloqueados pelo site).

## 7.1.0 — 13 de novembro de 2026

- **HOLOGRAMA**: pesquisas viram uma tela viva. "Me explica como funciona…", "pesquisa sobre…", "me ensina…" abrem uma apresentação de 4 a 6 cenas animadas (ícone em anéis, título com efeito holográfico, legenda palavra a palavra, tópicos e número em destaque que sobe na tela), narrada pela voz do JARVIS: cada cena avança quando ele termina de falar. Barra de progresso por cena, pausa, voltar, avançar e um resumo no fim. Foto de fundo da Wikipédia.
- **Receita viva com modo cozinha**: "receita de bolo de cenoura" mostra ingredientes para marcar (os que faltam vão para a lista de compras), passo a passo grande, dica de ouro e timer do passo com um toque. Por voz: "próximo passo", "repete", "passo anterior", "fecha". A tela não apaga enquanto a receita está aberta.
- Funciona no PC e pela nuvem (fora de casa).

## 7.0.0 — 13 de novembro de 2026

- **Diagnóstico pela câmera**: "abre a câmera e analisa esse item" abre a câmera, espera a imagem firmar e analisa sozinho. A resposta vem numa janela de diagnóstico (nome, categoria, confiança, resumo, detalhes, alertas e dicas) além da fala curta. Funciona no PC e pela nuvem; a foto não é guardada.
- **Olho de Deus com trânsito ao vivo**: nova categoria 🚦 Trânsito (abre primeiro) com o mapa ao vivo do Waze na cidade do clima. Busca por cidade, endereço, bairro ou CEP; MINHA CIDADE, ONDE ESTOU, zoom, atalhos dos lugares salvos e IR ATÉ AQUI NO WAZE. Por voz: "mostra o trânsito".
- **Otimização**: mais telas carregam só quando aparecem (Olho de Deus, cadastro, visitante, modo torcedor, janelas de áudio/microfone/navegador) e o React foi para um pacote separado, que fica no cache entre versões. O pacote inicial caiu de 515 kB para 342 kB.

## 6.8.3 — 13 de novembro de 2026

- **Central de Agentes**: botão 🤖 AGENTES ao lado do Olho de Deus (e em CONTROLES). Mostra cada agente, o que faz e exemplos (um toque envia o pedido), os lugares do agente de rotas (▶ ROTA com um toque, adicionar e apagar) e um chat com os agentes, onde aparece o que você pediu e o que eles fizeram. Funciona também pela nuvem (o lugar salvo fora de casa vai para o PC na sincronização).
- **Verificar atualizações** no menu do perfil (Controle & Ações): confere no GitHub, mostra se está em dia ou quantas versões novas há, acende a bolinha do ATUALIZAR e oferece **Atualizar agora**.

## 6.8.2 — 13 de novembro de 2026

- **Câmera do aparelho, como na Alexa** (`components/CameraWindow.jsx`): "abre a câmera" abre a câmera do aparelho em que você está (celular ou PC), ao vivo só ali; FOTO salva no aparelho, TROCAR alterna frontal/traseira, ⏱ 3 s; "tira uma foto" conta 3, 2, 1 e salva.
- **"O que é isso?"**: com a câmera aberta (falando ou pelo botão), manda só aquela foto à IA, que responde por voz. No PC: `POST /api/camera/ask` (foto validada, não guardada; rota pessoal); fora de casa: `POST /api/cloud/vision` (Gemini, OpenAI ou Claude, com imagem). Não identifica pessoas pelo rosto.
- **App Android:** permissão de câmera (CAMERA) e a página recebe câmera e/ou microfone conforme o que o Android permitir. Precisa do APK 6.8.2.

## 6.8.1 — 13 de novembro de 2026

- **Google Agenda nos Ajustes:** a conexão da agenda só existia em Menu › Fontes de Dados, difícil de achar. Agora há a seção **GOOGLE AGENDA** em Ajustes › Geral, com o status (conectada ou não), o passo a passo para copiar o endereço secreto iCal no Google Agenda, o campo para colar e o botão para desconectar (`GET /api/calendar/status`).

## 6.8.0 — 13 de novembro de 2026

- **Sub-agentes** (`modules/agents.py`): o JARVIS entrega pedidos a agentes especialistas, que aparecem na tela enquanto trabalham (evento `agent`) e abrem o resultado no aparelho que pediu (evento `open_url` para o celular; navegador do PC quando o pedido veio do PC). Novo agente cabe numa classe com `match`/`run`.
  - **Agente de rotas 🧭:** guarda lugares ("meu trabalho fica na…", `data/lugares.json`, um por pessoa) e abre o Google Maps com a rota saindo de onde você está ("quero ir para o trabalho", "me leva pra academia a pé", "rota para o aeroporto de Guarulhos de ônibus"). Lugar pessoal sem endereço: ele pergunta. "quero ir dormir" e afins não disparam.
  - **Agente de pesquisa 🔎:** "abre o YouTube e pesquisa…", "procura … no YouTube" (antes abria sempre no PC).
  - **Fora de casa:** a nuvem conhece os lugares (sincronizados) e ganha as ações `rota`, `lugar_salvar` (vai para o PC) e `youtube`; o app abre o Google Maps/YouTube direto.
- **Ofensiva da água 🔥:** dias seguidos batendo a meta, no painel de água ("🔥 Ofensiva de N dias" ou "beba X ml para manter"), na comemoração da meta ("Ofensiva de 6 dias!"), no lembrete depois das 17h quando está em risco e por voz ("qual minha ofensiva de água?", com o recorde). Fora de casa, a nuvem continua a contagem do PC.

## 6.7.7 — 13 de novembro de 2026

- **App que se atualiza de qualquer lugar:** o app procurava versão nova só no PC (Wi-Fi de casa). Agora, se não acha o PC (fora de casa, PC desligado) ou o PC não tem APK mais novo, procura nas **Releases do GitHub** e se instala dali (só aceita APK publicado neste repositório). O GitHub gera o APK sozinho a cada versão nova na main (`release-apk.yml` dispara quando `backend/version.py` muda; versão já publicada é pulada), assinado com a **mesma chave do PC**, que precisa ir para os secrets do repositório uma vez: rode o **`Preparar-App-no-GitHub.bat`** (abre a página e põe a chave e a senha na área de transferência para colar; não envia nada sozinho). Sem a chave, o processo só avisa e pula. Precisa do APK 6.7.7 (a última vez gerado no PC).

## 6.7.6 — 13 de novembro de 2026

- **Tela preta ao abrir os Ajustes (site):** com a central aberta durante uma publicação nova no Netlify, abrir uma parte carregada sob demanda (Ajustes, widgets, modais) pedia um arquivo da versão antiga, que não existe mais; o Netlify respondia com a página da central no lugar do código e a tela inteira ficava preta. Agora: (1) a central recarrega sozinha uma vez e pega a versão nova; (2) se ainda falhar, só aquela parte mostra "Esta parte não carregou" com RECARREGAR, e a central continua de pé; (3) qualquer erro na tela vira "O JARVIS precisa recarregar a tela" com o botão RECARREGAR, nunca mais a tela preta; (4) no Netlify, arquivo antigo de `/app/assets/` responde 404 em vez da página da central.

## 6.7.5 — 13 de novembro de 2026

- **"Verificar atualizações" (Ajustes › Diagnóstico) corrigido:** ainda olhava as Releases do GitHub (que o projeto não usa) e sempre dizia "versão mais nova". Agora confere na hora a mesma fonte do ⟳ ATUALIZAR (`/api/system/update/status?force=true`), mostra a versão deste PC e quantas versões novas existem, e já acende a bolinha do botão sem esperar os 30 minutos. A conferência diária antiga saiu.

## 6.7.4 — 13 de novembro de 2026

- **Agenda fora de casa:** o PC manda para a nuvem, na sincronização, os compromissos dos próximos 7 dias (Google Agenda ou iCal; título, início e local, atualizados a cada 10 min). A nuvem **nunca recebe a chave do Google**. Fora de casa, "o que tenho amanhã?" responde, e o widget de agenda e a tela de espera mostram os compromissos.
- **Música no celular fora de casa (app):** "toca Coldplay" abre a busca no Spotify do celular; "pausa", "próxima", "anterior" e os botões de música da central viram os botões de mídia do Android (como um fone Bluetooth; vale para qualquer player), sem chave do Spotify. No navegador, o JARVIS explica que isso funciona pelo app. Precisa do APK 6.7.4.

## 6.7.3 — 13 de novembro de 2026

- **Memória que aprende sozinha** (`modules/memory_learn.py`): depois de cada resposta da IA, se você falou de si ("eu", "meu", "gosto", "trabalho"...), o JARVIS pede à IA, em segundo plano e sem atrasar a resposta, até 3 fatos duradouros (gostos, rotina, pessoas próximas, metas, trabalho, lugares) e guarda sem repetir o que já sabe. Fica de fora: coisas passageiras, senhas, documentos, dados bancários e detalhes de saúde. "Pare de aprender sobre mim" / "pode voltar a aprender sobre mim" (`memory_auto_learn`). "O que você lembra de mim?" mostra até 12 memórias e lembra como apagar; a IA recebe as 30 mais recentes.
- **Nuvem:** as memórias vão na sincronização, e o JARVIS de fora de casa também conhece o senhor.
- **Bug antigo na memória:** sem o arquivo `memoria.json`, o primeiro "lembre que..." gravava dentro da lista padrão compartilhada (cópia rasa). Corrigido.

## 6.7.2 — 13 de novembro de 2026

- **Bolinha de atualização:** quando há versão nova do JARVIS no GitHub, o botão **⟳ ATUALIZAR** ganha uma bolinha vermelha com o número de versões novas, na tela de bloqueio e no topo da central (onde o botão só aparece quando há novidade). Clicar pergunta "Atualizar para a versão X?" e faz a atualização de sempre (baixa, avisa por voz e reinicia). O PC confere a branch que o ATUALIZAR baixa (`git fetch`, sem baixar nada ainda) e conta os commits "JARVIS x.y.z" novos; guarda o resultado por 15 min, e a central pergunta a cada 30 min (`GET /api/system/update/status`, liberado também no bloqueio). Antes, a conferência olhava as Releases do GitHub, que o projeto não usa, e nunca acusava nada. Só no PC (o celular atualiza pelo ATUALIZAR APP).

## 6.7.1 — 13 de novembro de 2026

- **Timers com nome de verdade:** "cancela o timer do arroz" cancelava **todos** os timers; agora cancela só aquele (com vários e sem nome, pergunta qual; "cancela todos" continua valendo). Novos: "quanto falta pro arroz?" e "aumenta 5 minutos no timer do arroz". Os timers ficam em `data/timers.json` e voltam depois de o JARVIS reiniciar; os que acabaram durante o reinício (até 10 min) são avisados.
- **Aviso em todos os aparelhos:** "avisa em todos os aparelhos que o almoço está pronto", "avisa todo mundo que…", "anuncia que…", "faz um anúncio: …" (`modules/announce.py`): todas as telas, voz no PC e nos celulares com a central aberta, e notificação no app.
- **Timers e lembretes falam também no celular:** o evento novo `speak_everywhere` faz os aparelhos que não são o PC falarem o aviso (o timer pedido na cozinha toca lá).
- **Testes estáveis no CI:** os 4 testes que falhavam fora do PC do dono dependiam de existir uma foto real em `data/`; agora usam a fixture `credentials`. 380 testes passando, `ruff` limpo.

## 6.7.0 — 13 de novembro de 2026

- **Modo bem-estar** (`modules/wellbeing.py`): o JARVIS como um mordomo atento, não um psicólogo. Respiração guiada 4-7-8 e quadrada, aterramento 5-4-3-2-1, registro do humor do dia (1 a 5, em `data/humor.json`, um por pessoa) e resumo da semana ("como foi meu humor essa semana?"). A IA recebe orientações de escuta ativa (acolher, validar, uma pergunta, depois algo prático; nunca diagnosticar; sugerir psicólogo se persistir) e o humor recente para ajustar o tom.
- **Segurança:** frases de crise ("quero morrer", "penso em me machucar", "não quero mais viver"...) recebem sempre a mesma resposta acolhedora com **CVV 188** e **SAMU 192**, antes de qualquer outra coisa e sem passar pela IA, inclusive com a central bloqueada, no modo visitante e pela nuvem. Expressões comuns ("me matar de rir", "morrer de vergonha", "cortar o cabelo") não disparam. Um teste garante que o texto do PC e o da nuvem sejam iguais.
- **Pela nuvem:** as mesmas respostas fixas; "meu humor hoje é 4" fora de casa vai para o PC na sincronização.
- Lint: dois avisos antigos que travavam o `ruff check` (CI) corrigidos (`when.py`, `voice_route.py`).

## 6.6.9 — 13 de novembro de 2026

- **Mesma voz do JARVIS fora de casa:** pela nuvem (dados móveis ou Chrome do celular), a resposta saía na voz do Android/navegador. Agora a nuvem gera o áudio com a **mesma voz do PC** (vozes neurais da Microsoft, as mesmas do edge-tts): o PC manda na sincronização o estilo escolhido em Ajustes (nome da voz, velocidade e tom: Natural, Grave, Clássica, Thalita, Andrew), e a central toca o MP3 de `POST /api/cloud/tts`. Antes da primeira sincronização, usa a voz padrão (Antonio, estilo Natural). Sem internet ou com erro, cai na voz do aparelho. Nova dependência das funções: `msedge-tts`.

## 6.6.8 — 13 de novembro de 2026

- **App parado no bloqueio ao sair de casa:** com a central do notebook aberta no Wi-Fi, ao passar para os dados móveis o app avisava a troca de rede mas continuava na mesma página (endereço da rede de casa); PIN e digital ficavam "carregando" para sempre. Agora, a cada troca de rede (e ao voltar para o app depois de 15 s), o app decide de novo: notebook respondendo nesta rede → central do notebook; não respondendo → a mesma central pela nuvem (sem Tailscale). Ao voltar ao Wi-Fi de casa, volta sozinho para o notebook.
- **Teste do notebook mais seguro:** com a chave de pareamento, só conta como "notebook" a resposta do próprio JARVIS (200 ou 403, em JSON), para outro aparelho com o mesmo endereço numa Wi-Fi de fora não enganar o app. Precisa do APK 6.6.8.

## 6.6.7 — 13 de novembro de 2026

- **App caía no acesso pela nuvem mesmo em casa:** ao abrir, o app 6.6.x testava o PC em `/api/health` sem a chave de pareamento; o PC respondia 401 (o celular sempre precisa da chave) e o app entendia "PC fora do ar". Agora o teste leva a chave, e qualquer resposta do PC conta como "ao alcance": só falha de conexão (dados móveis, outra rede, PC desligado) leva à nuvem. Precisa do APK 6.6.7: gere no PC e toque em ATUALIZAR APP no celular (funciona de dentro da nuvem, na Wi-Fi de casa).

## 6.6.6 — 13 de novembro de 2026

- **Status certo no acesso pela nuvem:** o aviso do topo dizia "notebook desligado" mesmo com o notebook ligado em casa (você só estava fora, nos dados móveis). Agora diz "☁ ACESSO PELA NUVEM · notebook ligado em casa · listas sincronizadas" quando o PC sincronizou nos últimos 3 minutos, e "notebook desligado · visto 13/11 15:09" quando não. Atualiza a cada minuto. No app, o aviso de rede ("O senhor está conectado pela rede de dados móveis") continua aparecendo e falando também pela nuvem. `/api/cloud/status` passa a mandar `agora`.

## 6.6.5 — 13 de novembro de 2026

- **Modo nuvem com a central de sempre:** com o notebook desligado, o celular (Chrome ou app) abre a **mesma central** do app e do site (orbe, Canal Ativo, lista de compras, água, tarefas, clima, notícias, CONTROLES, Área Limpa), em vez da tela simplificada. Depois do PIN da nuvem, um adaptador (`utils/cloudShim.js`) responde no lugar do PC: conversa com a IA da nuvem (com voz do aparelho), compras, tarefas, lembretes, alarmes, água, notícias, clima e os avisos. O que só existe no PC (câmera, Spotify, volume, controle do Windows) responde "precisa do notebook ligado". Um aviso discreto no topo mostra "☁ MODO NUVEM · notebook desligado" e quando o PC foi visto pela última vez. O "Primeiros passos" não aparece na nuvem.
- **Selo "Powered by Netlify" por cima dos botões:** no celular, a barra de baixo (TELAS, NOTÍCIAS, microfone, CONTROLES) sobe acima do selo; no PC, o texto do canto sai de baixo dele.
- **TRANSMITIR (app Android):** em CONTROLES › SISTEMA & HUD, abre a transmissão de tela do Android para espelhar o JARVIS numa TV (Chromecast, Smart TV, Miracast). Precisa do APK 6.6.5.

## 6.6.4 — 13 de novembro de 2026

- **Tela final do resumo (bom dia / boa tarde / boa noite) reorganizada no PC:** antes, o orbe ocupava o meio e os cards ficavam espremidos numa fileira só de 200 px, por cima das linhas do orbe. Agora o orbe fica menor no alto e os cards vão para um painel de vidro embaixo, em no máximo 2 fileiras (8 assuntos = 4×2; 10 = 5×2; tela média até 3 colunas), maiores (até 300 px) e sem passar por cima do orbe (o painel tem altura máxima e rola por dentro se precisar). A frase final do JARVIS aparece inteira (até 2 linhas) e a prontidão fisiológica ficou compacta, com o anel ao lado dos números. No celular, nada muda.

## 6.6.3 — 13 de novembro de 2026

- **Nuvem só no celular:** no navegador do **computador**, a central é sempre a do PC: sem o botão USAR PELA NUVEM e sem entrar na nuvem (nem com `?nuvem=1`). No **Chrome do celular** e no **app Android**, com o notebook desligado, entra sozinho no modo nuvem, com as configurações da central.
- **App Android com nuvem de novo** (como na 6.6.0): sem resposta do PC, abre o modo nuvem, confere o PC a cada 20 s e volta para a central completa quando ele liga; avisos de lembretes, alarmes e água pela nuvem com o app fechado; voz do Android nas respostas da nuvem. Precisa gerar o APK 6.6.3 (`Gerar-App-Android.bat`).
- **App abre mais rápido sem o PC:** ao abrir, o app confere o PC por até ~3 s antes de carregar a central; sem resposta, vai direto para a nuvem, em vez de esperar o "tempo esgotado" do Android (que em alguns celulares mostrava a página de erro crua "Página da Web não disponível").

## 6.6.2 — 13 de novembro de 2026

- **App Android de volta como antes:** o app fala só com o PC (Wi-Fi de casa e Tailscale), sem modo nuvem: com o PC fora do alcance, volta a tela "reconectando" de sempre, e os avisos vêm só do PC. O modo nuvem fica só no **navegador** (celular ou computador). Não precisa gerar APK novo: o app 6.5 continua valendo.
- **Configurações da central valem na nuvem:** a cada minuto o PC manda para a nuvem o nome da IA, a personalidade (inclusive o estilo Alexa), o fundo (Blueprint, Universo ou Clássico), a cor do tema, a acessibilidade, o modo silencioso (voz da nuvem começa muda), os temas de notícias (viram atalhos na aba NOTÍCIAS) e os copos de água rápidos. Nada de câmera, PIN, atalhos ou chaves. A nuvem valida tudo o que chega.

## 6.6.1 — 13 de novembro de 2026

- **Pedidos de voz no bloqueio não respondiam:** a escuta de comandos do bloqueio ("Jarvis, como está o clima?") só ligava com o **Modo Sentinela** ativado nas configurações (vem desligado) e com o microfone do bloqueio ligado (vinha silenciado); sem as palmas ligadas, nem o botão do microfone aparecia. Agora o bloqueio ouve sempre que o microfone dele está ligado, o botão do microfone aparece sempre (no PC) e o microfone começa ligado (`lock_mic_on` padrão `true`; P ou o botão desligam e a escolha é lembrada).
- **Notícias no bloqueio:** "Jarvis, quais as notícias?" lê as 3 primeiras manchetes e mostra as 5 numa mini janela (antes pedia o rosto).
- **Spotify no bloqueio:** tocar, "toca minha playlist", pausar, próxima, anterior e "o que está tocando" respondem sem liberar a central (antes só no modo visitante), com a mini janela ♫. "Abre o Spotify" continua pedindo o rosto.
- **"Pausa a música" não pausava** (o Spotify só entendia "pausar", "pause" e "parar"): corrigido também na central.
- Continuam pedindo o rosto: tarefas, lembretes, agenda, memória, finanças e o resto que é pessoal. Teste: `backend/tests/test_lock_voice_661.py`.

## 6.6.0 — 13 de novembro de 2026

- **Modo nuvem: o JARVIS no celular com o notebook desligado.** Antes, o app abria o endereço do PC na Wi-Fi de casa (`http://192.168.x.x:5173`) e, nos dados móveis ou com o notebook desligado, só mostrava "Página da Web não disponível" (`ERR_CONNECTION_TIMED_OUT`). Agora, quando o PC não responde, a central abre o **modo nuvem**, que roda nas funções do Netlify (`/api/cloud/*`, dados no Netlify Blobs): conversa com a IA por voz ou texto (Gemini, OpenAI ou Claude, com a chave nas variáveis do Netlify), lista de compras, tarefas, lembretes, alarmes, água, notícias (Google Notícias) e clima (Open-Meteo). Entra com um PIN próprio (`JARVIS_NUVEM_PIN`); 8 erros em 15 min bloqueiam.
- **Sincroniza com o PC:** com `JARVIS_NUVEM_CHAVE` no `.env`, o PC busca a cada minuto o que foi mudado pelo celular, aplica nas listas dele e manda as listas de volta para a nuvem (`modules/cloud_sync.py`). Só o perfil principal.
- **App Android 6.6:** abria o modo nuvem quando o PC não respondia (desfeito na 6.6.2: o app voltou a falar só com o PC).
- **Navegador:** no celular, PC desligado = modo nuvem direto; no computador, a tela de "PC desligado" ganhou **USAR PELA NUVEM**.
- **Voz no site com erro (microfone):** na central, o ouvido contínuo ("Jarvis, …") ficava ligado e, ao tocar no microfone, o botão abria uma segunda escuta antes de a primeira soltar. O Chrome só aceita uma escuta de voz por página: as duas se derrubavam e o botão dava erro ou não ouvia. Agora o botão pede o microfone (`jarvis-mic-claim`), o ouvido solta e só volta quando o botão termina (`jarvis-mic-release`). A falha de rede passageira do reconhecimento do Chrome tenta de novo sozinha uma vez, sem mostrar erro.
- Guia: `docs/MODO-NUVEM.md`. Testes: `netlify/nuvem/core.test.mjs` (`npm run test:nuvem`) e `backend/tests/test_cloud_sync_66.py`.

## 6.5.21 — 12 de novembro de 2026

- **Pedido no bloqueio virava "entrar na central":** com o microfone do bloqueio ligado, a própria fala ("Jarvis, como está o clima?") era confundida com duas palmas, e duas palmas no bloqueio escaneiam o rosto e entram — a central desbloqueava em 2 s e o pedido se perdia (visto nos registros: bloqueia 21:28:17, entra 21:28:19). Agora a palma espera 0,9 s: se o reconhecimento de voz ouviu fala junto (evento `jarvis-heard`), é fala e a "palma" é ignorada.

## 6.5.20 — 12 de novembro de 2026

- **Perguntas no bloqueio não respondiam:** toda vez que a central voltava para a tela de bloqueio, o microfone recomeçava silenciado (privacidade), então "Jarvis, como está o clima?" nem era ouvido (nenhum pedido chegava ao PC). Agora o microfone do bloqueio lembra a última escolha (P ou clique em MIC): ligado fica ligado nos próximos bloqueios (`lock_mic_on`, `POST /api/lock/mic`). Ligado para o perfil principal.

## 6.5.19 — 12 de novembro de 2026

- **O JARVIS se religa sozinho se cair:** o backend parou sozinho às 20:42 (sem erro no log nem suspensão do PC) e a central ficou em "Reconectando". Agora o ouvido offline, que já confere o JARVIS a cada 2 s, liga de novo pelo `Iniciar-JARVIS.bat site` quando ele fica 45 s fora do ar (no máximo uma vez a cada 10 min). Parar pelo `Parar-JARVIS.bat` encerra o ouvido antes, então parar de propósito não religa. Testado: derrubado às 21:14:29, de volta às 21:15:31.

## 6.5.18 — 12 de novembro de 2026

- **Botão FUNDO na central:** no topo, ao lado de ÁUDIO e SPOTIFY, troca o fundo na hora (Blueprint → Universo → Clássico) e o PC salva para os outros aparelhos. O "Trocar fundo" do CONTROLES passou a trocar na hora também (antes dependia da resposta do PC e não reconhecia o Universo como atual).
- **Chat que recolhe sozinho:** na Área Limpa, a janelinha do chat ficava aberta para sempre depois da primeira resposta; agora some 45 s depois da última conversa (rolar ou digitar nela segura aberta). No modo normal, o Canal Ativo recolhe depois de 90 s sem uso (antes 3 min).

## 6.5.17 — 12 de novembro de 2026

- **Voz cortando o começo da frase:** com "Jarvis, …" (sem tocar no microfone), o Chrome dividia a frase numa pausa curta ("Jarvis abre o" + "YouTube") e só um pedaço era enviado. Agora os pedaços que chegam logo depois da palavra de ativação são juntados (até 1,3 s de silêncio) e a frase vai inteira. No botão do microfone, a permissão era conferida a cada toque e atrasava o início (as primeiras palavras se perdiam): agora só na primeira vez, e o bipe toca quando o microfone de fato começou a ouvir.
- **"Abriu o clima" sozinho:** o aviso "Previsão de chuva amanhã…" é diário, mas a memória de "já avisei" zerava a cada reinício do JARVIS (toda atualização reinicia) e ele se repetia várias vezes no mesmo dia. Agora fica em disco (`data/gatilhos_avisados.json`).

## 6.5.16 — 12 de novembro de 2026

- **Limpar o chat:** botão "🗑 LIMPAR" no Canal Ativo. Pergunta "Apagar qual conversa?" — "Só a de hoje" ou "Todo o período" (ou Cancelar). Apaga a conversa na tela de todos os aparelhos (evento `chat_cleared`) e no PC (memória de conversa e o contexto da IA), sem apagar fatos, preferências e rotina. `POST /api/chat/clear` e `memory.clear_conversation`.

## 6.5.15 — 12 de novembro de 2026

- **Tela de espera (Área Limpa) como smart display:** em volta do orbe, saudação e relógio grande com a data; manchetes dos seus temas passando (tocar abre a janela de notícias); à esquerda o clima de agora e dos próximos 5 dias; à direita os próximos compromissos e lembretes (com o alarme), a água do dia num anel (toque = +1 copo) e as compras. Tocar em qualquer cartão faz o pedido por voz. Tudo se atualiza sozinho (`components/ZenGlance.jsx`). Novos dados: `GET /api/agenda/next` e `icon`/`week` em `/api/weather`.

## 6.5.14 — 12 de novembro de 2026

- **"YouTube" pela segunda vez não abria:** o reconhecimento de voz entregou só "YouTube" (sem o "abre"), e a frase ia para a IA, que só conversava. Agora o nome de um site/app sozinho abre (como na Alexa), inclusive "vai no YouTube", "entra no Netflix" e "o Netflix aí".
- **Entende melhor a voz:** `modules/voice_fix.py` corrige trocas comuns do reconhecimento ("iutubi", "you tube", "espotifai", "netiflix", "uatsap", "chat gpt", "abri o" → "abre o") e aproxima nomes parecidos com os conhecidos ("netflx" → Netflix), sem mexer em frases longas nem em outros comandos.
- **Estilo Alexa:** nova personalidade "Estilo Alexa (curto e direto)" em Configurações › IA: respostas de 1 ou 2 frases curtas, a informação primeiro, oferecendo detalhes. Ligada para o perfil principal.

## 6.5.13 — 12 de novembro de 2026

- **Rodapé do bloqueio sem encavalar:** com os botões da direita mais para o centro (por causa do selo do Netlify), o ÁUDIO ficava por cima de "ESPAÇO = LIBERAR". No PC, a faixa do microfone agora fica numa linha própria, logo acima da fileira de botões.

## 6.5.12 — 12 de novembro de 2026

- **Bloquear pelo celular:** o botão do topo virou "🔒 BLOQUEAR" (antes "⏻ SAIR", que não deixava claro que volta à tela de bloqueio) e o painel CONTROLES ganhou "BLOQUEAR" em Sistema & HUD (no celular, o CONTROLES fica no rodapé). "Modo bloqueio" por voz continua valendo.
- **Selo do Netlify por cima do CELULAR:** no site, o grupo de botões do rodapé do bloqueio (Áudio, Fundo, Modo Torcedor, Celular) fica à esquerda do selo "Powered by Netlify"; no celular, os botões sobem um pouco.

## 6.5.11 — 12 de novembro de 2026

- **Em qual navegador?** Ao abrir um site ("abra o YouTube"), o JARVIS pergunta em qual navegador, mostra a lista dos instalados (Chrome, Edge, Firefox, Brave, Opera e "Padrão do Windows") e abre no escolhido, falando ("no Chrome", "sempre no Edge", "tanto faz", "cancela") ou tocando. "Sempre…" ou a caixinha "Lembrar a escolha" grava a preferência (`site_browser`: "ask", "default" ou o navegador), que também fica em Configurações › Mídia & Foco › NAVEGADOR DOS SITES. Com um navegador só instalado, não pergunta. `modules/browser_choice.py`, `GET /api/browser`, `POST /api/browser/choose`, `components/BrowserChooser.jsx`.

## 6.5.10 — 12 de novembro de 2026

- **Rodapé do bloqueio invertido (PC):** o carimbo J.A.R.V.I.S. foi para o canto inferior esquerdo e o CELULAR para a direita, ao lado do Modo Torcedor (também deixa de ficar embaixo do selo do Netlify). No celular e em telas pequenas, nada muda.
- **Spotify do bloqueio com imagem:** parado ou desconectado, um disco de vinil no lugar do ícone (gira devagar quando conectado, com a dica "Jarvis, toca minha playlist"); tocando, a capa do álbum fica maior e o fundo do cartão ganha a capa desfocada.

## 6.5.9 — 12 de novembro de 2026

- **ATUALIZAR APP no Xiaomi/HyperOS:** a instalação "por sessão" do Android ficava parada em 100% nesses celulares. Agora, com o app aberto, ele entrega o APK baixado ao instalador padrão do Android (a tela "Deseja atualizar este app?"), que funciona em qualquer celular (`ApkProvider`); em segundo plano continua a instalação silenciosa. APK 6.5.9.
- **Diagnóstico:** o celular informa a versão do app instalada ao buscar avisos (`X-Jarvis-App`); o PC registra no log e mostra em `/api/mobile/info` (`phone_app`).

## 6.5.8 — 12 de novembro de 2026

- **Botão ÁUDIO na tela de bloqueio** (🎧, ao lado do FUNDO): escolher onde o JARVIS fala (no celular: aqui ou no PC), a caixa de som do PC (com 🔊 TESTAR), o microfone do PC (o ouvido offline reabre na hora no microfone novo) e o microfone desta tela (palmas e escuta). `GET/POST /api/audio`, `POST /api/audio/test`, `modules/audio_devices.py`; preferências `audio_output_device` e `voice_input_device`. O alarme toca na mesma caixa da voz.
- **Mini janela das respostas no bloqueio:** cada pergunta pública respondida na tela de bloqueio abre uma mini janela (`components/LockAnswer.jsx`). Clima: agora (temperatura, sensação, umidade, vento), hoje (máx/mín, chuva, nascer e pôr do sol) e os próximos 6 dias (previsão de 7 dias, `tools.weather_card`). Outras: a pergunta e a resposta. Fecha sozinha em 30 s sem toque.
- **Sites numa janela média e arrastável:** "abra o YouTube" (e os outros sites e atalhos) abre uma janela própria do navegador padrão (Chrome, Edge, Firefox ou Brave), com ~60% da tela, no canto inferior direito, em vez de uma aba em tela cheia (`modules/browser_window.py`; `site_window_mode` = "tab" volta ao jeito antigo).

## 6.5.7 — 12 de novembro de 2026

- **Atualização do app parada em 100%:** no Android 14+ e em celulares Xiaomi/HyperOS, a tela "Atualizar o JARVIS?" aberta pelo instalador em segundo plano era bloqueada em silêncio. Agora quem abre a confirmação é a própria tela do JARVIS, e de reserva aparece o aviso "Concluir atualização do JARVIS" para tocar; se nada acontecer em 2 minutos, o botão destrava com uma explicação. APK 6.5.7.
- **"Modo bloqueio" por voz:** mais jeitos de dizer levam a central para a tela de bloqueio ("ativa o modo bloqueio", "entra no modo de bloqueio", "volta pra tela de bloqueio", "bloqueia a central"…), com a resposta "Bloqueando a central, senhor. Até logo." ("bloquear a tela" continua bloqueando o Windows). Teste em `test_lock_voice_657.py`.

## 6.5.6 — 12 de novembro de 2026

- **Janela da pesquisa fecha sozinha:** sem nenhuma interação, ela fecha 25 s depois (`AUTO_CLOSE_MS`), sempre esperando o JARVIS terminar de ler a resposta ("LENDO…"). Uma barra fininha no topo mostra o tempo; tocar, rolar ou digitar recomeça a contagem, e "FECHA EM Xs" → "📌 FIXADA" mantém aberta.

## 6.5.5 — 12 de novembro de 2026

- **Painel CONTROLES ampliado:** grade compacta por seção com Modos de ambiente, Rotinas (resumo pela hora, dormir, saindo de casa, timer de 5 min), Ações rápidas (notícias, compras, bebi um copo, índice de água), Música & som (tocar, pausar, próxima, mudo, volume − e +) e Sistema & HUD (modo silencioso liga/desliga direto, trocar fundo, área limpa, widgets, ajustes). No celular, o CONTROLES fica no rodapé e abre para cima.
- **Fixar comando na tela inicial (app):** na faixa DIGA, "📌 fixar na tela inicial" e depois o comando ("bom dia", "boa tarde", "notícias"…): o Android cria um ícone que roda o comando direto (`JarvisApp.pinShortcut`; "notícias" abre a janela de notícias). APK 6.5.5.
- **Pesquisa no celular:** a tela de resultado não espreme mais a pergunta numa coluna estreita (o card empilha), o título fica menor, o FECHAR vira ✕ e a janela rola por dentro; um "resumo" que era só cortesia ("Certo, senhor Patrick") não aparece mais.

## 6.5.4 — 12 de novembro de 2026

- **Notícias que não chegavam no celular:** a fila de avisos do celular ficava só na memória; cada reinício do JARVIS (toda atualização publicada reinicia) apagava os avisos que o celular ainda não tinha buscado, e as notícias já marcadas como avisadas não voltavam. Agora a fila fica em disco (`modules/phone_feed.py`, `data/avisos_celular.json`) e a numeração continua depois do reinício. O log registra quando o celular busca avisos ("Celular buscando avisos … via túnel/rede").

## 6.5.3 — 12 de novembro de 2026

- **Pular continuava falando / Cancelar fechava mas a voz seguia:** com a voz no celular, os dois só calavam a caixa do PC. Agora o PC manda `speech_stop` ao aparelho: "pular" cala só a fala atual (a próxima parte segue), "cancelar" cala tudo e esvazia a fila; o botão Cancelar também cala o aparelho na hora, e uma voz que ainda estava baixando não toca mais depois.
- **Entrada com frases variadas:** `modules/phrases.py` com várias versões para o cumprimento do desbloqueio (rosto, PIN, digital), a confirmação antes do briefing, a abertura do "bom dia" / "boa tarde" / "boa noite", o "nada fora do comum", "repetir o briefing?" e "em que posso ajudar?". Nunca repete as 2 últimas de cada momento, mesmo depois de reiniciar. Teste em `test_phrases_653.py`.

## 6.5.2 — 12 de novembro de 2026

- **ATUALIZAR APP resolve tudo dentro do app:** quase toda atualização é só da central (site), sem APK novo. Agora, quando o app já está em dia, o botão diz "App em dia (versão). Carregando a central mais nova…" e recarrega a tela. Quando há APK novo no PC, o app baixa e instala sozinho, como antes (desde o 6.5.0 também pelo túnel). Sem APK novo nesta versão.

## 6.5.1 — 12 de novembro de 2026

- **Briefing sem atraso nas notícias:** a voz de cada parte só começava a ser gerada quando chegava a vez dela; nas notícias (as falas mais longas) eram até ~9 s de silêncio com o card já na tela. Agora todas as partes começam a ser geradas no início do briefing (`tts.prefetch`, até 3 de cada vez) e cada fala só espera o que faltar.
- **Celular no mesmo ritmo da tela:** o PC "chutava" a duração da fala no celular e passava para o próximo card; voz e tela iam se desencontrando. Agora o celular avisa quando termina cada fala (`POST /api/tts/played`, `say_id` no `speak_on_device`) e só então o próximo card entra (com folga para a rede; aparelho antigo segue pelo tempo estimado). Testes em `test_voice_sync_651.py`.

## 6.5.0 — 12 de novembro de 2026

- **"Boa tarde":** resumo da tarde em etapas (`build_afternoon_briefing`, título RESUMO DA TARDE): o que falta da agenda de hoje, tarefas pendentes ("Ainda faltam…"), clima, água, e-mails (se conectados) e as notícias dos seus temas, com um fechamento ("O próximo compromisso é…"). "Resumo da tarde", "minha tarde" e "resumo" sozinho entre 12h e 18h também abrem. A entrada na central entre 12h e 18h faz o resumo da tarde (antes era o "bom dia" com "Boa tarde" na saudação). Atalho "boa tarde" ◐ na faixa DIGA.
- **Janela de notícias:** botão NOTÍCIAS no rodapé (ou tocar em "notícias" na faixa DIGA) abre a janela com os temas do briefing em abas, busca de outro assunto (`GET /api/news/search?q=`) e manchetes com fonte e "há X min"; tocar abre a matéria.
- **Notícias no celular:** a cada 45 min (fora das 22h às 7h), manchetes novas dos temas viram aviso no app (`modules/news_alerts.py`, `news_watcher_loop`, tipo `news`), no máximo 2 por tema por rodada e nunca a mesma duas vezes; na primeira vez só memoriza. Não fala no PC. Tocar no aviso abre a janela de notícias (`jarvis://news`). Liga/desliga na própria janela (`news_notify_enabled`).
- **App de longe:** os avisos e a atualização do app também passam pelo túnel quando o app foi pareado por ele (`PcAddress`). APK 6.5.0.

## 6.4.1 — 12 de novembro de 2026

- **App de longe pelo túnel:** o link de pareamento (`/api/mobile/pair?token=…`) aberto pelo túnel da Cloudflare leva o app ao site (Netlify) já falando com o PC pelo túnel (`?api=https://….trycloudflare.com`), e o botão de baixar o APK leva a chave (o APK passa pelo túnel). Só endereços `*.trycloudflare.com`; um Host forjado volta ao caminho de casa. Em casa, pareie de novo pelo QR ou pelo PIN. Teste em `test_tunnel_63.py`.

## 6.4.0 — 12 de novembro de 2026

- **Aviso de rede no app:** ao abrir o app nos dados móveis, o JARVIS avisa "O senhor está conectado pela rede de dados móveis."; quando a rede muda (com o app aberto ou ao reabrir), "Mudança de rede, senhor. Agora o senhor está no Wi-Fi." (ou nos dados móveis). Aviso no topo da tela e voz no celular; no Wi-Fi de sempre, silêncio. O app Android informa a rede (`JarvisApp.networkNotice()`, evento `jarvis-app-network`; com a VPN do Tailscale ligada, olha a rede por baixo dela) e lembra a anterior. `components/NetworkNotice.jsx`, `utils/networkNotice.js`, teste `networkNotice.test.js`. APK 6.4.0.

## 6.3.0 — 12 de novembro de 2026

- **Ouvido offline:** "Jarvis, que horas são?" com o navegador **fechado**. `scripts/voice_listener.py` (Vosk, modelo pt-BR pequeno em `%USERPROFILE%\.jarvis-voice`, nada sai do PC) acorda com "Jarvis" e manda o pedido para `/api/chat`; a resposta sai pela caixa do PC. Fica quieto com a central aberta numa aba do PC (a página já atende), enquanto o JARVIS fala (`/api/health` ganhou `speaking`) e com a opção desligada (Configurações › Mídia & Foco, `voice_listener_enabled`). Só "Jarvis"? Bipa e ouve o pedido na frase seguinte. O `Iniciar-JARVIS.bat` liga quando o modelo existe; o `Parar-JARVIS.bat` desliga. Log em `logs/ouvido.log`. Pacotes: `scripts/requirements-ouvido.txt`.
- **Acesso de longe por túnel:** conexões que chegam por túnel (Cloudflare, ngrok, proxies) nunca contam como "este PC": exigem a chave e não recebem a chave. O link pode levar o endereço do PC (`?api=https://….trycloudflare.com`, `?api=reset` volta ao normal). Longe do PC, a central entra pelo **PIN** (sem a verificação do rosto).

## 6.2.0 — 12 de novembro de 2026

- **Temas de notícias no briefing:** o "bom dia" usa os temas de Configurações › Geral › NOTÍCIAS DO BRIEFING (`briefing_news_themes`, `GET /api/briefing/news-themes`), cada um com 1 a 5 manchetes. Padrão: os três de antes e **Marvel com as 3 principais** ("Em Marvel, as três principais. Primeira: …"), num card com a lista numerada; manchetes repetidas (o mesmo fato em dois sites) saem. Ideias prontas com um toque (DC, Palmeiras, Games, Fórmula 1, Bitcoin, Séries e filmes, Espaço, Star Wars…).
- **Levantamento "sem navegador":** `docs/SEM-NAVEGADOR.md` — o que já funciona só com o backend (alarmes, lembretes, água, jogo, celular, palmas do Windows) e o que falta para o PC escutar sem a aba aberta (ouvido offline com Vosk no backend).

## 6.1.0 — 12 de novembro de 2026

- **Vozes duplicadas ao entrar:** o desbloqueio já cumprimentava ("Olá... boa noite, tudo bem?") e a entrada falava de novo ("Bem-vindo de volta" ou o "Bom dia" do briefing). Agora fala só um: com briefing pendente, o rosto só confirma e o briefing cumprimenta; sem briefing, a entrada fica em silêncio. A pergunta "repetir o briefing?" vem sem o "Bem-vindo de volta". A digital também ganha a sua saudação curta.
- **Voz menos robótica:** fala de até 280 caracteres vai inteira (antes a primeira frase saía sozinha e cada pedaço recomeçava a entonação); falas longas em blocos de frases inteiras; reticências viram pausa curta. Estilos de voz (`voice_style`): Natural (padrão), Grave, Clássica, Thalita e Andrew, em Configurações › Mídia & Foco, com exemplo falado.
- **Barra de progresso 0–100%** no ATUALIZAR do PC (por etapa: baixando, preparando, reiniciando, carregando) e no ATUALIZAR APP (download real do APK, depois "Instalando…"). APK 6.1.0.

## 6.0.0 — 12 de novembro de 2026

O dia a dia.

- **Lista de compras** (`modules/shopping.py`, `/api/shopping`, painel LISTA DE COMPRAS): "coloca leite, pão e ovos na lista", "comprei o leite", "tira o pão da lista", "o que tem na lista?", "limpa a lista". Caixinhas para marcar no mercado; o celular e o PC ficam iguais na hora (evento `shopping`). Um arquivo por pessoa.
- **Rotinas em 1 comando:** os protocolos ganham os passos pausar a música, bloquear o computador, resumo de amanhã, clima agora e ler a lista de compras; rotinas prontas **Dormir** ("vou dormir", "modo dormir") e **Saindo de casa** ("estou saindo"). Editor das Configurações com os passos novos.
- **Entrar no app com a digital:** depois de entrar pelo PIN, o app oferece ativar; o PC guarda só o hash de uma chave do aparelho (`modules/device_keys.py`, `/api/auth/device/*`) e o app só a usa depois da biometria do Android. No bloqueio do app, "ENTRAR COM A DIGITAL" (e o pedido já abre sozinho).
- **Compartilhar com o JARVIS:** "Compartilhar → JARVIS" em qualquer app abre Resumir, Anotar, Lembrar amanhã ou Lista de compras.
- **Atalhos do Android:** toque longo no ícone (Falar com o JARVIS, Bom dia, Lista de compras) e botão "JARVIS" nas configurações rápidas (`JarvisTile`), que abre a central já ouvindo (`jarvis://listen`, `jarvis://say`).
- **Acesso fora de casa (Tailscale):** o PC informa o endereço do Tailscale (`remote_host`) e aceita a central por ele; o app tenta esse endereço quando a Wi-Fi de casa não responde. Guia em `docs/ACESSO-FORA-DE-CASA.md`. Correção: o endereço da rede de casa não pega mais o do Tailscale, e a regra de origem para redes `10.x.x.x` foi consertada.
- APK 6.0.0. Testes: `test_shopping_60.py`, `test_routines_60.py`, `test_device_keys_60.py`.

## 5.9.1 — 12 de novembro de 2026

- **Botão FUNDO na tela de bloqueio**, à esquerda do Modo Torcedor: cada toque troca o fundo (Blueprint → Universo → Clássico), na hora e salvo no PC. Rota pública `POST /api/background` (só o visual, como o botão do Modo Torcedor).

## 5.9.0 — 12 de novembro de 2026

- **Mini janelas de detalhes no bloqueio** (`LockDetail.jsx`): tocar em qualquer cartão (sistemas, Spotify, hoje, clima, mercado, manchete, água, jogo) abre uma janela com mais informações; fecha no ✕, Esc ou tocando fora; no celular sobe de baixo. O clique não chega à tela de bloqueio (não dispara a verificação).
- `/api/weather` traz a previsão de amanhã (`tomorrow`) e `/api/lock/public-info` mais duas manchetes (`headline.more`).

## 5.8.0 — 12 de novembro de 2026

- **Fundo Universo:** nova opção em Configurações › Geral › Fundo (`background_style: "space"`): céu com nebulosas e estrelas em CSS, com os painéis de vidro da planta; no bloqueio, estrelas piscando devagar.
- **Anel dourado no reator** (`.arc-gold-ring` no `ArcReactorHUD`).
- **Lado direito do bloqueio:** cotações (dólar, euro, bitcoin) em cima do clima e a manchete do momento embaixo; rota pública `GET /api/lock/public-info` (só informação pública, cache de 10 min).
- **Briefing no celular:** o palco do briefing (feito para ficar por cima do orbe no PC) transbordava no celular — cabeçalho esticado, página mais larga que a tela. Agora vira uma coluna com abas e cards em faixas que rolam para o lado.
- **Voz no celular:** a voz só sai no aparelho que pediu depois de reiniciar o JARVIS do PC na 5.7 ou mais nova (o PC ainda rodava a 5.6.3).

## 5.7.1 — 11 de novembro de 2026

- **Botão ATUALIZAR APP** na tela de bloqueio do app: procura a versão nova no PC na hora (sem esperar os 30 minutos) e mostra a resposta ("O app já está na versão mais nova", "Atualizando o app…", ou o erro). Ponte nova `JarvisApp.checkUpdate()`; no app antigo, o botão recarrega pelo `jarvis://open`, que também confere. APK 5.7.1.
- **Bloqueio no celular:** cartões com a mesma largura e o botão do Modo Torcedor no fim da página, em vez de flutuar sobre os cartões.

## 5.7.0 — 11 de novembro de 2026

Uma voz só, e o celular com atalhos.

- **A voz sai no aparelho que pediu:** a central manda em cada pedido quem ela é (`X-Jarvis-Client`, `X-Jarvis-Device`); o middleware guarda o destino (`core/voice_route.py`) e `speech.speak` manda a fala para aquele aparelho (evento `speak_on_device`, que toca o MP3 de `/api/tts` em fila) em vez da caixa do PC. Pedido no PC continua falando no PC. Vale para o briefing e as saudações de entrada; alarmes e lembretes continuam no PC. Antes, a resposta tocava no PC e no celular ao mesmo tempo.
- **Escolha no celular:** "🔊 VOZ NESTE APARELHO / 🖥 VOZ NO PC" na barra do chat (substitui o alto-falante da 5.5). No próprio PC a barra some.
- **Falar no PC:** "📢 FALAR NO PC" no celular: o PC lê em voz alta o que você digitar (`POST /api/speak/pc`).
- **Atalhos rápidos no celular:** Bom dia, +250 ml de água, Tarefas, Alarmes, Clima, Pausar música e Bloquear PC (com confirmação).
- Testes em `backend/tests/test_voice_57.py`.

## 5.6.3 — 11 de novembro de 2026

- **Coluna esquerda do bloqueio mais completa:** embaixo do SISTEMAS, o Spotify (tocando, conectado sem música ou "Não conectado", em vez de sumir) e o cartão HOJE (nascer e pôr do sol, umidade, vento, luz do dia que resta e quanto do dia já passou, com a semana do ano). O clima de `/api/weather` passou a trazer `sunrise`, `sunset`, `humidity` e `wind`.

## 5.6.2 — 11 de novembro de 2026

- **Briefing e falas repetidas ao entrar:** quando o `Iniciar-JARVIS.bat` rodava com a central já aberta, a aba antiga reconectava e entrava sozinha, e a aba nova entrava também: uma recebia o briefing e a outra o "quer que eu repita?", cada uma falando. Agora entradas com menos de 2 minutos de diferença contam como uma só (a segunda tela entra em silêncio), e o `Iniciar-JARVIS.bat` não abre outra aba quando a central já estava aberta (espera até 8 s ela reconectar).

## 5.6.1 — 11 de novembro de 2026

- **Cartão SISTEMAS no bloqueio:** o lado esquerdo da tela de bloqueio ganhou um cartão com o estado da IA, do microfone, da câmera e da internet, há quanto tempo o JARVIS está no ar, se há celular conectado e a hora do próximo alarme. Nova rota pública `GET /api/lock/status`, sem nada pessoal (sem nomes de aparelhos nem rótulo do alarme).

## 5.6.0 — 11 de novembro de 2026

A agenda.

- **App sem baixar toda hora:** o PC anunciava ao app a versão do JARVIS inteiro, então o celular se atualizava a cada mudança do PC (ou ficava tentando de novo, quando o APK era mais antigo). Agora o `build_apk.ps1` grava `JARVIS.apk.version` e `/api/mobile/info` anuncia a versão do APK: o app só se atualiza quando o app mudou. Falhou a atualização: tenta de novo sozinho depois, sem abrir o navegador.
- **Agenda pelo endereço iCal:** `modules/calendar_hub.py` junta o Google Calendar (OAuth) e o "endereço secreto no formato iCal" do Google Agenda (colado em Fontes de Dados, `POST /api/calendar/ics`), com eventos repetidos (`icalendar` + `recurring-ical-events`, novas dependências).
- **Próximos 3 dias no "bom dia":** card "PRÓXIMOS 3 DIAS" com quanto falta (amanhã, em 2 dias, em 3 dias), agenda + lembretes.
- **Contagem regressiva por voz** (`modules/countdowns.py`): "contagem regressiva para a viagem" / "até dia 20 de dezembro" põe um widget com dias, horas, minutos e segundos abaixo do orbe (evento `countdowns`, `GET/DELETE /api/countdowns`); "quanto falta para o natal?" só responde; "apaga a contagem regressiva" tira. As ativas entram no "bom dia". Timer de cozinha ("contagem regressiva de 5 minutos") continua com o timer.
- Testes em `backend/tests/test_calendar_56.py`. APK 5.6.0 gerado no PC.

## 5.5.0 — 11 de novembro de 2026

O celular de verdade.

- **Aparelhos conectados:** o PC sabe quem está com a central aberta (`runtime.manager.devices()`, evento `devices` e `GET /api/devices`) e mostra a lista no painel NÚCLEO · SERVIÇOS ("Este PC", "Celular · SM-A546E"...). Quando um celular conecta, aparece o aviso "📱 Conectado: …".
- **Foto no app:** a foto do perfil não aparecia no celular porque a imagem era pedida sem a chave de acesso; agora leva a chave quando a central não está no próprio PC.
- **Voz no celular:** `POST /api/tts` devolve a fala do JARVIS em MP3 para tocar no aparelho. Cada resposta do Canal Ativo tem um botão 🔊 (■ para) e o chat ganhou o **alto-falante**: ligado, toda resposta nova é lida sozinha no aparelho (preferência salva em cada aparelho).
- **Avisos no app:** no celular, o botão "📳 AVISOS" do chat liga ou desliga as notificações do JARVIS na barra do Android (antes só pelo menu do botão voltar).
- Testes em `backend/tests/test_devices_55.py`. APK 5.5.0 gerado no PC.

## 5.4.0 — 11 de novembro de 2026

- **Entrada sem repetição:** "já fiz o briefing hoje" ficava salvo em cada navegador, então o site, a central do PC e o app repetiam o briefing inteiro, e toda reentrada perguntava de novo se repetia (junto com um "Em que posso ajudar?"). Agora o PC decide para todos (`modules/entry_greeting.py`, `POST /api/briefing/entry`): 1ª entrada do dia, o briefing; 2ª, pergunta uma vez; depois, uma saudação curta que nunca repete a anterior. "Bom dia" por voz também conta.
- **Janela do perfil cortada no topo:** ela era desenhada dentro do cabeçalho (que tem efeito de vidro) e ficava presa a ele. Agora cobre a tela (portal no `<body>`), rola quando não cabe, fecha com Esc ou clique fora, vira uma coluna no celular e mostra a versão real no rodapé.
- **QR que abre o app já conectado:** a página do QR de pareamento (Perfil › Acesso Mobile › App Android) abre o app sozinha, sem endereço nem PIN; sem o app instalado, volta oferecendo baixar o JARVIS.apk.
- **Central sempre pelo site:** o `Iniciar-JARVIS.bat` e o `Abrir-Painel.bat` (também usado pelas palmas) abrem a central em https://projeto-jarvis-ia.netlify.app/app/, não mais em http://127.0.0.1:5173. No modo dev (`Iniciar-JARVIS-Dev.bat`) ou com `JARVIS_PAINEL_LOCAL=1`, continua a interface local.
- **Endereço do PC no app:** aceita vírgula no lugar do ponto e avisa quando faltam os pontos ("192168158"), com uma dica para usar o QR. APK 5.4.0 gerado no PC.

## 5.3.0 — 11 de novembro de 2026

Briefing mais pessoal.

- **Saudação que segue o relógio:** "bom dia" às 15h responde "Boa tarde" (e a abertura diz "sua tarde"); segunda, sexta e fim de semana ganham uma frase própria ("Último dia útil da semana.").
- **Clima com conselho:** ícone do card conforme o tempo (☀ ☁ ≋ ☂ ⚡) e, só quando faz diferença, um conselho falado e numa faixa âmbar: guarda-chuva, calor, frio ou trovoada. Também no clima de amanhã do "boa noite".
- **Agenda pelo próximo compromisso:** fala do próximo (não de um que já passou), "daqui a X minutos" se for nas próximas 2 horas e o seguinte; o card ganha o chip "PRÓXIMO EM X MIN".
- **Prioridades no "bom dia":** com tarefas pendentes, o card "PRIORIDADES · HOJE" sugere por onde começar (as mais antigas primeiro), e a recomendação final junta a primeira tarefa com o próximo compromisso ou com o clima.
- **Dia de jogo:** com o Modo Torcedor ligado, o jogo de hoje do time entra no briefing (adversário, horário, competição e local), lido do cache, sem rede extra.
- **Despertador no "boa noite":** o alarme de amanhã aparece num card; se amanhã começa antes das 9 e não há alarme, o JARVIS oferece marcar.
- Testes novos em `backend/tests/test_briefing_53.py`; demo do briefing com os cards novos.

## 5.2.1 — 11 de novembro de 2026

- **Botão LIGAR O JARVIS sem aviso falso:** o Chrome novo pergunta "Abrir …?" num quadro dentro da página, sem tirar o foco dela, e a central concluía em 2,5 s que o atalho `jarvis://` não estava instalado ("O botão ainda não está ativado neste PC") mesmo com ele instalado e a pergunta esperando o clique. Agora, logo depois do toque, a tela pede "Clique em Abrir"; a ajuda de instalar o atalho só aparece depois de 30 s sem o JARVIS responder, com o título "O JARVIS ainda não respondeu.".

## 5.2.0 — 11 de novembro de 2026

- **Entrada direta para quem já usa:** o navegador lembra a última entrada (`utils/session.js`). Reabrir a central até 12 h depois, com o JARVIS do PC ainda liberado, vai direto para a central (sem bloqueio, sem nova verificação e sem repetir a saudação). Bloqueado ou visitante: caminho normal.
- **Tela de PC desligado mais curta:** quem já entrou vê só "RECONECTANDO AO SEU JARVIS", com LIGAR O JARVIS, TENTAR AGORA e a ajuda recolhida; na primeira vez, três passos numerados. Confere o PC a cada 2 s (5 s depois de 2 min) e na hora em que a aba/rede volta; a busca do perfil desiste em 10 s em vez de travar. Se o botão LIGAR já funcionou neste navegador, não aparece mais "não está ativado".
- **Conexão mais firme:** o WebSocket tenta de novo em 1, 2, 4, 8 e 10 s (com sorteio), reconecta na hora quando a rede, a aba ou a tela do celular voltam, derruba conexões paradas (sem "pong" em 45 s) e ignora mensagem quebrada. A faixa de queda ganhou o botão "RECONECTAR".
- **App Android reconecta sozinho:** já pareado e com o PC fora do ar, mostra "RECONECTANDO AO SEU PC" com contagem e tenta de novo em 3–30 s, quando a Wi-Fi volta e quando o app volta para a frente — sem pedir o PIN de novo ("Parear de novo ou trocar de PC" continua a um toque). Chega no celular pelo APK 5.2.0 (o app se atualiza sozinho pelo PC).
- **Central no celular:** cabeçalho em uma linha que acompanha a rolagem, orbe menor, frases "DIGA" numa faixa que rola para o lado, Canal Ativo logo abaixo do orbe, painéis entrando com deslize e sem os controles de desktop (recolher, arrastar, 2ª tela).
- Dev: `hud-demo.html` abre a central sem backend (`?offline=1`, `?new=1`) para conferir o visual.

## 5.1.1 — 11 de novembro de 2026

- **App Android se atualiza sozinho:** quando o PC tem versão nova, o app baixa o APK do PC e se instala pelo instalador do Android (`PackageInstaller`), sem abrir o navegador. Na primeira vez, o Android pede "permitir instalar apps" para o JARVIS (uma vez só) e confirma a troca; no Android 12 ou mais novo, depois que o próprio JARVIS instalou uma versão, as próximas entram sem perguntar. Confere ao conectar e ao voltar para o app (no máximo a cada 30 min).
- **QR com o app instalado:** a página do QR (`/api/mobile`) tenta abrir o app sozinha e tem o botão "ABRIR O JARVIS" no topo: com o app, abre (e ele se atualiza); sem o app, o mesmo botão baixa o JARVIS.apk. Novo link `jarvis://open?host=IP` (já pareado: abre a central; sem pareamento: tela do PIN).
- **IP do PC mudou:** o roteador pode trocar o IP do PC (ex.: de .7 para .5) e o app ficava procurando o endereço antigo. Escanear o QR agora corrige: o app troca só o endereço, mantém a chave e reconecta ("Endereço do PC atualizado para …").

## 5.1.0 — 11 de novembro de 2026

Na web e por voz. Inclui tudo de 10 de novembro (abaixo) e mais:

- **Alarmes por voz, como a Alexa** (`modules/alarms.py`): "me acorda às 7", "alarme de segunda a sexta às 6 e meia", "quais são meus alarmes?", "cancela o alarme das 7". Tocando: bipes no PC, a hora falada a cada 25 s e um cartão com PARAR e SONECA (9 min) na central e no bloqueio; "Jarvis, parar" e "soneca" valem até com a central bloqueada (sem mostrar o nome do alarme). Desliga sozinho em 10 min; alarme perdido com o PC desligado não toca atrasado. Guardados em `data/alarmes.json`, um por pessoa.
- **Horários falados** (`modules/when.py`): "às 6 e meia", "às 7 da noite", "meio-dia", "sexta às 10", "dia 15 às 9", "daqui a uma hora e meia", "de segunda a sexta", "fim de semana". Usado por alarmes e lembretes.
- **Lembretes:** horários naturais, repetição por dia da semana ("toda terça às 19") e cancelar um só ("cancela o lembrete do dentista"); antes, cancelar apagava todos.
- **Esqueci o PIN:** no teclado do PIN e em Configurações › Bloqueio. Confirma o rosto e libera um PIN novo sem o atual por 3 minutos (`POST /api/auth/pin/reset`, só no próprio PC). Sem câmera, `Redefinir-PIN.bat`.
- **Branding Book v1.9:** capítulo XVI "Na web e por voz" com prancha nova, capa e histórico até a 5.1, linha do tempo com 14 versões.
- Versão 5.1.0 em `backend/version.py` e `frontend/src/utils/version.js`.

## 10 de novembro de 2026

- **Como a Alexa:** "Jarvis, ..." também funciona com a central aberta (antes só no bloqueio), com conversa contínua: depois de responder a um pedido de voz, ele fica 8 s ouvindo a próxima pergunta. Chaves em Configurações > Bloqueio (`hands_free_enabled`, `follow_up_enabled`).
- **Pesquisa automática:** novo modo de pesquisa "Automático, como a Alexa" (`search_mode: auto`, agora o padrão): perguntas factuais vão para a IA com busca no Google, sem abrir o navegador, sem perguntar "API ou navegador?" e sem gastar a cota da pesquisa profunda. Com outro provedor escolhido, essas perguntas vão para o Gemini.
- **Respostas de assistente:** 1 a 3 frases faladas, educadas ("Claro, senhor."), citando a fonte quando vierem de pesquisa.
- **Botão ATUALIZAR na tela de bloqueio:** baixa a versão nova do GitHub (`git pull --ff-only`), avisa por voz e reinicia pelo `Iniciar-JARVIS.bat site`; a página recarrega sozinha quando o backend novo sobe (`boot_id` no `/api/health`). Só aceita pedidos do próprio PC e da própria central.
- **App Android 5.0.0:** gerado e servido pelo PC em `/api/mobile` (o app 4.5 antigo só aceitava o link com a chave; o novo conecta com endereço + PIN).

- **Mais tempo para reconhecer:** a verificação facial tenta por até 15 s (era 8), contados depois que a webcam abre; para assim que reconhece. Ajustável por `FACE_TIMEOUT`.

- **Briefing com a pauta desde o início:** o backend manda todos os cards já no `briefing_start` (`plan`); durante a saudação a tela mostra a pauta inteira, e em cada assunto o card dele vira o destaque, com os próximos apagados embaixo.
- **Câmera sem travar na verificação:** o vídeo ao vivo e a análise do rosto rodam separados (antes o vídeo esperava cada detecção, ~155 ms). A detecção usa uma cópia de 320 px e o OpenCV fica em 1 núcleo durante a verificação: com todos os núcleos ele derrubava a webcam de 23 para 3 a 10 fps. Vídeo ao vivo a 15 fps (era 10) e aviso "LIGANDO A CÂMERA…" enquanto a webcam abre (2 a 6 s, pelo driver).

- **Verificação rápida ao abrir:** a central já lê o rosto ao abrir; quem tem perfil entra sozinho na própria central, e rosto não reconhecido destaca "＋ SOU NOVO: CRIAR PERFIL" (o PIN continua disponível). No app do celular segue pelo PIN.
- **Botão LIGAR O JARVIS:** com o JARVIS desligado, a central do site oferece "LIGAR O JARVIS". Ele usa o atalho `jarvis://`, criado só para o seu usuário pelo `Instalar-Botao-Ligar.bat` (desfaz com `Remover-Botao-Ligar.bat`), que roda o `Iniciar-JARVIS.bat site`: liga tudo sem abrir aba nova, e a central já aberta entra sozinha.
- **Botão sem resposta:** se o atalho `jarvis://` não está instalado, o navegador ignorava o clique em silêncio. Agora, quando nada abre em 2,5 s, a tela mostra "O botão ainda não está ativado neste PC" e o passo a passo do instalador. A tela também lembra de permitir o "acesso à rede local" no Chrome, que, se bloqueado, parece o JARVIS desligado.
- **JARVIS do PC desligado:** a central do site mostra "O JARVIS DO SEU PC ESTÁ DESLIGADO" em vez do erro vermelho, confere a cada 2 s e continua sozinha quando o backend responde.

- **Central pelo site:** o botão "Abrir meu JARVIS" abre a própria central em `/app/` no Netlify (o mesmo frontend, sem programa novo). Ela fala com o backend do PC em `127.0.0.1:8000`; o backend aceita o endereço do site no CORS (`JARVIS_SITE_ORIGIN`) e responde ao pedido de rede local do Chrome. Escudos, sons e a tela secundária respeitam a pasta `/app/`.
- **Branding Book no celular:** cada capítulo tinha 900px de largura fixa (regra de desempenho) e gerava rolagem lateral; agora segue a largura da tela, com tabelas roláveis e textos que quebram.

## 5.0.0 — 9 de novembro de 2026

Preparação da V5 para uso e publicação no GitHub.

- **Versão unificada:** `backend/version.py` é a fonte de versão; o build Android grava `versionName` e `versionCode` no manifesto temporário.
- **Meus Sites:** cadastro e edição em Configurações, com apelidos, validação de URL e opção de abrir como app do Chrome; compatível com atalhos antigos.
- **Modo Torcedor:** escudos na central, no bloqueio e no banner, com cache local e reservas; partidas antigas deixam de manter o modo preso e ativações em dia de jogo desligam no dia seguinte.
- **Atualizações:** verificação manual e diária de releases no PC; o Android oferece baixar APK mais novo sem instalar automaticamente.
- **Publicação:** CI em Windows para backend e frontend, workflow de APK assinado por tag e instruções para configurar os secrets em `docs/RELEASE.md`.
- **Jogo inventado pelo Google:** com a agenda da ESPN em dia, o Google Notícias só confirma o jogo; jogos da base, do feminino e listas "Jogos de hoje" não contam mais (antes, num dia sem jogo, aparecia "Palmeiras x Remo · Hoje").
- **Site de apresentação no Netlify:** pasta `site/`, `netlify.toml` e o botão "Abrir meu JARVIS", que leva à central do próprio PC.

## 4.5 — 5 de novembro de 2026

JARVIS no celular, uma central por pessoa e acessibilidade. Detalhes em `docs/ATUALIZACAO-V4.5.md`.

- **App Android (APK):** gerado no PC pelo `Gerar-App-Android.bat`. QR pequeno na Sentinela (modo rede)
  para baixar; pareamento pela central liberada. O QR do bloqueio não leva a chave de acesso.
- **Perfis por pessoa:** "＋ NOVA PESSOA" no bloqueio (o PIN do dono autoriza), foto pela webcam, PIN
  próprio e painel de boas-vindas. Cada pessoa tem os próprios dados; o rosto ou o PIN escolhe o perfil;
  ao bloquear, volta para o dono. Configurações > Pessoas.
- **Acessibilidade:** texto maior (115% / 130%), alto contraste e reduzir movimento, em todas as telas;
  contorno de foco visível no teclado.
- Apagado o `_backup_codigo`. Versão 4.5.
- **6 nov (última leva):** `Iniciar-JARVIS.bat` já abre com a rede; app pareia pelo PIN ("ABRIR O JARVIS"), com
  avisos no celular, microfone nativo e layout de celular; microfone padrão sem pergunta; abre com o briefing (e
  pergunta se repete); histórico do chat; memória de longo prazo ("lembre que…"); arquivos (lixeira, mover, criar
  pasta) e WhatsApp, sempre com confirmação; finanças sem banco; branding book sem travar.

## 4.4 — 4 de novembro de 2026

Central em espera limpa e cabeçalho novo. Detalhes em `docs/ATUALIZACAO-V4.4.md`.

- **Em espera só com o orbe:** depois da entrada, a coluna da direita (clima e Canal Ativo) recolhe
  junto com a telemetria. Ela não reabre mais a cada fala do JARVIS, só quando você fala ou envia
  um pedido. Ao fechar a fileira do briefing, a central volta para esse modo limpo, com a faixa
  DIGA: de atalhos.
- **Cabeçalho em três zonas:** menu ☰, logo e "ASSISTENTE PESSOAL · v4.4" à esquerda; CONTROLES no
  centro exato; status "SISTEMA ONLINE · VOZ LIVRE" (muda com a voz), relógio com data, ÁUDIO e
  SPOTIFY agrupados, SAIR e perfil à direita.
- A tela de bloqueio e a tela extra mostram a versão certa (antes, "v4.2.2" fixo).
- **Fundo blueprint (5 nov):** azul de planta técnica com grade dupla na central, no bloqueio e na
  inicialização; moldura com régua, círculo de cota no orbe e carimbo "J.A.R.V.I.S. · FOLHA" no
  bloqueio. Verde no Modo Torcedor. Volta ao antigo em Configurações > Geral > Fundo > Clássico.
- **Inicialização mais rápida (5 nov):** o Iniciar-JARVIS.bat usa a interface já compilada num
  servidor leve (sem Node e sem compilar a cada abertura) e só refaz o build quando o código muda;
  abre o painel assim que tudo responde, sem esperas fixas; o backup diário roda depois de abrir.
  A voz (edge-tts) passou a carregar em segundo plano e deixou de segurar a subida do backend.
- **Reator Arc em destaque (5 nov):** invólucro escuro, halo que respira e núcleo mais forte sobre
  a planta; na Sentinela não é mais escurecido.
- **Modo Torcedor com jogo de verdade (5 nov):** agenda e placar da ESPN e confirmação pelo Google
  Notícias, sem IA e sem token (saiu a agenda inventada). Liga sozinho no dia do jogo e desliga no
  dia seguinte; comemora gol em tela cheia; placar no bloqueio. Na planta, o fundo fica azul e só o
  layout fica verde.
- **Branding Book v1.3:** capítulo "Planta e Modo Torcedor" e cores da planta com contraste medido.
- **Modo Torcedor no bloqueio (5 nov):** painel do jogo com escudos, tempo, gols com autor e
  assistência, estatísticas, tabela e próximo jogo; gol com o nome de quem marcou; intervalo e fim de
  jogo anunciados uma vez. Corrigida a fala repetida ao abrir com o jogo rolando. Branding Book v1.4.
- **Botão do Modo Torcedor no bloqueio (5 nov):** ao lado do carimbo, funciona com a central
  bloqueada. Os testes do backend não gravam mais nos arquivos reais de `data/` (um deles desligava o
  Modo Torcedor de verdade). Branding Book v1.5.
- **Iniciar-JARVIS.bat substitui a versão aberta (5 nov):** antes, com o JARVIS já aberto, a versão
  nova falhava escondida e a antiga seguia (por isso o botão não trocava). O botão agora avisa quando
  falha.

## 4.3 — 4 de novembro de 2026

Briefing "bom dia" em etapas, com base na análise do vídeo de referência. Detalhes em
`docs/ATUALIZACAO-V4.3.md`.

- **Um "bom dia" dispara tudo:** o JARVIS abre dizendo se há algo urgente ("Sem desvios relevantes"
  ou "Atenção a N pontos"), fala de clima, agenda, e-mails, notícias e saúde, e fecha com uma
  recomendação do dia. Cada assunto entra na tela como um card enquanto ele fala.
- **Abas com progresso** (Clima, Agenda, E-mails, Notícias, Prioridades) e texto de etapa
  ("Verificando e-mails importantes...").
- **Em espera:** ao terminar, os cards ficam numa fileira no centro e a prontidão fisiológica no canto
  esquerdo, até você fechar (✕). Cancelar no meio guarda os cards já falados.
- **Cards novos:** clima detalhado (mínima, máxima, sensação, chuva, vento), agenda (Google Agenda +
  lembretes, com estado "Agenda livre"), triagem de e-mail, notícias por tema com "Abrir matéria" e
  saúde sob demanda.
- **Triagem de e-mail (opcional):** lê só os cabeçalhos da caixa de entrada por IMAP, sem marcar como
  lido, e conta quantos pedem ação (fatura, prazo, confirmação, segurança). Configure `EMAIL_IMAP_*`.
- **Notícias por tema:** tecnologia, novos modelos de IA e política, citando a fonte na fala.
- **Privacidade:** dados de saúde nunca são lidos em voz alta; o card só diz quantas leituras existem.
- **Mais interativo, como no vídeo:** a central fica limpa (laterais escondidas) durante o
  briefing, o orbe fica centralizado, sua foto aparece nele, cada fala entra ao vivo no Canal Ativo
  e como legenda, o card atual fica largo no centro com os já falados em fileira logo abaixo
  (cards baixos, de altura fixa), cada aba tem a
  própria barra de progresso, **PRÓXIMO ▸** (ou →) pula o assunto, e na fileira final dá para
  ampliar, esconder e reexibir cards em **Gerenciar HUD**. Nova rota `POST /api/briefing/skip`.
- **Telas por assunto:** "notícias", "notificações", "e-mails", "agenda", "clima", "tarefas", "meus
  dados de saúde" e "comandos" abrem o mesmo palco com um card por item. A faixa **DIGA:** embaixo do
  orbe (e na fileira final) mostra as frases, e clicar nelas envia o comando.
- Página de demonstração `frontend/briefing-demo.html` (só no modo dev) para ver o briefing sem
  desbloquear a central.
- **"Boa noite" com cards:** fechamento do dia no mesmo formato, com tarefas pendentes, agenda e
  lembretes de amanhã, clima de amanhã, água de hoje e anotações de hoje, e uma dica para a noite.
- Corrigido: "boa noite, resumo do dia" e "boa noite, como foi meu dia" abriam o resumo da manhã; o
  resumo da noite não listava o nome das tarefas pendentes.
- Corrigido: a data do resumo saía com o mês em inglês no Windows; o botão da tela Briefing (menu
  Telas) não enviava o comando e gerava o resumo duas vezes.

## 4.2.2 — 30 de outubro de 2026

Ajustes finos pedidos depois de testar a 4.2, mais o que faltava do Branding Book.
Detalhes e testes em `docs/ATUALIZACAO-V4.2.2.md`.

### Tela de bloqueio e central
- O microfone da tela de bloqueio **começa silenciado** (escuta do Sentinela e palmas). A tecla **P** ou um clique no botão liga e desliga. Ao voltar para o bloqueio, silencia de novo.
- A coluna da direita (Clima e Canal Ativo) **recolhe sozinha após 3 minutos sem uso**, como Telemetria & Serviços, e reabre quando você fala ou o JARVIS responde. Botões RECOLHER e "◀ CLIMA & CANAL ATIVO".
- No Modo Sentinela, **"abrir central"**, "liberar", "desbloquear" ou "entrar" vão direto para o escaneamento do rosto, com ou sem "Jarvis" na frente (antes, sem "Jarvis" o pedido era ignorado, e com "Jarvis" ele ainda tentava abrir um programa "central" depois de entrar).
- Cartão **"Tocando agora"** do Spotify: capa, música, artista e progresso embaixo do clima, na tela de bloqueio (só mostra; pode desligar em Configurações > Bloqueio) e na central (com voltar, tocar/pausar e avançar).
- Textos "Stark" que sobraram na interface trocados por JARVIS v4.2.2.

### Sons por estado
- Novos sons curtos para **ouvindo, sucesso, erro e repouso** (todos com até 400 ms, sintetizados, sem arquivos).
- Volume geral e modo **Todos / Só o que importa / Desligado** em Configurações > Mídia & Foco, com botões de prévia.
- Das 22h às 7h só tocam os sons importantes (erro e alerta), com metade do volume. O modo silencioso cala tudo.
- Corrigido: o aviso da pergunta de modo de pesquisa chamava um som que não existia.

### Carregamento, vazio e sem conexão
- Blocos esqueleto no lugar de "Carregando..." em clima, agenda, Spotify, finanças e notícias (sem brilho com "reduzir movimento").
- Estados vazios com ícone, frase curta e ação (ex.: "Agenda livre", "Nada tocando agora").
- Faixa âmbar no topo quando o servidor cai ("Tentando reconectar sozinho…") e verde quando volta.
- A aba do navegador mostra o estado: "● Ouvindo", "◐ Pensando", "◉ Falando", "🔒 Bloqueado".

### Versão, diagnóstico e backup
- Versão única **4.2.2** em `/api/health`, no FastAPI, no topo da central e no widget Sobre mim (`backend/version.py` e `frontend/src/utils/version.js`, conferidas por teste).
- **Copiar diagnóstico** (Configurações > Geral): versão, sistema, integrações configuradas (só sim/não) e últimos eventos, sem chaves, PIN nem o texto dos seus pedidos. Rota `GET /api/diagnostics`.
- **Exportar e importar ajustes** em JSON (`GET /api/prefs/export`, `POST /api/prefs/import`), com as mesmas validações de sempre. Não leva chaves, rosto, memórias nem o índice da câmera.

### Marca
- Kit de logo em `frontend/public/brand/`: avatar (512 e 1024), banner 1500×500, imagem de compartilhamento 1200×630 e o nome em traço (SVG e PNG). Gerado por `scripts/dev/gerar_kit_logo.py`.
- Tela de boas-vindas com o Núcleo animado (anéis entram girando, núcleo acende) e o nome se desenhando em traço.
- Branding Book atualizado (sons, kit de logo, carregamento) com a assinatura do autor; capítulo das versões antigas reservado.

## 4.2 — 30 de outubro de 2026

Foco em documentação e otimização. Nenhum comportamento visível mudou, a não ser onde indicado.

### Código mais organizado
- `backend/main.py` foi de 2.319 para cerca de 95 linhas: as 84 rotas foram para `backend/routes/` (uma por área) e o motor de conversa, a fala e o estado para `backend/core/`.
- `frontend/src/App.jsx` perdeu o cliente da API, o tema, a conexão em tempo real, o indicador de busca e o painel de água, agora em `utils/` e `hooks/`.
- A cotação de moedas, antes buscada em três lugares, ficou em `services/quotes.py`. Clima, cotação e notícias passam por um cliente HTTP único com tempo limite, nova tentativa e cache curto.
- Lint configurado (`ruff` no backend, ESLint e Prettier na interface) e imports sem uso removidos.

### Mais rápido
- Nenhuma chamada de rede trava mais o servidor: notícias do Modo Torcedor e leitura de CPU rodam em segundo plano (um teste impede que isso volte).
- Os clientes de IA são reaproveitados entre perguntas, sem refazer a conexão a cada vez.
- A primeira parte da fala é curta, para o som começar antes; a pausa entre partes caiu de 0,35 s para 0,2 s; frases fixas tocam do cache de voz.

### Mais leve em segundo plano
- Dez buscas periódicas param com a aba oculta e atualizam ao voltar. O painel de status atualiza a cada 10 s (era 5 s).
- Sete relógios dividem um único timer.
- Configurações, modais, monitores e Telas são carregados só quando abertos (pacote inicial cerca de 27% menor).
- Câmera ao vivo mais leve: 10 quadros/s, 400 px, qualidade 65 (ajustável no `.env`).

### Visível para o usuário
- Botão **MODO SENTINELA** no menu ⚡ CONTROLES.
- Tela de Finanças avisa quando a cotação está sem conexão e mostra valores de referência.
- Lembrete de água a cada 2 horas por padrão (configurável), clima à direita e reator centralizado na tela de bloqueio.

### Funcionalidades novas (aba Automação)
- **Gatilhos condicionais:** chuva amanhã, jogo começando, processador alto e água atrasada (configuráveis; sem voz entre 22h e 7h).
- **Protocolos:** "protocolo trabalho" roda uma lista de passos seguros (abrir, foco, volume, playlist, silencioso, frase). Editáveis e testáveis em Configurações.
- **Leitura de tela:** "o que é esse erro na tela?" captura a tela só na hora e pergunta à IA; nada é salvo.
- **Sugestões pela rotina:** ações repetidas no mesmo horário em 3 dias viram uma pergunta ("quer que eu ative?"); nunca age sem um "sim".
- **Arquivos por voz:** busca nas pastas pessoais, abrir ou mostrar na pasta, e "organiza a pasta Downloads" com confirmação e desfazer.
- **Central de notificações (experimental):** lê as notificações do Windows com pacotes opcionais (`backend/requirements-notificacoes.txt`); desligada por padrão.

### Branding aplicado
- Logo "Núcleo" no topo da central e como ícone da aba do navegador (`frontend/public/jarvis-logo.svg`).
- Paleta como tokens CSS (`frontend/src/brand.css`) e tema azul padrão ajustado para ela.
- Tipografia: Inter nas respostas e JetBrains Mono no relógio, além de Orbitron e Rajdhani.
- Estados do orbe: repouso com brilho baixo, ouvindo, processando, falando em âmbar, flash verde ao concluir uma ação e vermelho com tremida curta em erro (sem movimento com "reduzir movimento").
- Tom de voz: prompt da IA e frases fixas ajustados (formal e cordial, frases curtas, sem gírias e sem excesso de exclamações). O Modo Torcedor mantém o próprio estilo.

### Documentação
- Novos: `docs/ARQUITETURA.md`, `docs/API.md` (gerado do código por `scripts/dev/gerar_api_md.py`), `docs/COMANDOS.md`, `docs/CONFIGURACAO.md` e este changelog. README reescrito; o antigo ficou em `docs/README-v4.1-completo.md`.

## 4.1 — 29 de outubro de 2026

Palmas para acordar o JARVIS (com a página aberta ou fechada), câmera ao vivo no orbe, bloqueio real no backend, PIN, registro de tentativas, resumo do dia, cartões da tela de bloqueio, bloqueio por ausência, modo visitante, música de abertura, água animada e Modo Sentinela. Detalhes em [docs/ATUALIZACAO-V4.1.md](docs/ATUALIZACAO-V4.1.md).

## 4.0

Base anterior: HUD com reator, widgets flutuantes, painel de configurações, integrações com Spotify e Google Agenda, Modo Torcedor, hidratação e pesquisa profunda.
