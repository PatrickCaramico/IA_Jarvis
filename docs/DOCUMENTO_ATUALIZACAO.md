# Documento de atualização do JARVIS

> **Status:** rascunho de ideias, ainda **não** implementado.
> Combinado: primeiro a gente desenha cada ideia aqui, com calma. Só depois que estiver fechada ela entra no JARVIS.
> Versão atual do projeto quando este documento foi criado: **7.5.0** (14/11/2026).

---

## Ideias do Patrick

### Ideia 1: Upload de fotos (galeria)

**O que foi pedido**
- Um botão para **subir uma foto da galeria** (não só tirar na hora pela câmera).
- Uso principal: mandar uma foto para o JARVIS **pesquisar ou analisar** algo.
- Definir **quanto tempo a foto fica guardada**, para não virar alvo de ataque.

**Pontos a decidir**
- [ ] Onde fica o botão: dentro da janela da câmera, no chat (clipe 📎) ou nos dois?
- [ ] A foto é só para a pergunta e some na hora, ou queremos um histórico?
- [ ] Se tiver histórico: por quanto tempo (10 min? 24 h?) e quem pode ver?
- [ ] Vale também fora de casa (pela nuvem)?

**Proposta inicial (para discutir)**
- Mesmo caminho do "O QUE É ISSO?" da câmera, que já existe: a foto vai para a IA e **não é gravada em disco**.
- Se quisermos histórico:
  - guardar só no PC, apagar sozinho depois do prazo combinado;
  - nunca dar um link público para a foto.
- Antes de enviar:
  - tirar a **localização (GPS)** e outros dados escondidos da foto;
  - limitar o tamanho;
  - conferir que é mesmo uma imagem (o PC já faz essa conferência hoje).

#### ✅ Desenho fechado (15/11/2026)

**Decisões do Patrick**
| Tema | Decisão |
|---|---|
| Onde enviar | **Os três:** botão 🖼 GALERIA na janela da câmera, clipe 📎 no campo de conversa e arrastar a imagem na central do PC |
| O que fazer com a foto | **Tudo:** analisar/diagnóstico, ler texto e agir, pesquisar na internet e explicar no Holograma |
| Guardar a foto | **Não guardar:** vai para a IA, a resposta volta e a foto some na hora (nada no PC nem na nuvem) |
| Fora de casa | **Sim, pela nuvem, sem guardar nada** (como a câmera já faz) |

**Como vai funcionar**
1. **Escolher a foto:**
   - 🖼 GALERIA na câmera, 📎 no campo de conversa (celular e PC) ou arrastar para a central no PC (aparece "SOLTE A IMAGEM AQUI").
2. **Antes de sair do aparelho:**
   - a foto é **reduzida** (no máximo 1600 px) e **regravada**;
   - isso apaga a **localização (GPS)** e os outros dados escondidos da foto;
   - fica pequena e rápida de enviar.
3. **Janela "FOTO ENVIADA":**
   - miniatura e um campo de pergunta opcional;
   - 4 botões: 🔍 **ANALISAR** · 📄 **LER E AGIR** · 🌐 **PESQUISAR** · ✦ **HOLOGRAMA**;
   - escrevendo uma pergunta, o JARVIS escolhe sozinho ("quanto custa isso?" vira pesquisa).
4. **Cada função:**
   - 🔍 **Analisar:** a janela de diagnóstico que a câmera já tem (o que é, detalhes, dicas, alertas).
   - 📄 **Ler e agir:** o JARVIS lê o texto e **propõe** uma ação, que **só acontece depois do seu toque em CONFIRMAR**. Exemplos:
     - receita → "Adicionar 8 ingredientes à lista de compras";
     - conta → "Lembrete: pagar a conta de luz de R$ 154,30 no dia 20/11";
     - cartão de visita → "Salvar contato";
     - lista escrita à mão → "Adicionar como tarefas".
   - 🌐 **Pesquisar:** identifica o item e pesquisa (preço médio, onde comprar, avaliações), com as fontes.
   - ✦ **Holograma:** identifica o assunto e abre a apresentação animada, com **a sua foto** no fundo.

**Segurança (com as regras da ideia 2)**
- A foto **nunca é gravada**: nem no PC, nem na nuvem, nem nos logs. Fica só na memória enquanto a IA responde.
- Só com a central **desbloqueada** e pela chave do aparelho. Com https ligado, vai **criptografada**.
- Confere que é mesmo uma imagem, com limite de tamanho, e no máximo **10 fotos por minuto** por aparelho.
- Ações tiradas da foto (lista, lembrete, contato) **sempre pedem confirmação**: um texto escondido numa imagem não consegue mandar o JARVIS fazer nada sozinho.

**Status:** ✅ **Implementada na versão 7.8.0.**

---

### Ideia 2: Proteção contra ataques (segurança)

**O que foi pedido**
- O JARVIS roda no PC, na rede de casa. Proteger para ele **não sofrer ataque hacker**.

