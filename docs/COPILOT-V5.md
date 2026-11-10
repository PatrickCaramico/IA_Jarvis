# JARVIS V5 — o grande lançamento (instruções para o GitHub Copilot)

> Leia este arquivo inteiro antes de qualquer ação. Ele vale para toda esta conversa.
> Repositório: https://github.com/PatrickCaramico/IA_Jarvis

## Projeto

Assistente pessoal local, em português (BR), rodando no Windows. Versão atual: **4.5** (app Android 4.5.1).
- Backend: Python + FastAPI (porta 8000). `backend/main.py`, rotas em `backend/routes/`, lógica em
  `backend/modules/`, laços em segundo plano em `backend/core/watchers.py`, IA em
  `backend/services/llm_orchestrator.py`, configuração em `backend/config/settings.py`, versão em `backend/version.py`.
- Frontend: React + Vite + Tailwind (porta 5173). `frontend/src/App.jsx`, `frontend/src/components/`,
  `frontend/src/hooks/`, configurações em `frontend/src/components/settings/`.
- App Android: `mobile/android/` (Java puro, sem Gradle), gerado por `scripts/android/build_apk.ps1`
  (`Gerar-App-Android.bat`). O PC serve o APK em `/api/mobile/app.apk` (`backend/routes/mobile.py`).
- Documentação: `docs/` (API, ARQUITETURA, COMANDOS, CONFIGURACAO, BRANDING-BOOK) e `CHANGELOG.md`.

## Regras (iguais às da Fase 1)

- Faça **só o item pedido**. Não refatore nem renomeie nada fora dele.
- **Nunca** leia, edite ou mostre o `.env`. Não adicione dependências sem perguntar.
- Antes de editar, diga **quais arquivos** vai alterar e **o que** vai mudar.
- O que já funciona não pode quebrar. Rode os testes existentes antes de dizer que terminou.
- Textos de interface e logs em português do Brasil, **com acentuação correta**, no estilo dos existentes.
- Ao terminar: diga **como testar** e espere minha confirmação antes do próximo item.
- Valide com `python -m py_compile` e `pytest` (backend) e `npm run build` e `npm test` (frontend).
- **Não faça commit, push nem apague arquivos.** Eu faço o commit depois de testar. Se algo precisar ser removido, pergunte.
- **Não altere** a pasta `data/`, os arquivos `.bat`, as portas (8000 e 5173) nem as origens do CORS sem me avisar antes.
- **Preserve o final de linha de cada arquivo** (alguns usam CRLF) e salve tudo em UTF-8.
- **Se achar outro problema fora do item pedido, só me avise.** Não corrija por conta própria.
- **Se algo estiver ambíguo, pergunte** (no máximo 3 perguntas) em vez de adivinhar.
- **Nunca registre** chaves, tokens, PIN ou conteúdo de notas no `event_log` nem no console.
- **Nada de segredo no repositório:** chave de assinatura do APK (`.jks`), senhas, tokens e o `.env` ficam fora do git, sempre.
- Toda mudança visual (cor, tela, estado, som, texto da interface) entra numa lista **"Mudanças visuais"** na
  sua resposta final. Não edite o Branding Book; ele será atualizado depois com essa lista.

## Armadilhas conhecidas deste projeto

- Estou no **Windows**: use PowerShell/`cmd`. O caminho da pasta tem **espaços e acentos** ("Área de Trabalho"): sempre use aspas.
- O backend sobe com `--host 0.0.0.0` (necessário para o celular). Não mude isso.
- Em `backend/modules/tools.py`, a **ordem** dos handlers em `_HANDLERS` importa: um handler novo pode "roubar"
  comandos de outro. Hoje `_h_custom_shortcut` vem antes de `_h_open`. Se criar um handler, diga onde vai colocá-lo.
- O `.env` é lido só na inicialização: mudanças nele ou em `settings.py` exigem reiniciar o backend.
- Os dados são **por pessoa** (`backend/modules/profiles.py` troca os caminhos, inclusive o de `atalhos.json`).
  Qualquer arquivo novo de dados do usuário precisa entrar nessa troca.
