# Atualização V4.5: JARVIS no celular, uma central por pessoa e acessibilidade

5 de novembro de 2026. Feita a partir de três áudios do Patrick (transcritos no próprio PC, com o
Whisper local; a voz não saiu do computador).

## O que muda para você

### JARVIS no celular (app Android)

- **App de verdade:** `mobile\dist\JARVIS.apk` (61 KB), gerado no PC pelo **Gerar-App-Android.bat**.
  É uma tela só com a sua central dentro, em tela cheia, com microfone, e abre os links de fora (notícias,
  agenda) no navegador do celular.
- **QR pequeno na Sentinela:** com o JARVIS aberto pelo **Iniciar-JARVIS-Rede.bat**, o canto inferior
  esquerdo do bloqueio mostra "JARVIS NO CELULAR". Escaneie com a câmera do celular para abrir a página de
  download e instalar o app.
- **Pareamento:** com a central liberada, abra **JARVIS no celular** > aba **App Android**, escaneie o QR
  e toque em **Abrir no app JARVIS**. O app guarda a conexão e, daí em diante, abre direto.
- **Segurança:** o QR do bloqueio **não leva a chave de acesso**. Quem só vê a tela bloqueada consegue baixar
  o app, mas não entra no JARVIS. O pareamento só aparece com a central liberada, e o celular continua
  precisando do rosto ou do PIN quando o PC está bloqueado. Tudo funciona só na Wi-Fi de casa.
- Na aba **Navegador** continua o QR de antes, para abrir a central no navegador do celular.

### Uma central por pessoa (perfis com rosto + PIN)

- **＋ NOVA PESSOA** no bloqueio: o dono autoriza com o PIN dele (se tiver PIN), a pessoa diz o nome, tira
  a foto pela webcam (ou escolhe um arquivo) e cria um PIN próprio (opcional).
- Em seguida aparece o painel **Bem-vindo**, onde ela escolhe Modo Torcedor (e se liga sozinho em dia de
  jogo), fundo, cor dos destaques e se o JARVIS fala ou só escreve.