**O que já existe hoje (para não refazer)**
- Bloqueio com rosto, PIN e digital.
- O PIN trava após 5 erros e o tempo de trava dobra a cada novo erro.
- A maioria das rotas do PC exige a central desbloqueada.
- O modo nuvem usa uma chave secreta (`JARVIS_NUVEM_CHAVE`) e acesso por PIN com prazo.
- Não existe túnel público abrindo o PC para a internet.

**Pontos a decidir / melhorias possíveis**
- [ ] **Revisar as rotas liberadas na tela de bloqueio.** As últimas versões liberaram `⚡ OTIMIZAR` e `🩺 DIAGNÓSTICO` sem desbloquear. Hoje elas não mostram nada pessoal, mas devem ter limite de uso.
- [ ] **Limite de tentativas** em todas as rotas: se alguém da rede ficar martelando o PC, ele bloqueia esse aparelho por um tempo.
- [ ] **Lista de aparelhos confiáveis:** celular, PC e TV aprovados uma vez; aparelho novo na rede precisa de aprovação.
- [ ] **Firewall do Windows:** porta do JARVIS aberta só para a rede de casa, nunca para a internet.
- [ ] **Registro de tentativas suspeitas**, com aviso no celular ("um aparelho desconhecido tentou entrar").
- [ ] **HTTPS na rede de casa** (conexão criptografada entre o celular e o PC).
- [ ] **Troca periódica das chaves e tokens** (e um botão "desconectar todos os aparelhos").
- [ ] **Conferir bibliotecas com falhas conhecidas** de tempos em tempos.
- [ ] Um item de **segurança no 🩺 DIAGNÓSTICO** (ex.: "porta exposta?", "PIN fraco?", "chave da nuvem padrão?").

#### ✅ Desenho fechado (15/11/2026)

**Raio-x de hoje**
- ✔ Fora do próprio PC, todo acesso já exige a chave de acesso (a do QR code). O Otimizar e o Diagnóstico também.
- ✘ A chave é **uma só para todos os aparelhos e vale para sempre**: não dá para expulsar um aparelho.
- ✘ A chave também é aceita no **endereço da página** (`?token=`), que fica no histórico e em logs.
- ✘ A conexão na rede de casa é **http, sem criptografia**: alguém no mesmo Wi-Fi pode ver a chave passando.
- ✘ **Ninguém é avisado** de tentativas erradas.

**Decisões do Patrick**
| Tema | Decisão |
|---|---|
| Chave de acesso | **Uma chave por aparelho**, com a tela "Aparelhos conectados" e o botão REMOVER |
| Aparelho novo | **Precisa ser aprovado na tela do PC** (PERMITIR / RECUSAR), mesmo depois de escanear o QR |
| Tentativas suspeitas | **Todos os avisos:** notificação no celular, aviso por voz no PC, bloqueio temporário do aparelho e registro no 🩺 Diagnóstico |
| Criptografia | **Sim, https na rede de casa**, com passo a passo para o celular aceitar o certificado |

**Como vai funcionar**
1. **Aparelhos conectados** (Configurações > Segurança):
   - lista com nome, tipo (celular/tablet/TV/PC), último acesso e de onde;
   - botões REMOVER (um aparelho) e DESCONECTAR TODOS.
2. **Chegada de um aparelho novo:**
   - escaneia o QR e fica em "aguardando aprovação";
   - o PC mostra um cartão e fala: "Um aparelho novo quer se conectar: Galaxy S23. Permitir?";
   - aprovado, o aparelho recebe a **própria chave** e vai para a lista;
   - recusado (ou 2 minutos sem resposta), não entra.
3. **Chaves:**
   - só no cabeçalho da requisição; nada de `?token=` no endereço;
   - a chave antiga (única) continua valendo **uma última vez**, para migrar os aparelhos atuais sem precisar escanear tudo de novo.
4. **Tentativas suspeitas** (chave errada, PIN errado, aparelho removido tentando voltar):
   - **5 erros em 10 minutos** bloqueiam aquele aparelho por 15 minutos, e o tempo dobra a cada nova vez;
   - aviso por voz no PC, notificação no app do celular e registro no 🩺 Diagnóstico (últimas 24 h).
5. **https na rede de casa:**
   - o JARVIS cria um certificado próprio na primeira vez;
   - o QR code passa a apontar para `https://`;
   - passo a passo na tela para o celular confiar no certificado (uma vez só).
6. **Rotas da tela de bloqueio** (⚡ Otimizar, 🩺 Diagnóstico): no máximo 1 vez por minuto por aparelho.
7. **Diagnóstico ganha o item "Segurança":** PIN fraco (ex.: 1234), https ligado, aparelhos sem uso há mais de 30 dias, tentativas suspeitas.

**Cuidados para não quebrar nada**
- O app Android e o modo nuvem precisam continuar funcionando: a migração da chave antiga é automática.
- O app precisa ser gerado de novo (APK) para aceitar o https.

