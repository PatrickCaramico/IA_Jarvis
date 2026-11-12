# Changelog

Mudanças do JARVIS por versão, da mais nova para a mais antiga.

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
