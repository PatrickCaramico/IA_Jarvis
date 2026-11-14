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

---

### Ideia 4: Olho de Deus mais completo

**O que foi pedido**
- O Olho de Deus ainda está "cru". Deixar ele bem melhor.

**O que já existe hoje**
- Mapa de **trânsito ao vivo** (Waze), com busca, "onde estou" e lugares salvos.
- As outras categorias (voos, satélites, terremotos, clima…) ainda **sem dados reais**.

**Pontos a decidir / possibilidades**
- [ ] Quais camadas trazer primeiro, com dados reais e gratuitos?
  - ✈ **Voos** passando por cima da cidade, ao vivo.
  - 🌎 **Terremotos** das últimas 24 h no mundo.
  - 🔥 **Queimadas** no Brasil (dados do INPE/NASA).
  - ☁ **Radar de chuva** ao vivo.
  - 🛰 **Estação Espacial** passando agora e quando ela passa visível na sua cidade.
- [ ] Um **globo 3D de verdade**, que gira e dá zoom, no lugar do desenho atual.
- [ ] **Alertas:** o JARVIS avisa sozinho ("chuva forte chegando na sua região em 30 min").
- [ ] Comandos de voz: "mostra os voos agora", "tem terremoto hoje?".

---

### Ideia 5: Holograma ainda melhor e pesquisa com animação

**O que foi pedido**
- Deixar o **Holograma** ainda melhor.
- Em **toda pesquisa**, mostrar também **uma animação** sobre o assunto, e não só o texto na tela.

**O que já existe hoje**
- Pedidos como "me explica…", "pesquisa sobre…" e "receita de…" abrem o Holograma: cenas narradas, partículas, esfera 3D, ondas de voz e receita viva.

**Pontos a decidir / possibilidades**
- [ ] **Animação por tipo de assunto**, por exemplo:
  - planeta girando para astronomia;
  - mapa com rota para viagem;
  - gráfico subindo para economia;
  - corpo humano para saúde;
  - linha do tempo para história.
- [ ] **Imagens e vídeos curtos** da internet em cada cena (Wikipédia já entra no fundo; dá para ir além).
- [ ] **Pesquisa rápida animada:** perguntas curtas ("quem ganhou o jogo?") ganham um cartão animado pequeno, sem abrir o Holograma inteiro.
- [ ] **Perguntar no meio da apresentação** ("espera, o que é horizonte de eventos?"): ele responde e continua.
- [ ] **Salvar ou compartilhar** uma apresentação para rever depois.
- [ ] **Modo quiz** no final ("quer testar o que aprendeu?").

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

-