**Status:** ✅ **Parte 1 implementada na versão 7.6.0** (chave por aparelho, aprovação no PC, aviso e bloqueio de tentativas, Configurações > Segurança, item no Diagnóstico).
✅ **Parte 2 implementada na versão 7.7.0:** https na rede de casa (certificado próprio, QR com https, página do certificado, app Android). Fica desligado até ser ligado em Configurações › Segurança.

---

### Ideia 3: Chat direto com os subagentes ("chatbots")

**O que foi pedido**
- Um chat onde dá para falar **direto com um subagente** usando `@nome`. Exemplos: `@rotas me leva pro trabalho`, `@pesquisa receita de pão`.
- Falar com um não pode interferir no outro.
- Criar **novos subagentes** para deixar o JARVIS ainda melhor.

**O que já existe hoje**
- A Central de Agentes (botão 🤖 AGENTES), com o agente de **rotas** e o de **pesquisa**, e um chat comum entre os dois.

**Pontos a decidir**
- [ ] Cada agente tem a **sua própria conversa e memória** (aba por agente)?
- [ ] O `@nome` funciona também por voz ("Jarvis, fala com o agente de rotas…")?
- [ ] Ao digitar `@`, aparece uma lista para escolher o agente?
- [ ] Quais **novos agentes** criar primeiro? Sugestões:
  - 🛒 **Compras/Mercado:** monta a lista, compara preços, sugere receitas com o que tem em casa.
  - 💰 **Finanças:** gastos do mês, contas a pagar, avisos de vencimento.
  - 🏋️ **Saúde/Treino:** água, sono, treino do dia, lembretes.
  - 📅 **Agenda/Secretário:** marca compromissos, avisa conflitos, resume o dia.
  - 🎬 **Entretenimento:** filmes, séries, jogos do Palmeiras, onde assistir.
  - 🧠 **Estudos:** explica matérias usando o Holograma, faz perguntas tipo prova.

#### ✅ Desenho fechado (15/11/2026)

**Decisões do Patrick**
| Tema | Decisão |
|---|---|
| Onde falar com o agente | **Nos dois:** abas por agente na Central de Agentes **e** `@nome` no campo de conversa normal |
| Memória | **Cada agente lembra a própria conversa** (últimas 30 mensagens, salvas no PC), com botão LIMPAR |
| Agentes novos | **Todos os 4:** 🛒 Mercado, 💰 Finanças, 📅 Secretário e 🧠 Professor |
| Voz | **Sim:** "Jarvis, pergunta pro agente de finanças…", "agente mercado, monta a lista da semana" |

**Como vai funcionar**
1. **Agentes** (6), cada um com nome curto para o `@`:
   | Agente | `@` | O que faz | Usa o que já existe |
   |---|---|---|---|
   | 🧭 Rotas | `@rotas` | rota e lugares salvos | agente de rotas |
   | 🔎 Pesquisa | `@pesquisa` | YouTube e pesquisa na internet | agente de pesquisa |
   | 🛒 Mercado | `@mercado` | lista de compras, receitas com o que tem em casa, quantidades | lista de compras |
   | 💰 Finanças | `@financas` | anota gastos e entradas, resume o mês, compara categorias | módulo de finanças |
   | 📅 Secretário | `@secretario` | agenda, lembretes e tarefas num lugar só ("o que tenho amanhã?", "marca dentista sexta às 10") | Google Agenda (iCal), lembretes, tarefas |
   | 🧠 Professor | `@professor` | explica matérias (com o Holograma) e faz perguntas tipo prova | Holograma |
2. **Falar com um agente:**
   - **Central de Agentes:** uma **aba por agente**, cada uma com a própria conversa.
   - **Campo de conversa:** começar com `@` mostra a lista de agentes. Escolhendo um, a mensagem vai **só para ele** e a resposta aparece com o ícone e o nome dele.
   - **Voz:** "Jarvis, pergunta pro agente de finanças quanto gastei no mês", "agente mercado, monta a lista da semana", "fala com o professor: me explica frações".
3. **Cada agente é especialista:**
   - tem instruções próprias e só enxerga os dados da área dele (o de Finanças não vê a agenda, por exemplo);
   - responde com a voz do JARVIS;
   - quando precisa **mudar algo** (adicionar à lista, criar lembrete, anotar gasto), **mostra o que vai fazer** e faz, com o mesmo cuidado de confirmação da foto para ações maiores (apagar, várias de uma vez).
4. **Memória:**
   - as últimas 30 mensagens de cada agente ficam salvas no PC;
   - um agente não vê a conversa do outro;
   - o botão LIMPAR apaga só a conversa daquele agente.
5. **Fora de casa (nuvem):** funcionam os agentes que já têm dados lá (Mercado, Secretário com lembretes/tarefas, Professor). Finanças e a agenda do Google pedem o PC ligado.

**Status:** ✅ **Implementada na versão 7.9.0.**

---

### Ideia 3.1: Agente de finanças completo (controle de dívidas)

**O que foi pedido:** usar o agente de finanças no dia a dia como controle financeiro, principalmente das dívidas.

