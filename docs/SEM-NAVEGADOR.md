# JARVIS sem o navegador aberto: o que funciona e o que falta (V6.2, ouvido na V6.3)

Levantamento feito no código em 12/11/2026. O JARVIS tem duas partes:

- o **backend** (o "cérebro", Python, roda escondido no PC desde o `Iniciar-JARVIS.bat`);
- a **central** (a tela, no navegador do PC — site ou `127.0.0.1:5173` — ou no app do celular).

## Já funciona sem nenhuma aba aberta (só o backend)

| Recurso | Onde está | Observação |
| --- | --- | --- |
| Alarmes (tocar, falar a hora, soneca por tempo) | `modules/alarms.py` (`worker_loop`) | Toca e fala pela caixa do PC. Para parar sem tela: ele desliga sozinho em 10 min. |
| Lembretes falados | `modules/reminders.py` (`reminder_worker_loop`) | Fala na hora marcada. |
| Lembrete de água, gatilhos, Modo Torcedor (gols, início de jogo) | `core/watchers.py` | Falam pela caixa do PC. |
| Avisos no celular (lembretes, água, alarmes, jogo) | `/api/mobile/notifications` + app | O app consulta o PC mesmo com a central fechada. |
| App do celular inteiro | app Android | O celular **é** a tela: conversa, voz no celular, lista de compras, briefing. |
| Ligar o JARVIS com 2 palmas | `scripts/clap_launcher.py` (Instalar-Palmas-no-Windows.bat) | Ouve o microfone pelo Windows e abre a central. |
| Voz (falar) | `modules/tts.py` | A voz sai do backend, não do navegador. |
| **"Jarvis, …" pelo microfone do PC (V6.3)** | `scripts/voice_listener.py` | Ouvido offline com Vosk: acorda com "Jarvis", manda o pedido ao chat e responde pela caixa. Fica quieto com a central aberta numa aba do PC. |

## Depende da aba aberta no PC

| Recurso | Por quê |
| --- | --- |
| **"Jarvis, …" (palavra de ativação) e a conversa por voz no PC** | Usa o reconhecimento de voz do **Chrome** (Web Speech API, `useSpeechRecognition.js` / `useSentinelListener.js`). Só funciona com a aba aberta, e o áudio passa pelo serviço do Google. |
| Modo Sentinela (escuta na tela de bloqueio) | Mesmo motivo: reconhecimento do Chrome. |
| Palmas dentro da página | `useClapDetector.js` usa o microfone da aba (as palmas do Windows, acima, não dependem). |
| Briefing ao entrar, saudação, telas e cartões | São disparados ao entrar na central (a entrada é a tela). Por voz no celular, o briefing roda igual. |
| Verificação do rosto | A câmera é do backend, mas quem pede a verificação é a tela de bloqueio. |

## O que precisa para o PC atender por voz **sem** navegador

1. **Um "ouvido" no próprio backend** (serviço Python, o mesmo jeito do ouvinte de palmas):
   microfone sempre ligado + **palavra de ativação offline** ("Jarvis") + **reconhecimento do comando**.
   - Opção recomendada: **Vosk** (offline, modelo pt-BR pequeno ~50 MB, leve na CPU, ~150–250 MB de RAM),
     usado nas duas etapas: frase curta "jarvis" com gramática limitada para acordar, e o modelo completo
     para o pedido. Nada vai para a internet.
   - Alternativas: openWakeWord (só a ativação; o comando ainda precisaria de Vosk/Whisper);
     Whisper local (mais preciso, mas pesa no notebook); Porcupine (exige chave da Picovoice).
2. **Ligar a fila de pedidos**: o texto reconhecido vai para o mesmo caminho do chat
   (`core/turns.handle_turn`), e a resposta sai pela caixa do PC — sem tela nenhuma.
3. **Respeitar o bloqueio**: sem a central, pedidos pessoais continuam exigindo acesso liberado
   (como o Sentinela hoje: com o PC bloqueado, só pedidos públicos — hora, clima, música, alarme).
4. **Iniciar com o Windows** (opcional): uma tarefa no Agendador para rodar o `Iniciar-JARVIS.bat` ao entrar
   no Windows — aí nem o duplo clique é necessário.

**Esforço estimado:** médio (1 módulo novo `modules/voice_listener.py` + instalador como o das palmas + testes),
mais o download do modelo Vosk (~50 MB) uma vez. **Custo no notebook:** um núcleo com uso baixo e contínuo
enquanto escuta (o detector só "acorda" o reconhecimento completo depois do "Jarvis").

> **Feito na V6.3:** o ouvido foi feito como `scripts/voice_listener.py` (processo separado, como as palmas),
> ligado pelo `Iniciar-JARVIS.bat` quando o modelo está em `%USERPROFILE%\.jarvis-voice\vosk-model-small-pt-0.3`.
> Pacotes: `pip install -r scripts/requirements-ouvido.txt`. Teste: `python scripts/voice_listener.py --test`.
> Desligar: Configurações › Mídia & Foco › "Ouvir Jarvis com o navegador fechado".

**Resumo (antes da V6.3):** com a aba fechada, o JARVIS continua **avisando e falando** (alarmes, lembretes, água,
jogo, celular), mas **não escuta** pelo PC. Para escutar sem navegador, o passo é o ouvido offline no backend.
