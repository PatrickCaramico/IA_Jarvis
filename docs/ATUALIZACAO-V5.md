# Atualização V5.0.0: sites, Modo Torcedor e publicação

9 de novembro de 2026.

## O que muda para você

### Uma versão do JARVIS

A versão do backend é a fonte única. O build do APK grava a mesma versão no manifesto temporário e calcula um `versionCode` maior que o legado, permitindo instalar a atualização sobre o app anterior.

### Meus Sites

- Em **Configurações > Meus Sites**, cadastre um nome, URL e apelidos para abrir pelo nome ou por voz.
- URLs sem protocolo recebem `https://`; a tela aceita somente `http://` e `https://`.
- A opção de abrir como aplicativo usa uma janela do Chrome quando disponível e recorre ao navegador padrão se não estiver.
- Os atalhos antigos continuam compatíveis. Programas locais continuam sendo definidos no arquivo de atalhos, não nessa tela.

### Modo Torcedor

- Os escudos aparecem no placar, no bloqueio e no banner do dia de jogo.
- O escudo do adversário é guardado localmente depois do primeiro download. Sem imagem, o Palmeiras usa seu arquivo local e o adversário mostra a inicial do nome.
- Jogos marcados como ao vivo que ultrapassam a janela de três horas são encerrados na leitura e reconsultados uma vez. No dia seguinte, o jogo antigo deixa de esconder o próximo.
- Uma ativação manual ou automática em dia de jogo desliga o modo no dia seguinte e avisa qual é a próxima partida. Ativá-lo manualmente num dia sem jogo continua mantendo-o ligado.

### Avisos de atualização

- Em **Configurações > Manutenção**, o PC consulta a release pública do GitHub e mostra a versão, as notas e o link. Há também uma checagem diária em segundo plano; não baixa nem instala atualizações.
- Ao abrir uma conexão salva, o app Android compara sua versão com `/api/mobile/info`. Se houver um APK mais novo no PC, oferece abrir o download; a instalação continua manual.

## Publicação e manutenção

- `.github/workflows/ci.yml` executa lint, testes e build em Windows para backend e frontend.
- `.github/workflows/release-apk.yml` prepara o APK assinado ao receber uma tag `v*` e usa as notas da seção correspondente do `CHANGELOG.md`.
- Configure a keystore e a senha como secrets do GitHub seguindo [RELEASE.md](RELEASE.md). A workflow usa uma cópia temporária da chave e a remove ao terminar.

## Para quem mexe no código

| Arquivo | O que mudou |
| --- | --- |
| `backend/modules/tools.py`, `backend/routes/productivity.py` | CRUD de sites, compatibilidade com atalhos antigos e abertura por alias. |
| `backend/modules/sports_provider.py`, `backend/routes/fan.py`, `backend/core/watchers.py` | Cache e reservas de escudos, seleção de partidas e encerramento do Modo Torcedor no dia seguinte. |
| `frontend/src/components/settings/SitesSettings.jsx`, `FanScoreWidget.jsx`, `FanLockPanel.jsx`, `FanMatchBanner.jsx` | Gerenciamento de sites e exibição dos escudos/reservas. |
| `frontend/src/utils/updateCheck.js`, `frontend/src/components/settings/MaintenanceSettings.jsx`, `mobile/android/src/com/patrick/jarvis/MainActivity.java` | Verificações de atualização no PC e Android. |
| `.github/workflows/ci.yml`, `.github/workflows/release-apk.yml`, `scripts/android/build_apk.ps1` | CI, publicação do APK e versionamento do manifesto de build. |

## Validação

Na validação local, passaram 233 testes Python (backend e scripts), 57 testes frontend, Ruff, lint frontend sem erros e build Vite. O build Android completo foi verificado com uma keystore descartável, não com a chave de release real.

**Ainda não foi testado:** executar as workflows no GitHub com os secrets do repositório, publicar uma release real ou instalar o APK num celular. O APK de produção requer os secrets `ANDROID_KEYSTORE_BASE64` e `ANDROID_KEYSTORE_PASSWORD`.