#### ✅ Desenho fechado (15/11/2026)

**Decisões do Patrick**
| Tema | Decisão |
|---|---|
| O que controlar | **Tudo:** dívidas e parcelamentos, contas fixas do mês, cartão de crédito, orçamento e metas |
| Plano para quitar | **Comparar e sugerir:** "menor dívida primeiro" × "maior juros primeiro", com tempo e juros de cada um |
| Avisos de vencimento | **3 dias antes e no dia**, por voz no PC e notificação no celular |
| Fora de casa | **Anotar e ver resumo** (os detalhes completos ficam só no PC) |

**O que o agente vai saber fazer**
1. **Dívidas e parcelamentos**
   - cadastrar: credor, o que é, saldo, valor e número de parcelas (ex.: 7 de 12), juros ao mês e dia do vencimento;
   - "paguei a parcela do carro", "paguei R$ 500 a mais no cartão", "quitei o empréstimo";
   - o saldo cai, a parcela conta e fica o histórico de pagamentos.
2. **Contas fixas do mês**
   - aluguel, luz, água, internet, celular… com valor e vencimento;
   - marca "paga" em cada mês e mostra o que ainda falta pagar.
3. **Cartão de crédito**
   - cartões com dia de fechamento e vencimento;
   - compras à vista ou parceladas, que caem nas faturas certas;
   - "quanto está minha fatura?", "quanto já tenho comprometido no mês que vem?".
4. **Orçamento e metas**
   - limite por categoria (ex.: R$ 800 de mercado), com aviso a 80% e a 100%;
   - metas, como uma reserva de emergência, com quanto falta e em quanto tempo chega.
5. **Plano para sair das dívidas**
   - compara os dois jeitos lado a lado, com e sem um valor extra por mês ("se eu pagar R$ 300 a mais?"):
     - **menor dívida primeiro:** dá motivação, porque as dívidas vão sumindo;
     - **maior juros primeiro:** paga menos juros no total;
   - para cada um, mostra em quantos meses quita tudo e quanto paga de juros, e recomenda um.
6. **Avisos**
   - 3 dias antes e no dia do vencimento: "Hoje vence a parcela do carro, R$ 890,00" (voz no PC e notificação no celular);
   - avisos também de fatura e orçamento estourando.
7. **Painel de finanças** (aba 💰 da Central de Agentes)
   - total devido, quanto vence neste mês, contas a pagar, fatura atual;
   - barras do orçamento, progresso das metas e de cada dívida;
   - próximos vencimentos (30 dias) e o plano para quitar.
8. **Segurança**
   - tudo fica só no PC;
   - ações grandes pedem **✓ CONFIRMAR**: quitar, apagar, pagamento acima de R$ 1.000 e mudar dados de uma dívida;
   - fora de casa, o celular só **anota** (gasto ou pagamento, que chegam ao PC na sincronização) e vê o **resumo**.

**Status:** ✅ **Implementada na versão 7.10.0.**

---

### Ideia 4: Olho de Deus mais completo

**O que foi pedido**
- O Olho de Deus ainda está "cru". Deixar ele bem melhor.

**O que já existe hoje**
- Mapa de **trânsito ao vivo** (Waze), com busca, "onde estou" e lugares salvos.
- As outras categorias (voos, satélites, terremotos, clima…) ainda **sem dados reais**.

#### ✅ Desenho fechado (15/11/2026)

**Decisões do Patrick**
| Tema | Decisão |
|---|---|
| Camadas novas | **Todas:** radar de chuva, voos ao vivo, terremotos e queimadas, Estação Espacial (o trânsito do Waze continua) |
| Mapa | **Globo 3D real**, que gira e dá zoom até a rua; o desenho atual sai |
| Avisos sozinho | **Chuva forte chegando**, **perto de mim** (queimada e terremoto) e **Estação Espacial visível**, com um botão para desligar cada um ("só quando eu pedir") |
| Categorias sem dados | **Esconder por enquanto**; leitores de placa saem de vez, por privacidade |

**Como vai ficar**
1. **Globo 3D**
   - globo de verdade (MapLibre, mapas gratuitos e sem chave) que abre girando devagar e voa até a sua cidade;
   - visão escura (estilo HUD) e visão satélite;
   - clicar num ponto (avião, terremoto, foco de fogo) abre um cartão com os detalhes;
   - mais leve no celular: menos pontos e animação reduzida.
2. **Camadas com dados reais e gratuitos** (cada uma liga e desliga, com a hora da última atualização)
   - 🚦 **Trânsito** — o mapa do Waze de hoje, que continua sendo a primeira aba;
   - ☁ **Radar de chuva** — a chuva das últimas 2 horas, animada sobre o globo (RainViewer), e a previsão de chuva para as próximas horas na sua cidade (Open-Meteo);
   - ✈ **Voos ao vivo** — aviões num raio de ~150 km da cidade: voo, altitude, velocidade e rota quando houver (dados públicos de ADS-B), atualizando a cada 15 s;
   - 🌎 **Terremotos** — últimas 24 h no mundo, o tamanho do ponto mostra a força (USGS);
   - 🔥 **Queimadas** — focos no Brasil nas últimas 24 h (INPE), com quantos estão perto da sua cidade;
   - 🛰 **Estação Espacial** — onde a ISS está agora, a trilha da órbita e as próximas passagens visíveis no seu céu.
