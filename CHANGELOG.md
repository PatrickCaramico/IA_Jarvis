# Changelog

Mudanças do JARVIS por versão, da mais nova para a mais antiga.

## 10 de novembro de 2026

- **Verificação rápida ao abrir:** a central já lê o rosto ao abrir; quem tem perfil entra sozinho na própria central, e rosto não reconhecido destaca "＋ SOU NOVO: CRIAR PERFIL" (o PIN continua disponível). No app do celular segue pelo PIN.
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