- Rotas que mudam estado ficam bloqueadas com a central bloqueada (403). Rotas novas seguem a mesma regra,
  a não ser que eu peça o contrário.
- As ferramentas do Android falham com caminhos acentuados; por isso o `build_apk.ps1` compila numa pasta só-ASCII. Mantenha isso.
- Os testes do backend não podem gravar nos arquivos reais de `data/` (use as fixtures do `backend/tests/conftest.py`).

## Formato da resposta ao terminar cada item

1. Arquivos alterados (lista).
2. O que mudou, em 3 a 5 linhas.
3. Como testar, passo a passo, incluindo o que devo ver na tela.
4. Mudanças visuais (se houver).
5. Riscos ou dúvidas que ficaram.

---

## Bloco A — Preparar o repositório para o GitHub

### 0. Conferir a Fase 1 (somente análise)
**Não altere nada.** Leia `docs/COPILOT-FASE1.md` e diga, item por item (1 a 8), se já está feito, parcial ou
não feito, citando o arquivo e a função que comprovam. Os itens não feitos que eu escolher entram depois do Bloco C.

**Pronto quando:** recebo a tabela, sem nenhum arquivo alterado.

### 1. Higiene do repositório antes do primeiro push
Revisar o `.gitignore` e o que vai subir. Hoje faltam, entre outros:
- `mobile/dist/`, `*.apk`, `*.idsig`, `*.jks`, `*.keystore` (o APK e a chave de assinatura nunca sobem);
- `backend/.pytest_cache/`, `backend/.ruff_cache/`, `.pytest_cache/`, `.ruff_cache/`;
- `data/fan_cache.json` e `data/fan_news_cache.json` já estão cobertos por `data/*`; confirme.

Depois, **só me avise** (não apague nem mova):
- `data/atalhos.json` é versionado, mas tem um caminho pessoal (`c:\Users\patri\...`). Proponha um
  `data/atalhos.example.json` sem dados pessoais, usado quando o `atalhos.json` não existir.
- `JARVIS-LinkedIn.pdf` (4 MB) e `legenda-linkedin.txt` estão repetidos na raiz e em `docs/linkedin/`.
- `backend/Iniciar-JARVIS.bat` está vazio.
- Liste qualquer arquivo com mais de 1 MB que iria para o repositório.

**Pronto quando:** recebo a lista do que sobe e do que fica de fora, e o `.gitignore` atualizado. Nenhum segredo,
dado pessoal, log, cache, build ou APK entra no repositório.

### 2. Uma versão só: 5.0.0
Hoje a versão está espalhada: `backend/version.py` ("4.5"), `frontend/package.json` ("1.0.0"),
`frontend/src/utils/version.js` e o `AndroidManifest.xml` (`versionName` 4.5.1, `versionCode` 46).
- `backend/version.py` passa a ser a fonte única: `VERSION = "5.0.0"`.
- O `build_apk.ps1` lê a versão de `backend/version.py` e escreve `versionName` e `versionCode` no manifesto
  da **pasta de trabalho** (não no arquivo original). O `versionCode` só pode subir (ex.: 5.0.0 → 500; precisa
  ser maior que 46).
- O frontend continua mostrando a versão que vem de `/api/health` (ou do `version.js`, se for assim hoje); diga qual.

**Pronto quando:** a central, o bloqueio, o `/api/health`, a página `/api/mobile` e o app instalado mostram 5.0.0,
e o celular aceita o APK novo por cima do 4.5.1 sem desinstalar.

---

## Bloco B — Melhorias da V5

### 3. "Meus Sites": abrir qualquer site do navegador por voz
Hoje o `_h_open` (`tools.py`) abre o que está em `data/atalhos.json` (nome → URL ou programa), e o usuário só
consegue mudar essa lista editando o arquivo na mão. Os atalhos de vários itens (`custom_shortcuts` em `prefs.py`)
são outra coisa e continuam como estão.

**Backend**
- Rotas novas: `GET /api/sites`, `POST /api/sites`, `PUT /api/sites/{nome}`, `DELETE /api/sites/{nome}`.
  Bloqueadas com a central bloqueada.