3. **Resumo "o que está acontecendo"** — uma faixa no topo: "Sem chuva nas próximas 3 h · 42 voos por perto · 3 terremotos fortes hoje · ISS passa visível às 19:42".
4. **Avisos automáticos** (voz no PC e notificação no celular; cada um pode ser desligado)
   - **chuva forte chegando:** "Chuva forte na sua região em uns 30 minutos." (das 7h às 23h, no máximo 1 aviso a cada 3 h);
   - **perto de mim:** queimada a menos de 50 km da cidade, ou terremoto de força 5 ou mais no Brasil e vizinhos;
   - **Estação Espacial visível:** 10 minutos antes de passar, só à noite e com céu limpo.
5. **Voz e conversa**
   - "abre o Olho de Deus", "mostra os voos agora", "tem terremoto hoje?", "vai chover?", "tem queimada perto?", "quando a estação espacial passa?";
   - o JARVIS responde falando e abre o globo já na camada certa.
6. **Fora de casa** — funciona igual no celular, pela nuvem: os dados são públicos e não dependem do PC. Os avisos automáticos saem do PC.
7. **Privacidade e segurança**
   - só fontes públicas e oficiais; nada de câmeras de pessoas nem leitores de placa;
   - a sua localização só é usada para centralizar o mapa e calcular o "perto de mim"; não vai para outros serviços além das buscas de mapa e clima;
   - os dados ficam guardados por poucos minutos (cache), para não pesar e não ser bloqueado pelas fontes.
8. **O que sai** — o globo desenhado e as categorias sem dados (navios, Starlink, câmeras, rádios), que voltam quando houver fonte gratuita boa.

**Status:** ✅ **Implementada na versão 7.11.0.**

---

### Ideia 5: Holograma ainda melhor e pesquisa com animação

**O que foi pedido**
- Deixar o **Holograma** ainda melhor.
- Em **toda pesquisa**, mostrar também **uma animação** sobre o assunto, e não só o texto na tela.

**O que já existe hoje**
- Pedidos como "me explica…", "pesquisa sobre…" e "receita de…" abrem o Holograma: cenas narradas, partículas, esfera 3D, ondas de voz e receita viva.

#### ✅ Desenho fechado (15/11/2026)

**Decisões do Patrick**
| Tema | Decisão |
|---|---|
| Animações por assunto | **Todas:** gráficos e números, linha do tempo, mapa e globo, espaço e ciência |
| Perguntas rápidas | **Cartão animado pequeno** no canto; o Holograma inteiro só abre em "me explica…" |
| Extras | **Todos:** perguntar no meio, quiz no final, salvar e rever, fotos reais nas cenas |
| Som | **Trilha ambiente baixinha**, que abaixa quando o JARVIS fala, com botão para desligar |

**Como vai ficar**
1. **Cada cena com a animação certa** (a IA escolhe o tipo; se os dados não forem bons, a cena fica no modo de hoje)
   - 📊 **gráficos e números:** barras ou linha que crescem na tela (preços, população, recordes, comparações);
   - 🕰 **linha do tempo:** a linha avança e acende cada data e marco (história, biografias, invenções);
   - 🌍 **mapa e globo:** o globo 3D do Olho de Deus voa até o lugar, com marcadores e rota (países, viagens, batalhas);
   - 🪐 **espaço e ciência:** diagramas animados prontos (planetas e órbitas, átomo, ciclo da água, coração batendo, camadas da Terra…).
   - Os números e datas vêm da IA com a regra de não inventar; se ela não tiver certeza, a cena não usa gráfico.
2. **Fotos reais nas cenas:** cada cena pode ter uma foto do assunto (Wikipédia/Wikimedia), com o crédito pequeno embaixo.
3. **Trilha ambiente:** som de fundo suave, estilo documentário, gerado no próprio aparelho (sem música de terceiros). Ele abaixa quando o JARVIS fala, e o botão 🔈 desliga e lembra a escolha.
4. **Perguntar no meio:** "espera, o que é horizonte de eventos?" (voz ou digitando)
   - a apresentação pausa, a resposta aparece num balão e é falada;
   - depois continua da mesma cena.
5. **Quiz no final:** "quer testar o que aprendeu?"
   - 3 perguntas de múltipla escolha sobre o que foi mostrado;
   - responde tocando ou falando a letra, com placar e a explicação de cada uma.
6. **Salvar e rever**
   - ⭐ SALVAR guarda a apresentação (ou receita) numa lista; rever não gasta IA;
   - até 30 salvas, no PC, que vão para a nuvem na sincronização, para rever no celular fora de casa;
   - apagar uma salva pede confirmação.
