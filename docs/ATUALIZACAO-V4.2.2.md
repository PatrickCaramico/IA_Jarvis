# JARVIS v4.2.2 — Registro da atualização

Base: a 4.2 aplicada em 30/10/2026. Ajustes pedidos pelo Patrick depois de testar a 4.2 e o que
faltava do Branding Book (sons, esqueleto, kit de logo). V4.3 e V5 ficam para depois.

## 1. Decisões tomadas (confirmadas pelo Patrick)

| Decisão | Escolha |
| --- | --- |
| Microfone no bloqueio | Começa **silenciado** sempre que a tela de bloqueio abre: escuta do Sentinela **e** palmas. Liga com a tecla **P** ou um clique |
| Coluna da direita | Recolhe após **3 minutos** sem uso e **reabre sozinha** quando você fala ou o JARVIS responde |
| Sons | Repouso, ouvindo, sucesso e erro; volume e modo "só o que importa"; silêncio das 22h às 7h |
| Extras | Os quatro grupos: sons; versão + estado na aba; sem conexão + estados vazios; diagnóstico + exportar/importar |
| Kit de logo | Avatar, banner, compartilhamento 1200×630 e boas-vindas levemente animada |
| Branding Book | Capítulo das versões antigas espera a história do Patrick; assinatura "Escrito e desenvolvido por Patrick Souza" no fim (md e versão animada) |

## 2. O que foi implementado

### Microfone silenciado no bloqueio
- `App.jsx`: `sentinelMuted` começa `true` e volta a `true` toda vez que a tela vira "lock". As palmas também esperam o microfone ligado.
- Tecla **P** alterna (ignorada enquanto se digita). Botão "MIC SILENCIADO · aperte P para ligar" / "MIC LIGADO" no layout clássico e selo P no Sentinela (`LockScreen.jsx`, `lock-extras.css`).

### "Abrir central" no Modo Sentinela (pedido do Patrick depois do teste)
- Antes: sem "Jarvis" na frente, o pedido aparecia na tela mas era descartado; com "Jarvis", virava pedido pendente e, depois de entrar, rodava "abrir central" como comando.
- Agora: "abrir central", "abre a central", "liberar", "desbloquear", "destravar", "entrar" e "me deixa entrar" (com ou sem a palavra de ativação) iniciam o escaneamento na hora, sem IA e sem nada pendente. Só com o microfone ligado (P ou clique). Os outros pedidos continuam exigindo "Jarvis".
- `utils/wakeWords.js` (`isUnlockPhrase`, `matchUnlock`), `useSentinelListener.js` (`onUnlock`), `App.jsx` (`unlockByVoice`) e a mesma regra no backend (`modules/sentinel.py`, ação `unlock_only`). A legenda passa a dizer "Diga "abrir central" ou "Jarvis, …"".

### Cartão "Tocando agora" (Spotify) (pedido do Patrick depois do teste)
- `components/NowPlaying.jsx`: capa, música, artista, barra de progresso (anda sozinha entre as consultas) e ponto verde com equalizador quando está tocando; "Spotify · pausado" quando pausado; some quando não há nada ou o Spotify não está conectado. Consulta a cada 15 s e para com a aba oculta.
- Tela de bloqueio: embaixo do clima, sem botões. É o cartão `spotify` de Configurações > Bloqueio, ligado uma vez para quem já tinha cartões salvos (se desligar, não volta sozinho).
- Central: embaixo de Sensores · Clima, com ⏮ ⏯ ⏭ (rota de controle que já existia).
- Backend: `spotify.parse_now_playing()` (função pura) e `GET /api/integrations/spotify/track` (cache de 5 s). Com a central bloqueada, a rota só responde se o cartão estiver ligado.

### Coluna da direita recolhe sozinha
- `HudLayout.jsx`: 3 min sem atividade (`RIGHT_IDLE_MS`) recolhe Clima e Canal Ativo; mensagem nova, microfone ou processamento reabrem. Mexer na coluna (clique, rolagem, tecla) conta como uso. Botões RECOLHER ▶ e ◀ CLIMA & CANAL ATIVO (`hud-layout.css`).

### Sons por estado
- `utils/soundEffects.js`: `playListening`, `playStateSuccess`, `playError`, `playIdle` (até 400 ms), volume geral e `soundPolicy(kind, cfg, date)`, função pura com as regras de modo, silêncio noturno e modo silencioso.
- `App.jsx` toca "ouvindo" ao abrir o microfone, "repouso" quando termina de falar ou processar, e sucesso/erro junto com o flash do orbe.
- Preferências `sfx_volume` (0 a 100) e `sfx_mode` (`all`, `important`, `off`), públicas para a tela de bloqueio. Seção **SONS DO JARVIS** em Configurações > Mídia & Foco com prévia.
- Corrigido: `playNotification` não existia e era chamado pelo aviso de modo de pesquisa.

