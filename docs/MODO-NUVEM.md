# Modo nuvem: o JARVIS no celular com o notebook desligado (V6.6)

O JARVIS completo roda no notebook (câmera, Sentinela, controle do Windows, Spotify...). Quando o
notebook está desligado ou longe, o **navegador** (do celular ou do computador) passa a usar o
**modo nuvem**, um backend pequeno que roda no próprio Netlify (o mesmo site da central), sem custo
para uso pessoal.

**O app Android não usa a nuvem** (V6.6.2): ele continua falando só com o PC, como sempre.

## O que funciona sem o notebook

| Funciona na nuvem | Só com o notebook ligado |
| --- | --- |
| Conversar com o JARVIS (voz ou texto, com a IA que você escolher) | Câmera, rosto e Sentinela |
| Lista de compras, tarefas, lembretes e alarmes | Abrir sites e programas no PC, controlar o Windows |
| Água do dia (meta, copos, desfazer) | Spotify, volume, tela do PC |
| Notícias (Google Notícias) e clima (Open-Meteo) | Briefing completo, Modo Torcedor, e-mail |
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
4. No celular, abra pelo **navegador** `https://projeto-jarvis-ia.netlify.app/app/`: sem o PC, ele entra
   no modo nuvem. Dica: no Chrome, ⋮ › **Adicionar à tela inicial** cria um atalho só para ele.

Confira em `https://projeto-jarvis-ia.netlify.app/api/cloud/status`: `"configured": true` e `"llm"` com o
nome da IA.

## Como funciona

- **App Android:** igual antes: só o PC (Wi-Fi de casa e, se configurado, o Tailscale).
- **Configurações:** a cada minuto o PC manda para a nuvem as configurações de aparência, voz e IA
  (nada de câmera, PIN, atalhos ou chaves). A tela da nuvem aplica a última que chegou.
- **Navegador do celular:** a central tenta o PC; sem resposta, entra no modo nuvem. No navegador do
  computador, a tela de "PC desligado" ganhou o botão **USAR PELA NUVEM**.
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