7. **Cartão animado para perguntas rápidas** ("quem ganhou o jogo?", "quanto está o dólar?", "qual a altura do Everest?")
   - o JARVIS responde falando, como hoje, e mostra um cartão pequeno no canto que some sozinho;
   - tipos de cartão: **número** (com mini-gráfico quando houver série, ex.: dólar na semana), **placar**, **foto + fato** e **lista curta**;
   - botão "▶ VER NO HOLOGRAMA" no cartão, se quiser a apresentação inteira.
8. **Fora de casa:** tudo funciona igual pela nuvem (o mapa usa o mesmo globo).
9. **Celular:** animações mais leves e menos partículas; a trilha começa desligada para não tocar alto em público.

**Status:** ✅ **Implementada:** parte 1 na versão 7.13.0 (animações por cena, fotos e trilha) e parte 2 na versão 7.14.0 (perguntar no meio, quiz, salvar e rever, cartão rápido).

---

### Ideia 6: Modo Desk (o JARVIS como app de assistente pessoal no PC)

**O que foi pedido:** a partir de 2 vídeos de outro assistente para Windows, levar o JARVIS a outro patamar:
- uma interface nova, com um botão para alternar (a versão atual continua);
- os mesmos recursos e configurações;
- um avatar estilizado, mantendo a essência do JARVIS;
- um executável para baixar pelo botão no bloqueio e na central.

**Observação:** o app dos vídeos é um produto de outra pessoa, com nome e mascote próprios. O layout e as funções servem de inspiração; o nosso é o JARVIS, com identidade, nome e avatar próprios.

#### ✅ Desenho fechado (15/11/2026)

**Decisões do Patrick**
| Tema | Decisão |
|---|---|
| Avatar | **Robô JARVIS:** cabeça arredondada, visor escuro e olhos de luz em forma de arco-reator, com expressões e cores personalizáveis |
| Executável | **App + ilha no topo:** JARVIS.exe com janela própria e a "ilha" no topo da tela do Windows |
| Recursos novos | **Todos:** Hábitos, Copiados, Nível e XP, Memória em mapa |
| Cor | **Você escolhe:** começa no ciano do JARVIS; em Personalizar troca para verde-limão, roxo, laranja… |

**Como vai ficar**
1. **Botão 🖥 MODO DESK** na central, no ⚡ CONTROLES e no bloqueio: troca para o layout novo (e volta para o atual com um toque). Fica lembrado por aparelho.
2. **Layout** (fundo escuro, cartões arredondados, cor de destaque escolhida por você)
   - **barra lateral:** o avatar com o nome, o estado ("Pronto", "Ouvindo", "Falando") e o nível, mais as seções:
     - Início, Conversa, Memória, Tarefas, Lembretes, Hábitos, Timers, Música, Copiados, Rotinas e Meu PC;
     - Configurações;
   - **Início:**
     - "Boa noite, Patrick!" com o avatar;
     - campo "Escreva ou fale com o JARVIS" e a conversa recente;
     - o player de música;
     - contadores (lembretes, tarefas, hábitos de hoje) e a barra de XP;
   - **Configurações** com busca, em grupos:
     - **Assistente:** Personalizar, Cérebro (IA), Funções, Voz, Rotinas, Ilha;
     - **Conexões:** Celular e agendas, Proteção com rosto, Atalhos.
3. **Avatar robô JARVIS (Personalizar)**
   - cor do corpo, cor do visor, cor dos olhos;
   - expressões: feliz, pensando, falando, ouvindo, dormindo, surpreso, piscando;
   - acessórios: nenhum, fone, óculos, gorro de Natal e coroa;
   - nome do assistente, cor principal do app e tamanho da ilha;
   - o avatar reage sozinho: ouvindo, pensando e falando.
4. **Cérebro (IA)**
   - cartões para escolher como ele pensa: automático (troca sozinho quando uma IA chega no limite), eu escolho a IA (ChatGPT, Claude, Gemini…), e o estado de cada chave;
   - **Testar esta IA** mostra a resposta e o tempo.
5. **Funções:** catálogo do que dá para falar, com exemplos (YouTube, volume, música, lembretes, timers, clima, cotações, verificar o PC…), e atalhos próprios ("abre o meu programa X").
6. **Meu PC:** a varredura do ⚡ OTIMIZAR com o avatar no centro do anel de progresso ("Olhando a memória, vendo o processador, arquivos temporários, disco…").
7. **Recursos novos**
   - **Hábitos:**
     - hábitos do dia (beber água, ler, treinar) com marcar, sequência de dias e lembrete;
     - "Jarvis, marquei o treino de hoje".
   - **Copiados:**
     - histórico do que você copiou no PC (as últimas 50), para copiar de novo com um clique;
     - fica só no PC, não vai para a nuvem;
     - não guarda o que parece senha, cartão ou código;
     - botões para pausar e para apagar tudo.
   - **Nível e XP:** o JARVIS ganha XP com tarefas feitas, hábitos, conversas e rotinas; sobe de nível, com a barrinha na lateral.
   - **Memória em mapa:** as memórias do JARVIS (pessoas, preferências, coisas importantes) num mapa de bolinhas ligadas por assunto; tocar abre, e dá para adicionar e apagar.