- Guardar em `data/atalhos.json`, **mantendo compatível** com o formato atual: um valor pode continuar sendo texto
  (`"gmail": "https://mail.google.com"`) ou passar a ser objeto
  (`{"url": "...", "apelidos": ["email", "correio"], "janela_app": false}`). O `_load_shortcuts` aceita os dois.
- Validar a URL: só `http://` e `https://`. Recusar `file:`, `javascript:`, `data:` e qualquer outro esquema.
  Programas locais (`notepad`, `code`...) continuam funcionando só pelo arquivo, não por essa tela.
- Apelidos: "abre o correio" abre o Gmail se "correio" for apelido. Nome e apelidos sem acento e sem diferença de
  maiúsculas, como o `_norm` já faz. Dois sites não podem ter o mesmo nome ou apelido (erro 409 com mensagem clara).
- Opção "abrir como aplicativo": abre em janela própria do Chrome (`chrome --app=URL`); se o Chrome não for
  encontrado, abre no navegador padrão, sem erro.
- Comando de voz "quais sites você abre?" / "meus sites": responde com a quantidade e os 5 primeiros nomes.
- Se o pedido não for encontrado, a resposta atual já sugere adicionar o atalho: troque por
  "Não conheço esse site. Adicione em Configurações > Meus Sites."

**Frontend**
- Nova seção **Configurações > Meus Sites** (seguir o padrão de `components/settings/`): lista com ícone do site
  (favicon por `https://www.google.com/s2/favicons?domain=...&sz=64`, com a inicial como reserva se falhar),
  nome, apelidos, URL, chave "abrir como aplicativo", botões **Testar**, **Editar** e **Remover**
  (remover pede confirmação).
- Formulário "Adicionar site": nome, URL, apelidos separados por vírgula. Se a URL vier sem `https://`, completar.
- **Opcional (pergunte antes):** botão "Importar favoritos do Chrome", que lê o arquivo local `Bookmarks` do Chrome
  (`%LOCALAPPDATA%\Google\Chrome\User Data\Default\Bookmarks`, JSON), mostra a lista com caixas de seleção e
  adiciona só os escolhidos. Nada é importado sem eu marcar.

**Testes:** formato antigo e novo convivendo; apelido; URL perigosa recusada; nome repetido (409); 403 com a central
bloqueada; "abre X" de um site adicionado pela tela, sem reiniciar o backend.

**Pronto quando:** adiciono um site pela tela, digo "Jarvis, abre <nome ou apelido>" e ele abre no navegador; o
que já abria antes (YouTube, Gmail, Spotify no app do PC, programas locais) continua abrindo igual.

### 4. Modo Torcedor: escudos que não aparecem
Hoje o backend já pega os escudos da ESPN (`_logo` em `sports_provider.py`, campo `logos.ours`/`logos.theirs`),
mas:
- o `FanScoreWidget.jsx` não mostra escudo nenhum;
- o `FanLockPanel.jsx` esconde a imagem quando o link da ESPN falha (`onError` → `visibility: hidden`), e fica o buraco;
- sem internet, ou se a CDN da ESPN bloquear, não há escudo.

Fazer:
- Backend: `GET /api/fan/logo/{lado}` (`ours`/`theirs`) que baixa o escudo da ESPN uma vez, guarda em
  `data/fan_logos/<id_do_time>.png` e serve dali (mesmo sem internet). Liberada com a central bloqueada, como as
  outras rotas do Modo Torcedor. Só aceitar links de `a.espncdn.com`.
- Reserva: nosso time usa o escudo local (`badge_url` em `fan_mode.py`, `/fan/palmeiras/palmeiras_shield.png`);
  o adversário usa um círculo com a inicial (o estilo `flp-crest-empty` que já existe).
- Mostrar os escudos no `FanScoreWidget`, no `FanLockPanel` e no `FanMatchBanner`, sempre pela rota nova.

> Observação para o Patrick: a "Imagem 1" citada não veio junto com o pedido. Anexe-a quando passar este item ao
> Copilot, para ele confirmar em qual tela o escudo some.