### Carregando, vazio, sem conexão, versão e aba
- `components/ui/Skeleton.jsx` (`Skeleton`, `EmptyState`) aplicados em clima, agenda, Spotify, finanças e notícias do Modo Torcedor; `feedback.css` desliga o brilho com "reduzir movimento".
- `components/ui/OfflineBanner.jsx`: faixa âmbar após 3 s sem conexão; verde por 2,5 s quando volta.
- Versão única: `backend/version.py` e `frontend/src/utils/version.js` (4.2.2) em `/api/health`, FastAPI, topo da central, widget Sobre mim e boas-vindas.
- `utils/tabTitle.js`: "● Ouvindo", "◐ Pensando", "◉ Falando", "🔒 Bloqueado", "○ Sem conexão".

### Diagnóstico e backup de ajustes
- `GET /api/diagnostics` (e `?format=text`): versão, sistema, quais chaves e integrações estão configuradas (só sim/não), estado de execução, algumas preferências e os 25 últimos eventos. O texto dos comandos e das memórias é omitido; detalhes de erro passam por `redact()` (mascara chaves `sk-`/`AIza`, Bearer, `key=`/`token=`/`senha=` e e-mails).
- `GET /api/prefs/export` e `POST /api/prefs/import`: só preferências, sem `camera_index`; a importação passa pelas mesmas validações do `PATCH /api/prefs` e não muda nada se algum valor for inválido.
- As três rotas exigem a central desbloqueada (bloqueio real, negado por padrão).
- Seção **DIAGNÓSTICO & BACKUP** em Configurações > Geral (copia para a área de transferência; se o navegador não deixar, mostra o texto para copiar).

### Kit de logo e boas-vindas
- `scripts/dev/gerar_kit_logo.py` gera em `frontend/public/brand/`: avatar (SVG, 512, 1024), banner 1500×500, compartilhamento 1200×630 e `wordmark.svg`. O nome é desenhado em traço (sem depender de fonte instalada).
- `components/WelcomeLogo.jsx` na tela de inicialização: anéis entram girando, o núcleo acende e "respira", e o nome se desenha letra por letra. Se a IA tiver outro nome, ele aparece em texto.
- Textos "Stark Industries" que restavam na interface foram trocados.

## 3. Testes executados

| Conjunto | Resultado |
| --- | --- |
| Backend (pytest) | 121 aprovados (novos em `tests/test_v422.py`: versão única, prefs de som, `redact`, diagnóstico sem segredos, bloqueio das rotas novas, exportar/importar e importação inválida) |
| Interface (node --test) | 53 aprovados (novos: `sounds.test.js`, `tabTitle.test.js`, `wordmark.test.js`, `unlockPhrase.test.js`) |
| Ponta a ponta (navegador real) | 53/53: inclui rota e cartão do Spotify, "abrir central" no bloqueio, microfone silenciado + tecla P, modo de som salvo, diagnóstico copiado e importação de ajustes |
| Lint | ESLint sem erros (6 avisos antigos); ruff sem erros novos |
| Visual | Esqueleto, vazio, faixa sem conexão, kit de logo e animação de boas-vindas conferidos por captura de tela, também com "reduzir movimento" |

Não testado aqui: o som em si (o ambiente de teste não tem saída de áudio) e a aparência com as
fontes Orbitron/Rajdhani do Google (o teste usa as fontes de reserva).

## 4. Pendências

- Capítulo 7 do Branding Book (histórico de versões): escrito a partir das pastas das versões antigas.
- V4.3 e V5: planejamento separado.

## 5. Como verificar

1. `Parar-JARVIS.bat` e depois `Iniciar-JARVIS.bat`; recarregue o painel com **Ctrl + F5**.
2. Tela de boas-vindas: o Núcleo anima e o nome se desenha.
3. Tela de bloqueio: "MIC SILENCIADO"; aperte **P** e veja "MIC LIGADO".
4. Na central, fique 3 min sem falar: a coluna da direita recolhe; fale algo e ela volta.
5. Configurações > Mídia & Foco > SONS DO JARVIS: teste a prévia e o modo.
6. Configurações > Geral > Copiar diagnóstico; cole num bloco de notas e confira que não há chaves.
7. Pare só o backend com o painel aberto: a faixa âmbar aparece; ao religar, fica verde.