8. **JARVIS.exe (app para Windows)**
   - **Gerar-App-Windows.bat** monta o executável no seu PC, como o app Android;
   - o botão **⬇ APP PARA WINDOWS** (no bloqueio e na central) baixa o executável do PC;
   - janela própria com o Modo Desk, sem barra do navegador;
   - **ilha no topo da tela**, sempre visível, como no vídeo:
     - em repouso: o avatar pequeno e a hora;
     - durante música: a música tocando;
     - quando você fala com ele: a resposta;
   - tecla de atalho para falar com o JARVIS de qualquer lugar;
   - o JARVIS de sempre continua por trás (mesmos dados, mesma voz, mesmo celular); o .exe é só a "casa" nova dele no Windows.
9. **Fora de casa (celular):** o Modo Desk funciona no navegador do celular, em versão compacta. A ilha e os Copiados são só no PC.

**Versão:** como é um salto grande, a proposta é chamar de **JARVIS 8.0** (a versão atual é a 7.14.2).

**Status:** ✅ **Implementada na versão 8.0.0.**

---

### Ideia 7: Robô ainda mais personalizado, Missões e Ofensiva

**O que foi pedido:** deixar o robô do Modo Desk mais personalizável (na linha do gorro de Natal) e criar um botão de **Missões**: tarefas novas todo dia, ligadas ao uso do JARVIS e ao que ele aprende sobre você, para ir subindo de nível, com uma **ofensiva** de dias seguidos.

#### ✅ Desenho fechado (15/11/2026)

**Decisões do Patrick**
| Tema | Decisão |
|---|---|
| Visual novo | **Tudo:** mais chapéus e acessórios, roupinhas, temas automáticos nas datas, olhos e efeitos |
| Missões | **Todos os tipos:** usar o JARVIS, ensinar sobre você, bem-estar e um desafio da semana |
| Ofensiva | **Com protetor:** sobe a cada dia com pelo menos 1 missão completa; 1 protetor por semana salva um dia esquecido |
| Recompensas | **XP + itens desbloqueáveis** por nível e por ofensiva |

**Como vai ficar**
1. **Guarda-roupa do robô (Personalizar)**, em abas:
   - **Chapéus:** gorro de Natal, cartola, boné, chapéu de bruxa, tiara de gatinho, coroa e headset gamer;
   - **Rosto:** óculos, óculos escuros, bigode e laço;
   - **Roupas:** cachecol, gravata-borboleta, capa de herói, camisa do time e colete de armadura;
   - **Olhos:** arco-reator, coração, estrela e pixel;
   - **Efeitos:** brilho, faíscas e neve caindo.
   - Os itens bloqueados aparecem com cadeado e dizem como liberar ("Nível 5", "7 dias de ofensiva").
2. **Temas nas datas** (pode desligar):
   - no **Natal**, o gorro e a neve; no **Halloween**, a abóbora; no **Carnaval**, o confete;
   - em **dia de jogo do Palmeiras**, a camisa do time.
   - É só por cima do visual escolhido: passada a data, volta ao normal.
3. **🎯 Missões** (nova seção no Modo Desk e um cartão no Início)
   - **3 missões novas por dia**, sorteadas sem repetir as do dia anterior:
     - uma de **usar o JARVIS**: conversar, concluir tarefas, marcar um hábito, pedir um holograma, usar o Olho de Deus…;
     - uma de **ensinar sobre você**: ele faz uma pergunta ("qual sua comida favorita?"), você responde ali mesmo e ele guarda na Memória;
     - uma de **bem-estar**: beber água, fazer uma pausa, caminhar…;
   - as missões de uso são marcadas **sozinhas** quando você faz a ação; as de bem-estar você marca;
   - **desafio da semana**: uma missão maior (ex.: "5 dias com todos os hábitos"), com bastante XP.
4. **🔥 Ofensiva**
   - sobe 1 a cada dia em que você completa **pelo menos 1 missão**;
   - você ganha **1 protetor por semana** (guarda até 2), que salva a ofensiva automaticamente se você esquecer um dia;
   - aparece na barra lateral ao lado do nível, com o recorde.
5. **Recompensas:** cada missão dá XP (o desafio da semana dá mais); subir de nível e manter a ofensiva libera itens do guarda-roupa, com aviso "Item novo liberado: capa de herói!".
6. **Voz:** "quais são minhas missões?" e "como está minha ofensiva?".
7. **Fora de casa:** dá para ver as missões e marcar as de bem-estar pelo celular; o PC aplica na sincronização.

**Status:** implementado na versão 8.1.0.

---

## Ideias extras do Claude (para avaliar)

