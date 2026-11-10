# Configuração (`.env`)

O arquivo `.env` fica na raiz do projeto e guarda chaves e ajustes. Ele **não deve ser
compartilhado** nem enviado ao Git. Para começar, copie o `.env.example` para `.env` e preencha só
o que for usar. Depois de mudar o `.env`, feche e ligue o JARVIS de novo.

Os valores da coluna "Padrão" são os que o JARVIS usa quando a variável não está no `.env`
(definidos em `backend/config/settings.py`). Em alguns casos o `.env.example` sugere outro valor;
isso aparece na coluna "Observação".

## Inteligência artificial

| Variável | Padrão | Para que serve | Observação |
| --- | --- | --- | --- |
| `LLM_PROVIDER` | `openai` | Provedor de IA: `gemini`, `openai` ou `anthropic`. | O `.env.example` sugere `gemini`. Também dá para trocar em Configurações. |
| `GEMINI_API_KEY` | vazio | Chave do Google Gemini. | Só a do provedor escolhido é obrigatória. |
| `OPENAI_API_KEY` | vazio | Chave da OpenAI. | |
| `ANTHROPIC_API_KEY` | vazio | Chave da Anthropic (Claude). | |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Modelo do Gemini. | O `.env.example` sugere `gemini-2.5-flash`. Se o modelo falhar, o JARVIS tenta versões "lite". |
| `OPENAI_MODEL` | `gpt-4o` | Modelo da OpenAI. | |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Modelo da Anthropic. | |
| `GEMINI_SEARCH_GROUNDING` | `true` | Deixa o Gemini pesquisar no Google em perguntas atuais. | O `.env.example` sugere `false` para economizar cota. |
| `GEMINI_REASONING` | `none` | `none` = resposta mais rápida, sem raciocínio estendido. | |
| `LLM_MAX_TOKENS` | `1000` | Tamanho máximo da resposta. | O `.env.example` sugere `400` (respostas mais curtas e rápidas). |

## Voz

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `TTS_VOICE` | `pt-BR-AntonioNeural` | Voz do JARVIS (`pt-BR-FranciscaNeural` = feminina). |
| `TTS_RATE` | `+0%` | Velocidade da fala (`+10%` mais rápida, `-10%` mais lenta). |
| `FILLER_FIRST_DELAY` | `4` | Segundos até o primeiro aviso "só um minutinho" (0 desliga). O `.env.example` sugere `6`. |
| `FILLER_INTERVAL` | `20` | Segundos entre os avisos seguintes. |

## Câmera e reconhecimento facial

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `CAMERA_INDEX` | `0` | Qual webcam usar (0 = padrão, 1 = segunda...). |
| `FACE_THRESHOLD` | `0.363` | Similaridade mínima para reconhecer o rosto (0 a 1). Mais alto = mais rígido. |
| `FACE_TIMEOUT` | `8` | Segundos tentando reconhecer antes de desistir. |
| `FACE_STREAM_FPS` | `10` | Quadros por segundo da câmera ao vivo no orbe (era 12 até a 4.1). |
| `FACE_STREAM_WIDTH` | `400` | Largura em pixels da câmera ao vivo (era 480). |
| `FACE_STREAM_QUALITY` | `65` | Qualidade JPEG da câmera ao vivo, 1 a 100 (era 70). |

## Informações

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `WEATHER_CITY` | `São Paulo` | Cidade do clima quando você não diz outra. |
| `NEWS_LIMIT` | `3` | Quantas notícias entram no resumo simples (reserva). O briefing da 4.3 usa um card por tema; os temas ficam em `NEWS_THEMES`, em `backend/modules/briefing.py`. |
| `USER_NAME` | vazio | Nome usado quando não há perfil com foto. |

## Rede e segurança

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `JARVIS_NETWORK_MODE` | `false` | Aceita conexões de outros aparelhos da rede (com token). O `Iniciar-JARVIS-Rede.bat` liga isso sozinho. |
| `EXTRA_CORS_ORIGINS` | vazio | Endereços extras da interface, separados por vírgula (avançado). |

O token de acesso pela rede é gerado na primeira execução e guardado em `data/`. Ele aparece no QR
Code do painel; não é uma variável do `.env`.

## Integrações

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | vazio | Cliente OAuth do Google Cloud ("Aplicativo para computador") para o Google Agenda. |
| `GOOGLE_REDIRECT_URI` | `http://127.0.0.1:8000/api/integrations/google-calendar/callback` | Endereço de retorno cadastrado no Google. |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | vazio | App do Spotify Developer Dashboard. |
| `SPOTIFY_REDIRECT_URI` | `http://127.0.0.1:8000/api/integrations/spotify/callback` | Endereço de retorno cadastrado no Spotify. |

### Triagem de e-mail no briefing (V4.3, opcional)

Sem estas variáveis o card de e-mail aparece como "E-mail não conectado" e o JARVIS não fala dele.
O JARVIS só lê remetente, assunto e data (nunca o corpo) e abre a caixa em modo somente leitura,
então nada é marcado como lido.

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `EMAIL_IMAP_HOST` | vazio | Servidor IMAP. Gmail: `imap.gmail.com`; Outlook/Hotmail: `outlook.office365.com`. |
| `EMAIL_IMAP_USER` | vazio | Seu endereço de e-mail. |
| `EMAIL_IMAP_PASSWORD` | vazio | **Senha de app**, não a senha normal. No Gmail: Conta Google > Segurança > Verificação em duas etapas > Senhas de app. |
| `EMAIL_LOOKBACK_HOURS` | `24` | Quantas horas para trás entram na triagem. |

## Ajustes que não ficam no `.env`

Nome da IA, tema, widgets, personalidade, palmas, bloqueio (PIN, cartões, ausência, visitante,
Modo Sentinela) e hidratação ficam em **Configurações** no painel e são salvos em
`data/jarvis_settings.json`.

### Meus Sites (V5)

Em **Configurações > Meus Sites**, cadastre o nome, a URL e os apelidos usados para abrir sites por voz. A URL aceita `http://` ou `https://`; a opção **Abrir como aplicativo** tenta usar uma janela do Chrome. Programas locais continuam na lista de atalhos, não nesta tela.

### Atualizações (V5)

Em **Configurações > Manutenção**, o botão **Verificar atualizações** compara a versão do JARVIS com a release pública do GitHub e mostra as notas e o link. Uma verificação automática ocorre uma vez por dia em segundo plano. O PC não instala nada automaticamente.

O app Android compara sua versão com o PC ao abrir uma conexão salva. Se houver um APK mais novo, oferece o download para você confirmar. A automação que publica APKs assinados está descrita em [RELEASE.md](RELEASE.md).