**Pronto quando:** os dois escudos aparecem na central, no bloqueio e no banner; com a internet desligada eles
continuam aparecendo (depois de terem sido vistos uma vez); se um falhar, aparece a reserva, nunca um espaço vazio.

### 5. Modo Torcedor: jogo que já passou continua na tela
Sintoma: o dia do jogo passou, mas a central continua no Modo Torcedor, mostrando o jogo antigo.

Causas prováveis no código (confirme antes de mexer e diga qual reproduziu):
- `_fan_auto_mode` (`backend/core/watchers.py`) só desliga sozinho o que **ele mesmo** ligou (`by_auto`). Se o modo
  foi ligado pelo botão do bloqueio ou por voz no dia do jogo (`routes/fan.py` grava `by_auto=False`), ele nunca
  desliga.
- `_pick_match` (`sports_provider.py`) escolhe primeiro qualquer jogo com `status == "live"` do cache. Se a ESPN
  falhou na hora do fim, um jogo de ontem fica "ao vivo" para sempre, porque o `refresh` só reconsulta jogos de hoje
  ou dentro da janela ao vivo.
- O frontend (`useFanMatch.js`, `FanScoreWidget.jsx`) mantém o último dado recebido; confira se ele troca quando o
  backend passa para o próximo jogo.

Regras novas:
- Jogo com `live` cujo horário passou de `LIVE_WINDOW_AFTER` (3 h) vira "encerrado" na leitura e é reconsultado
  uma vez; não pode mais ser escolhido como "ao vivo".
- Depois do fim, o placar final fica na tela até o fim daquele dia. No dia seguinte, a tela mostra o **próximo
  jogo** com contagem regressiva.
- Desligar sozinho no dia seguinte quando o modo foi ligado **num dia de jogo**, seja automático ou manual.
  Se eu ligar na mão num dia sem jogo, ele fica ligado até eu desligar. (Se achar melhor uma chave
  "Manter o Modo Torcedor sempre ligado" em Configurações, proponha antes.)
- Ao desligar sozinho, avisar uma vez: "Modo Torcedor desligado. Próximo jogo: <adversário>, <dia> às <hora>."

**Testes** (em `backend/tests/test_fan_matchday_44.py` ou num arquivo novo, sem gravar em `data/` real): jogo "live"
de ontem no cache; modo ligado pelo botão no dia do jogo e desligado no dia seguinte; modo ligado na mão em dia sem
jogo continua ligado; o `/api/fan/match` do dia seguinte devolve o próximo jogo.

**Pronto quando:** no dia seguinte ao jogo, sem eu fazer nada, a central sai do Modo Torcedor e, se eu abrir o
placar, ele mostra o próximo jogo, não o antigo.

### 6. Aviso de versão nova (PC e celular)
- **PC:** em Configurações > Manutenção, botão "Verificar atualizações" que consulta
  `https://api.github.com/repos/PatrickCaramico/IA_Jarvis/releases/latest` (público, sem token), compara com
  `VERSION` e mostra "Você está na versão mais nova" ou "Versão X disponível" com as notas e o link da release.
  Uma checagem automática por dia, em segundo plano, nunca na abertura. Não baixa nem instala nada sozinho.
  Sem internet: mensagem amigável, sem erro na tela.
- **Celular:** ao abrir, o app compara a própria versão com `/api/mobile/info` do PC. Se o PC tiver uma versão
  mais nova do APK, mostra "Atualização do JARVIS disponível" com botão que baixa de `/api/mobile/app.apk`.

**Pronto quando:** com uma release mais nova no GitHub, o PC avisa; com um APK mais novo no PC, o celular avisa.

---

## Bloco C — Lançamento no GitHub

### 7. Testes automáticos no GitHub (Actions)
Criar `.github/workflows/ci.yml`, rodando em `windows-latest` a cada push e pull request:
- backend: Python 3.11, `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`, `ruff check`,
  `pytest -q backend/tests scripts/tests`;
- frontend: Node 20, `npm ci`, `npm run lint`, `npm test`, `npm run build`.
Nenhum teste pode depender de câmera, microfone, internet, `.env` ou chave de IA (marque e pule os que dependem,
dizendo quais). Se alguma dependência pesada (ex.: OpenCV, pygame) impedir a instalação no CI, diga antes de mudar algo.

