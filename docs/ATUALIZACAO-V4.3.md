# Atualização V4.3: briefing "bom dia" em etapas

4 de novembro de 2026. Baseada na análise do vídeo de referência (briefing "bom dia", 78 s).

## O que muda para você

Diga **"bom dia"** (ou clique em ▶ REPRODUZIR BRIEFING COMPLETO na tela Briefing, menu Telas).
O JARVIS faz um briefing único, em etapas:

| Etapa | Na tela | Na fala |
| --- | --- | --- |
| Abertura | Caixa central: "Sem desvios relevantes / dados consolidados desde ontem" ou "Atenção a N pontos" | "Revisei o que já está consolidado e nada exige interromper a sua manhã." |
| Clima | Card "PANORAMA · CLIMA": cidade, temperatura, condição, mínima, máxima, sensação, chuva e vento | Temperatura, condição, mínima e máxima; a chuva só quando passa de 50% |
| Agenda | Card "AGENDA · HOJE": compromissos do Google Agenda e lembretes de hoje, ou "Agenda livre" | Quantos compromissos e o primeiro |
| E-mail | Card "COMUNICAÇÕES · E-MAIL": "Pedem sua atenção", chips "N recebidos" e "N para agir", itens numerados por remetente | Quantos chegaram e quantos pedem ação |
| Notícias | Um card por tema (Tecnologia, Novos modelos de IA, Política): manchete, fonte, selo de tempo e "Abrir matéria ↗" | A manchete e "A informação é do (fonte)" |
| Saúde | Card "Observações disponíveis", chip "sob demanda", "N leituras sensíveis preservadas" | Só "seus dados de saúde estão disponíveis sob demanda" |
| Fechamento | Fileira com todos os cards + painel "Prontidão fisiológica" no canto esquerdo | Uma recomendação do dia (ex.: "Hoje, mantenha o foco no essencial") |

Durante a fala, o topo mostra **FALANDO** e uma fileira de abas (Clima, Agenda, E-mails, Notícias,
Prioridades). Cada aba tem a própria barra: cheia nas já faladas e enchendo na atual enquanto o
JARVIS fala. A caixa central mostra o texto da etapa ("Verificando e-mails importantes...").
Ao terminar, o topo volta para **EM ESPERA** e os cards ficam na fileira até você clicar em ✕.

### Interação e posicionamento (como no vídeo)

- **Tela limpa:** durante o briefing e as telas por assunto, as colunas laterais (telemetria,
  serviços, tarefas, clima e Canal Ativo) somem e o centro ocupa a tela toda. Elas voltam quando
  você fecha a fileira (✕). O Canal Ativo continua recebendo as falas por trás.
- **Orbe centralizado:** o botão "Olho de Deus" dividia a linha com o orbe e o empurrava para a
  esquerda; agora fica por cima, embaixo do orbe, e some durante o briefing.
- **Posição dos cards:** o card falado agora fica largo (até 560 px) no centro do orbe, e os já
  falados formam uma fileira centralizada logo abaixo dele, crescendo a cada assunto.
- **Cards baixos na fileira:** na fileira (durante e no fim) cada card tem altura fixa (150 a
  172 px, conforme a tela); manchetes longas viram 2 linhas com "...". Clique para ver inteiro.
- **Clima como no vídeo:** temperatura, mínima, máxima e sensação num bloco, chuva e vento numa
  coluna à direita.
- **Identificação no orbe:** enquanto o JARVIS cumprimenta, sua foto de perfil aparece dentro do
  orbe com um anel ciano girando.
- **Canal Ativo ao vivo:** cada parte falada entra como uma mensagem "JARVIS ▸", digitando, no
  momento em que é falada. No fim entram a recomendação e o resumo compacto dos cards.
- **Legenda:** o que o JARVIS está dizendo aparece embaixo do card atual.
- **PRÓXIMO ▸** (ou a seta **→**): corta só a fala atual e passa para o próximo assunto.
  O contador mostra em que parte está ("3 / 7").
- **Fileira em espera:** a fileira fica centralizada sobre o orbe e a prontidão fisiológica no
  canto superior esquerdo. Clique num card para **ampliar**
  (Esc fecha). O ✕ que aparece ao passar o mouse **esconde** o card.
- **Gerenciar HUD:** mostra "GERENCIAR HUD · N ESCONDIDOS". Clicando, todos os cards aparecem
  marcados como VISÍVEL ou ESCONDIDO; clique em cada um para trocar e em ✓ CONCLUIR para sair.
  A escolha fica salva neste navegador e vale para os próximos briefings.