- **Cada pessoa vê só o que é dela:** preferências, rosto, PIN, memória, tarefas, lembretes, rotina, notas,
  atalhos, "sobre mim", Google Agenda, Spotify, eventos, água e saúde ficam em `data\perfis\<nome>\`. O seu
  perfil (o principal) continua usando os arquivos de sempre, sem migração.
- **O rosto escolhe o perfil:** no bloqueio, o JARVIS compara com o rosto de todas as pessoas e entra no
  perfil de quem está na frente. O PIN também descobre de quem é.
- **No seu PC fica você:** ao bloquear (botão sair, ausência, voz ou visitante), o JARVIS volta sozinho para
  o perfil principal.
- **Configurações > Pessoas:** lista quem tem perfil neste PC. Só o perfil principal remove alguém (apaga a
  pasta da pessoa, com confirmação).
- O limite de tentativas de PIN é um só para o PC inteiro (conta no PIN do perfil principal), então mais
  pessoas não viram mais chances para quem tenta adivinhar.

### Acessibilidade

- **Configurações > Acessível:** tamanho do texto (100%, 115% ou 130%), **alto contraste** (painéis bem mais
  escuros, bordas brancas, nenhum texto apagado, planta mais escura) e **reduzir movimento** (para o orbe, o
  brilho da planta e as comemorações). Valem em todas as telas, inclusive no bloqueio, e já na abertura.
- **Teclado:** todo botão ganha um contorno amarelo bem visível ao navegar com Tab.
- Cada pessoa tem as próprias opções de acessibilidade.

### Pastas e abertura

- Apagado o `_backup_codigo` (cópias de 30/10 do `main.py` e do `App.jsx`, já substituídas pelo código atual).
- O projeto já era enxuto: quase todo o peso é o `venv` do Python (332 MB) e o `node_modules` (50 MB), que
  são necessários. O maior ganho de velocidade que sobra é **tirar a pasta do OneDrive**, que sincroniza esses
  380 MB e deixa a primeira abertura mais lenta. Ficou anotado como sugestão (não foi movido).
- Versão **4.5** no `/api/health`, na central, no bloqueio, no app e no carimbo da planta.

## Última leva (6 de novembro)

- **Um `.bat` só:** o `Iniciar-JARVIS.bat` já abre com a rede de casa (celular e app). O
  `Iniciar-JARVIS-Rede.bat` virou só um atalho para ele. Outros aparelhos continuam precisando da chave.
- **App que não abria (o "loop"):** depois de baixar, a página só oferecia baixar de novo, e o app recém-instalado
  não sabia onde estava o PC (era preciso um segundo QR dentro da central). Agora: escaneie o QR do **📱 CELULAR**,
  baixe, toque em **ABRIR O JARVIS** na mesma página e digite o **PIN** do perfil principal. Pronto. O endereço do PC
  também aparece no cartão do 📱 CELULAR, se precisar digitar. Pareamento pelo PIN só no modo rede, conta no limite de
  tentativas e não funciona se o PC não tiver PIN.
- **Avisos no celular** (lembretes, água, avisos, Modo Torcedor), **microfone nativo do Android** no app, **entrada pelo
  PIN** no bloqueio do celular e **layout de uma coluna** no celular.
- **Microfone sem pergunta:** a janela de escolher microfone não abre mais a cada entrada. O JARVIS usa o padrão (ou o
  último escolhido); para trocar: Configurações › Mídia & Foco › 🎙 Microfone (ou o menu do perfil).
- **Abertura com o briefing:** primeira entrada do dia, o briefing começa sozinho ("bom dia" até 18h, "boa noite"
  depois). Nas próximas, uma caixa pergunta "Quer que eu repita o briefing?" (REPETIR/Enter, PULAR/Esc ou pela voz).
  O resumo antigo, que esperava clima, tarefas e outros dados antes de falar, saiu.
- **Histórico do chat:** o Canal Ativo abre com as últimas conversas (esmaecidas, com a linha "CONVERSAS ANTERIORES").
- **Memória de longo prazo:** "lembre que…", "o que você lembra de mim?", "esqueça…". A IA também recebe as últimas
  conversas das sessões anteriores.
- **Arquivos:** lixeira (Lixeira do Windows), mover e criar pasta, sempre com o seu "sim" e só nas pastas pessoais.
- **WhatsApp:** monta a mensagem e, no "sim", abre o WhatsApp com tudo pronto; você toca em enviar. Contatos por voz.
- **Finanças sem banco:** gastos e entradas por voz ou na tela Finanças, com totais e categorias. Saíram os números
  inventados que a tela mostrava (reserva, investimentos, "IBOVESPA ESTÁVEL").
- **Branding book rápido:** de 19 para ~86 fps na rolagem (o orbe de fios só anima na tela e sem desfoque pesado;
  páginas fora da tela não são desenhadas).
- Testes não gravam mais em `data/`; testes do Modo Torcedor não dependem mais da hora do dia.

**Ainda não testado num celular de verdade:** o APK novo (73 KB) foi montado e assinado, mas o teste de verdade é no seu
Android: instalar, ABRIR O JARVIS, PIN, avisos e microfone.

## Para quem mexe no código

| Arquivo | O que mudou |
| --- | --- |
| `mobile/android/` (novo) | App Android: `AndroidManifest.xml` (pacote `com.patrick.jarvis`, Android 7+, link `jarvis://`), `MainActivity.java` (WebView com microfone, endereço salvo, links de fora no navegador, menu do botão voltar) e `assets/setup.html` (tela de conexão no estilo planta). |
| `scripts/android/build_apk.ps1`, `Gerar-App-Android.bat` (novos) | Monta o APK sem Gradle (aapt2, javac, d8, zipalign, apksigner), numa pasta só-ASCII em `%USERPROFILE%\.jarvis-android`, com ícones gerados do avatar e sempre a mesma chave (para atualizar por cima). |
| `backend/routes/mobile.py` (novo) | `/api/mobile` (página de download), `/api/mobile/app.apk`, `/api/mobile/pair` (pareamento, exige token e central liberada) e `/api/mobile/info` (QR do bloqueio, sem token). |
| `backend/main.py` | Download e APK abrem sem token no modo rede (só GET nessas duas rotas); routers `mobile` e `profiles`. |
| `backend/routes/system.py` | `local_ip()` reaproveitável; `/api/network-access` devolve também os links do app. |
| `backend/modules/profiles.py` (novo) | Registro `data/perfis.json`, pastas por pessoa, troca de perfil (aponta os caminhos de 18 arquivos pessoais), `face_refs()`, `match_pin()` e `owner_pin_ok()`. |
| `backend/routes/profiles.py` (novo) | `GET /api/profiles/lock-info` (pública, sem nomes), `GET/POST /api/profiles`, `DELETE /api/profiles/{id}`. |
| `backend/modules/face.py` | `verify_against_profile(..., refs)` reconhece entre várias pessoas e devolve `profile_id`. |
| `backend/routes/access.py`, `backend/modules/access.py` | Login escolhe o perfil pelo rosto ou pelo PIN; bloquear volta ao dono. |
| `backend/modules/prefs.py`, `routes/profile.py` | `a11y_text_scale`, `a11y_high_contrast`, `a11y_reduce_motion` (públicas, para o bloqueio). |
| `backend/modules/briefing.py` | Notas do briefing lidas do perfil ativo. |
| `frontend/src/components/MobileAppQr.jsx`, `NewProfileScreen.jsx`, `ProfileWelcome.jsx` (novos) | QR da Sentinela, cadastro de pessoa nova e boas-vindas. |
| `frontend/src/components/settings/PeopleSettings.jsx`, `AccessibilitySettings.jsx` (novos) | Abas Pessoas e Acessível. |
| `frontend/src/components/NetworkQrModal.jsx` | Abas "App Android" e "Navegador". |
| `frontend/src/profiles.css`, `accessibility.css` (novos), `blueprint.css`, `utils/theme.js` | Estilos e `applyAccessibility()` / `initialAccessibility()`. |
| `backend/tests/test_mobile_45.py`, `test_profiles_45.py` (novos) | 9 testes: QR sem token, download, celular sem token só baixa, pareamento, dados separados, volta ao dono, PIN do dono para criar, PIN escolhe a pessoa e conta no dono, só o dono remove. |

## O que não foi testado

- **O APK não foi instalado num celular** (não há celular nem emulador neste PC). Ele foi montado, assinado e
  conferido (`aapt2 dump badging` e `apksigner verify`), mas o primeiro teste de verdade é no seu Android.
- **O reconhecimento entre várias pessoas** foi testado com a câmera simulada; com rostos reais, vale testar
  com a segunda pessoa na frente da webcam.

Conferido: 180 testes do backend, 53 do frontend, lint e build passam. Telas novas conferidas na página de
demonstração (`frontend/lock-demo.html?screen=newprofile`, `?screen=welcome`).