**Pronto quando:** o workflow fica verde no GitHub e o selo de status aparece no README.

### 8. APK nas Releases do GitHub
Criar `.github/workflows/release-apk.yml`, disparado por tag `v*` (ex.: `v5.0.0`):
- instala JDK 17 e Android SDK 34 (build-tools 34.0.0) e roda a mesma sequência do `build_apk.ps1`
  (aapt2 → javac → d8 → zipalign → apksigner). Se for preciso, adapte o script para aceitar os caminhos das
  ferramentas por parâmetro, sem quebrar o uso local pelo `Gerar-App-Android.bat`;
- assina com a **mesma chave** que já uso (`%USERPROFILE%\.jarvis-android\jarvis-release.jks`), vinda dos
  *secrets* do repositório (`ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`). Sem a mesma chave, o celular
  não aceita a atualização por cima. A chave nunca é impressa no log nem salva no repositório;
- anexa `JARVIS-<versão>.apk` à release, com as notas daquela versão tiradas do `CHANGELOG.md`.
- Escreva em `docs/RELEASE.md` o passo a passo para eu cadastrar os dois *secrets* e publicar uma versão.

**Pronto quando:** ao criar a tag `v5.0.0`, a release aparece no GitHub com o APK assinado, e esse APK instala por
cima do app 4.5.1 no meu celular.

### 9. README de lançamento e documentação da V5
- `README.md` para quem chega pelo GitHub: o que é, prints (use `docs/historico/` e `docs/linkedin/img/`),
  requisitos, "como instalar a partir do clone" (`git clone`, copiar `.env.example` para `.env`,
  `Iniciar-JARVIS.bat`), app Android (baixar da página de Releases ou pelo QR do PC), selo do CI, links para `docs/`.
- `CHANGELOG.md`: seção **5.0.0** com os itens feitos.
- `docs/ATUALIZACAO-V5.md` no formato das anteriores.
- `docs/COMANDOS.md`, `docs/API.md` (pelo `scripts/dev/gerar_api_md.py`, se ele ainda funcionar) e
  `docs/CONFIGURACAO.md` atualizados com as rotas e comandos novos.
- Pergunte se quero uma licença (MIT ou "todos os direitos reservados") antes de criar o `LICENSE`.

**Pronto quando:** alguém que nunca viu o projeto consegue instalar só lendo o README.

### 10. Revisão de segurança antes de publicar (somente análise)
**Não altere nada.** Com o código já no GitHub, revise e me liste:
- qualquer segredo, token, PIN, foto ou dado pessoal que esteja (ou já tenha estado) nos arquivos versionados;
- rotas que funcionam sem token ou com a central bloqueada e que não deveriam;
- o que acontece se alguém na mesma rede Wi-Fi tentar usar a API sem o token do celular;
- riscos das funções novas (abrir sites, importar favoritos, baixar escudos, checar atualização).
Para cada ponto: gravidade (alta, média, baixa) e a correção sugerida. Aguarde minha aprovação.

**Pronto quando:** recebo a lista, sem nenhum arquivo alterado.

---

## Como começar

Antes de tudo (fora do Copilot): instalar o Git no Windows (https://git-scm.com/download/win), porque hoje o
comando `git` não existe no PC, e ligar a pasta ao repositório `PatrickCaramico/IA_Jarvis`.

Primeira mensagem para o Copilot (não altera nada):
> Leia `docs/COPILOT-V5.md` e o código do projeto. Resuma em 5 linhas o que entendeu e diga se algo no arquivo não bate com o código.

Depois, um item por vez (troque o número):
> Faça apenas o item 1 de `docs/COPILOT-V5.md`. Antes de editar, liste os arquivos e as mudanças. Depois diga como testar e espere minha confirmação.

Ordem sugerida: 0 → 1 → 2 (antes do primeiro push) · 3, 4, 5 (as melhorias que eu pedi) · 6 · 7 → 8 → 9 · 10 por último.
Os itens 3, 4 e 5 são independentes entre si.