- **Cancelar** (Esc ou ✕ CANCELAR) corta a fala; os cards já falados continuam na fileira.
- **Modo silencioso:** os cards passam sozinhos, cerca de 2,5 s cada, sem voz.
- Frases longas que começam com "bom dia" (mais de 6 palavras, como "bom dia, abre o Spotify e
  toca minha playlist") seguem o caminho normal, sem briefing.

### Regras do briefing

- **Por exceção:** a abertura só fala de problemas que justificam interromper a manhã. Hoje contam
  lembretes atrasados e alerta de trovoadas.
- **Triagem, não listagem:** o e-mail mostra o total, quantos pedem ação e o assunto de cada um, sem
  ler a caixa inteira.
- **Fonte citada:** cada notícia diz de onde veio.
- **Privacidade:** nenhum valor de saúde é falado. A prontidão (recuperação, passos, sono, água)
  aparece só na tela, com a central já liberada pelo rosto ou PIN.
- **Recomendação final**, nesta ordem: 3 ou mais e-mails para agir; chuva a partir de 60%;
  4 ou mais compromissos; 5 ou mais tarefas pendentes; senão "mantenha o foco no essencial".
- Uma fonte que falhar (sem internet, agenda desconectada) só sai do briefing; o resto continua.

## Fechamento do dia ("boa noite")

Diga **"boa noite"**, "fechar o dia" ou "boa noite, resumo do dia". O palco é o mesmo, com o título
**FECHAMENTO DO DIA** e as abas Tarefas, Amanhã, Clima, Água e Anotações.

| Etapa | Card | Na fala |
| --- | --- | --- |
| Abertura | "Dia encerrado sem pendências" ou "Fechamento do dia · N pendentes · N para amanhã" | Só quando o dia está limpo |
| Tarefas | "TAREFAS · PENDENTES": as 4 primeiras, ou "Tudo concluído" | Quantas ficaram e as duas primeiras |
| Amanhã | "AGENDA · AMANHÃ": Google Agenda e lembretes de amanhã | Quantos compromissos e o primeiro |
| Clima | "PANORAMA · CLIMA AMANHÃ": mínima, máxima e chuva de amanhã | Condição e faixa de temperatura; chuva a partir de 50% |
| Água | "HIDRATAÇÃO · HOJE": litros, meta e barra | Quanto bebeu ou "meta batida" |
| Anotações | "ANOTAÇÕES · HOJE" (só aparece se houver) | Quantas e a última |

A dica final, nesta ordem: compromisso amanhã antes das 9h ("vale dormir um pouco antes");
chuva a partir de 60% ("deixe o guarda-chuva separado"); 3 ou mais tarefas pendentes ("escolha
agora a primeira tarefa de amanhã"); senão "desligue as telas um pouco antes de dormir".

**Qual resumo cada frase abre:** frases com "boa noite", "fechar o dia", "resumo da noite" ou
"balanço do dia" sempre abrem o fechamento, mesmo com "dia" no meio. "Resumo" ou "briefing"
sozinhos dependem da hora (a partir das 18h, o fechamento). Um cumprimento seguido de outro pedido
("boa noite, abre o Spotify e toca jazz") não abre resumo nenhum.

## Telas por assunto e a faixa DIGA:

Além do "bom dia" e do "boa noite", uma palavra curta abre só um assunto no mesmo palco:
"notícias", "notificações", "e-mails", "agenda", "clima", "tarefas", "meus dados de saúde" e
"comandos". A lista completa de frases está em [COMANDOS.md](COMANDOS.md#telas-por-assunto-v43).

- Cada item vira um card e ganha sua aba (notícias: uma aba por tema; notificações: uma por
  aplicativo; clima: Hoje e Amanhã).
- Embaixo do orbe, quando o JARVIS está livre, a faixa **DIGA:** mostra as frases. Clicar numa
  delas envia o comando. A mesma faixa aparece, menor, embaixo da fileira final.
- **Privacidade:** nas notificações, a fala diz só quantas há e de qual aplicativo; o texto aparece
  só na tela, a não ser que "ler o conteúdo" esteja ligado. Em "meus dados de saúde", como você pediu,
  os números aparecem e a recuperação e o sono são falados.
- O código fica em `backend/modules/briefing_topics.py` (frases em `PHRASES`, um `build` por
  assunto). A faixa DIGA: fica em `VoiceHints`, em `frontend/src/components/BriefingStage.jsx`.

## Como ligar cada fonte

| Fonte | O que precisa | Sem ela |
| --- | --- | --- |
| Clima | `WEATHER_CITY` no `.env` (já existia) | Card de clima não aparece |
| Agenda | Google Agenda conectado em Configurações (opcional); lembretes do JARVIS sempre entram | Só lembretes |
| E-mail | `EMAIL_IMAP_HOST`, `EMAIL_IMAP_USER`, `EMAIL_IMAP_PASSWORD` (senha de app). Veja [CONFIGURACAO.md](CONFIGURACAO.md) | Card "E-mail não conectado", sem fala |
| Notícias | Internet (Google News RSS) | Tema sem notícia sai do briefing |
| Saúde e prontidão | `data/health_telemetry.json` (relógio por BLE ou sincronização Android, já existia) | Sem painel de prontidão |

Para trocar os temas das notícias, edite `NEWS_THEMES` em `backend/modules/briefing.py`
(`topic` = seção do Google News; `query` = busca por tema livre).

## Para quem mexe no código

| Arquivo | O que faz |
| --- | --- |
| `backend/modules/briefing.py` | `build_morning_briefing()` e `build_evening_briefing()`: buscam as fontes em paralelo e devolvem os segmentos (aba, texto de progresso, fala, card), abertura, prontidão e fechamento. `request_mode()` decide manhã ou noite. `generate_daily_briefing()` e `generate_evening_briefing()` continuam devolvendo o texto corrido (rota `/api/briefing`). |
| `backend/modules/email_triage.py` | Triagem IMAP somente leitura (`BODY.PEEK`, caixa aberta com `readonly=True`). A classificação por palavras fica em `classify()`. |
| `backend/modules/news_radar.py` | Novo `fetch_news_by_query()` (busca do Google News, últimos 2 dias) e o campo `source_url`. |
| `backend/core/briefing_flow.py` | Fala parte a parte e envia `briefing_start`, `briefing_step` e `briefing_end` pelo WebSocket; no fim manda um `response` com o card `briefing` para o Canal Ativo. |
| `backend/core/turns.py` | "bom dia" e "boa noite" (até 6 palavras) e a rotina `/api/trigger-jarvis` vão para o briefing em etapas antes das respostas rápidas. |
| `backend/core/speech.py` | `speak(..., idle_after=False)` não volta a tela para "em espera" entre uma parte e outra. |
| `backend/routes/productivity.py` | `POST /api/briefing/skip`: pula para o próximo assunto (`briefing_flow.skip()`). |
| `frontend/src/components/BriefingStage.jsx` | Palco no centro da central: abertura, abas com barra, card atual, pilha, legenda e PRÓXIMO; no fim, a fileira com ampliar, esconder e Gerenciar HUD. |
| `frontend/briefing-demo.html` + `src/dev/briefingDemo.jsx` | Demonstração sem backend e sem desbloqueio: com `npm run dev`, abra `http://127.0.0.1:5173/briefing-demo.html` e clique em ▶ Simular "bom dia". Não entra no build. |
| `frontend/src/components/BriefingCard.jsx` | Os cards (clima, agenda, e-mail, notícia, saúde) e o painel de prontidão. |
| `frontend/src/briefing.css` | Estilo dos cards (vidro translúcido, borda ciano, rótulo mono). Respeita "reduzir movimento". |

A resposta HTTP do "bom dia" volta na hora (`source: "briefing"`, `response` vazio); o conteúdo
chega pelo WebSocket. O JARVIS fica ocupado até o briefing terminar.

Testes: `backend/tests/test_briefing_43.py` (ordem dos cards, saúde nunca falada, desvios, fonte
que falha, triagem de e-mail, sequência de eventos, fechamento da noite e qual frase abre qual resumo).

## O que ficou de fora

- **Imagem da matéria:** o RSS do Google News não traz imagem nem permite capturar o site. O card
  mostra o ícone do site da fonte (serviço de ícones do Google) sobre um fundo gradiente.
- **Reordenar cards** (arrastar na fileira) não foi feito; dá para esconder e reexibir.
- **Pular por voz** ("próximo") não existe: o microfone fica fechado enquanto o JARVIS fala. Use o
  botão ou a seta →.
- A triagem de e-mail usa palavras-chave no assunto; não há resumo por IA nem prazo extraído.
- A tela foi conferida na página de demonstração; com a central real liberada pelo rosto, ainda não.
