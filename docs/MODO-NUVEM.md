# Modo nuvem: o JARVIS no celular com o notebook desligado (V6.6)

O JARVIS completo roda no notebook (câmera, Sentinela, controle do Windows, Spotify...). Quando o
notebook está desligado ou longe, o **celular** passa a usar o **modo nuvem**, um backend pequeno
que roda no próprio Netlify (o mesmo site da central), sem custo para uso pessoal.

| Onde | Notebook ligado | Notebook desligado |
| --- | --- | --- |
| Navegador do **computador** | Central completa (site normal) | Tela para ligar o JARVIS. **Nunca usa a nuvem.** |
| **Chrome do celular** | Central completa | Modo nuvem, sozinho |
| **App Android** | Central completa | Modo nuvem, sozinho (e volta para a central quando o PC liga) |

## Como é a tela (V6.6.5)

A **mesma central** do app e do site. Depois do PIN da nuvem, um adaptador
(`frontend/src/utils/cloudShim.js`) responde no lugar do PC. Um aviso no topo mostra
"☁ MODO NUVEM · notebook desligado".

**Como o celular decide:** o app tenta o PC (Wi-Fi de casa e, se configurado, Tailscale). Achou: central
do PC, como sempre. Não achou (dados móveis, outra rede ou PC desligado): a mesma central pela nuvem, com
o aviso "☁ ACESSO PELA NUVEM" dizendo se o notebook está ligado em casa (sincronizou há menos de 3 min)
ou desligado. No Chrome do celular, o site (https) não alcança o PC pela rede de casa (o navegador
bloqueia), então ele usa sempre a nuvem.

## O que funciona sem o notebook

| Funciona na nuvem | Só com o notebook ligado |
| --- | --- |
| Conversar com o JARVIS (voz ou texto, com a IA que você escolher) | Câmera, rosto e Sentinela |
| Lista de compras, tarefas, lembretes e alarmes | Abrir sites e programas no PC, controlar o Windows |
| Água do dia (meta, copos, desfazer) | Spotify, volume, tela do PC |
| Notícias (Google Notícias) e clima (Open-Meteo) | Briefing completo, Modo Torcedor, e-mail |
| Agenda dos próximos 7 dias (o PC manda os compromissos; a nuvem nunca recebe a chave do Google) | Conectar ou mudar a agenda |
| Música no próprio celular, pelo app: tocar, pausar, próxima, anterior e "toca …" (abre a busca no Spotify do celular) | Spotify do PC |
| As suas configurações da central: nome da IA, personalidade, fundo, cor, acessibilidade, modo silencioso, temas de notícias e copos de água | Mudar as configurações (mude na central com o PC ligado) |

## Como ligar (uma vez só)

1. No painel do Netlify, abra o site **projeto-jarvis-ia** › **Site configuration** › **Environment variables**
   e crie estas variáveis:

   | Variável | O que colocar |
   | --- | --- |
   | `JARVIS_NUVEM_PIN` | O PIN para entrar no modo nuvem (4 a 8 números). Pode ser diferente do PIN do PC. |
   | `JARVIS_NUVEM_CHAVE` | Uma senha longa e aleatória (ex.: 40 letras e números). Ela assina o acesso e é a chave da sincronização com o PC. |
   | `GEMINI_API_KEY` | A chave da IA (a mesma do `.env` do PC). Também serve `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`. |
   | `LLM_PROVIDER` (opcional) | `gemini`, `openai` ou `anthropic`, se tiver mais de uma chave. |
   | `GEMINI_MODEL` / `OPENAI_MODEL` / `ANTHROPIC_MODEL` (opcional) | Modelo, se quiser trocar o padrão. |
   | `WEATHER_CITY` (opcional) | Cidade do clima antes da primeira sincronização com o PC. |

2. Em **Deploys**, toque em **Trigger deploy › Deploy site** (as variáveis só valem depois de um deploy).
3. No `.env` do PC, coloque a mesma senha: `JARVIS_NUVEM_CHAVE=...` e reinicie o JARVIS
   (`Iniciar-JARVIS.bat`). A partir daí o PC sincroniza a cada minuto.
4. No celular, gere o app novo (`Gerar-App-Android.bat` no PC, ou **ATUALIZAR APP** no celular em casa,
   com o PC ligado): o app 6.6.3 abre o modo nuvem sozinho quando o PC não responde. Pelo Chrome do
   celular, `https://projeto-jarvis-ia.netlify.app/app/` também entra no modo nuvem sem o PC.

Confira em `https://projeto-jarvis-ia.netlify.app/api/cloud/status`: `"configured": true` e `"llm"` com o
nome da IA.

## Como funciona

- **App Android:** tenta o PC (Wi-Fi de casa e, se configurado, o Tailscale). Se nenhum responder, abre
  `…/app/?nuvem=1` e continua conferindo o PC a cada 20 s; quando ele responde, volta para a central completa.
  Com o app fechado, o serviço de avisos consulta a nuvem a cada 30 s (lembretes, alarmes e água), e a
  resposta da nuvem é falada pela voz do Android.
- **Configurações:** a cada minuto o PC manda para a nuvem as configurações de aparência, voz e IA
  (nada de câmera, PIN, atalhos ou chaves). A tela da nuvem aplica a última que chegou.
- **Chrome do celular:** a central tenta o PC; sem resposta, entra no modo nuvem.
- **Navegador do computador:** sempre a central do PC (sem nuvem, nem com `?nuvem=1`).
- **Sincronização:** cada mudança feita na nuvem vira uma operação pendente. O PC, quando ligado, busca as
  operações (`GET /api/cloud/sync`), aplica nas listas dele e manda a foto das listas
  (`POST /api/cloud/sync`), que passa a ser o que a nuvem mostra. Só o perfil principal é sincronizado.
- **Dados:** ficam no Netlify Blobs do seu site (loja `jarvis-nuvem`). A conversa guarda as últimas 24
  mensagens; a água, os últimos 14 dias.

## Segurança

- Entrar exige o PIN do modo nuvem. Depois de 8 PINs errados em 15 minutos, a entrada fica bloqueada.
- O acesso dura 60 dias por aparelho (botão **SAIR** apaga). Para cortar todos os aparelhos, troque a
  `JARVIS_NUVEM_CHAVE` no Netlify (e no `.env` do PC) e faça um deploy.
- A sincronização exige a `JARVIS_NUVEM_CHAVE`, que nunca vai para o celular.
- As chaves da IA ficam só nas variáveis do Netlify, nunca no código nem no navegador.

## Código

- `netlify/functions/nuvem.mjs`: a função (rota `/api/cloud/*`).
- `netlify/nuvem/core.mjs`: a lógica (PIN, listas, avisos, IA, notícias, clima, sincronização).
  Testes: `npm run test:nuvem` na raiz.
- `frontend/src/components/CloudMode.jsx`, `frontend/src/utils/cloudApi.js`, `frontend/src/cloud.css`: a tela.
- `backend/modules/cloud_sync.py`: a sincronização do PC. Testes: `backend/tests/test_cloud_sync_66.py`.
- App: `MainActivity.java` (abre a nuvem, confere o PC, voz do Android) e `NotifyService.java` (avisos da nuvem).