| # | Ideia | Por que vale |
|---|-------|--------------|
| A | **Chamada entre aparelhos ("Drop In")**: falar por voz ou vídeo do celular com o PC, como um interfone | Já estava na fila (era o próximo item antes destas ideias) |
| B | **Modo quiosque:** um tablet ou celular velho vira uma "tela do JARVIS" fixa na cozinha ou na sala, como o Echo Show | Aproveita a Área Limpa que já existe |
| C | **Reconhecer quem está falando pela voz** (você, sua esposa, visitante) e responder com o perfil certo | Deixa a casa toda usar o JARVIS |
| D | **Backup automático na nuvem** dos dados importantes (listas, lembretes, memórias), com restauração fácil | Proteção contra perder tudo se o PC der problema |
| E | **Rotinas personalizadas** montadas por você ("quando eu disser 'cheguei', acende…, toca…, me lembra…") | Base para a casa inteligente no futuro |
| F | **Resumo da semana** todo domingo: água, tarefas feitas, compromissos da próxima semana | Hábito e motivação |
| G | **Modo visita / modo criança:** respostas e acessos limitados quando outra pessoa usa | Segurança e privacidade |
| H | **Funcionar sem internet no básico** (hora, timers, alarmes, listas) | Antes estava na lista como item 6 |

Itens que já estavam na lista e continuam **em espera**:
- 🏠 casa inteligente (ainda sem aparelhos);
- 🎵 música em vários cômodos;
- 🛍 compras no site do mercado.

---

## Ordem sugerida (para decidir amanhã)

1. **Ideia 2 (segurança).** Vem antes de tudo, porque as outras ideias abrem mais portas (fotos, agentes, chamadas).
2. **Ideia 1 (upload de fotos)**, já nascendo com as regras de segurança.
3. **Ideia 3 (chat com `@agente` e novos agentes).**
4. **Ideia 5 (holograma e pesquisa animada).**
5. **Ideia 4 (Olho de Deus com dados reais).**
6. Extras, na ordem que o Patrick escolher.

---

## Anotações da conversa
_Espaço para ir anotando as decisões de cada ideia._

- **15/11:** Ideia 7 (guarda-roupa do robô, Missões e Ofensiva) desenhada e decidida.
- **15/11:** Ideia 6 publicada (JARVIS 8.0.0).
- **15/11:** Ideia 6 (Modo Desk, a partir de 2 vídeos) desenhada e decidida: robô JARVIS, JARVIS.exe com ilha no topo, Hábitos, Copiados, Nível/XP, Memória em mapa e cor escolhida pelo usuário.
- **15/11:** Ideia 5 concluída (7.14.0). Bloqueio volta ao clássico com a verificação nova do rosto (pedido do Patrick).
- **15/11:** Ideia 5, parte 1 publicada (7.13.0). Antes: Olho de Deus sem chave de mapa e lançamentos (7.11.1) e bloqueio estilo ORBE (7.12.0), a pedido do Patrick com os vídeos.
- **15/11:** Ideia 5 (Holograma e pesquisa animada) desenhada e decidida: 4 tipos de animação, fotos nas cenas, trilha ambiente, perguntar no meio, quiz, salvar e rever, e cartão animado para perguntas rápidas.
- **15/11:** Ideia 4 publicada (7.11.0). Próxima: ideia 5 (Holograma e pesquisa animada).
- **15/11:** Ideia 4 (Olho de Deus) desenhada e decidida: globo 3D real, radar de chuva, voos, terremotos, queimadas e ISS, avisos de chuva, perto de mim e ISS (cada um desligável), categorias sem dados escondidas.
- **15/11:** Ideia 3.1 publicada (7.10.0). Próximas: ideia 4 (Olho de Deus) e 5 (Holograma).
- **15/11:** Ideia 3.1 (finanças completo) desenhada e decidida: dívidas, contas fixas, cartão, orçamento/metas, plano comparando os dois métodos, avisos D-3 e no dia, nuvem só anota e mostra resumo.
- **15/11:** Ideia 3 publicada (7.9.0). Próximas: ideia 4 (Olho de Deus) e 5 (Holograma).
- **15/11:** Ideia 3 (chat com @agente) desenhada e decidida: abas e @ no campo, memória de 30 mensagens por agente, 4 agentes novos (Mercado, Finanças, Secretário, Professor) e voz.
- **15/11:** Ideia 1 publicada (7.8.0). Próximas: ideia 3 (chat com @agente), 4 (Olho de Deus) e 5 (Holograma).
- **15/11:** Ideia 1 (upload de fotos) desenhada e decidida: os três jeitos de enviar, as quatro funções, nada guardado e funcionando pela nuvem.
- **15/11:** Ideia 2 concluída: parte 1 (7.6.0) e parte 2/https (7.7.0).
- **15/11:** Ideia 2, parte 1 publicada (7.6.0).
- **15/11:** Ideia 2 (segurança) desenhada e decidida: chave por aparelho, aprovação de aparelho novo no PC, todos os avisos de tentativa suspeita e https na rede de casa.
