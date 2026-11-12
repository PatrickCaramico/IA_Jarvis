# Usar o JARVIS fora de casa (V6.0)

Na Wi-Fi de casa, o app conversa direto com o PC. Fora de casa (4G, trabalho, rua) o celular não
enxerga o PC, a não ser por uma **rede privada** entre os seus aparelhos. O JARVIS usa o **Tailscale**
para isso: é grátis para uso pessoal, não abre nenhuma porta no roteador e só os **seus** aparelhos
entram nessa rede.

O notebook precisa estar ligado e com o JARVIS aberto em casa.

## Passo a passo (uma vez só)

1. **No PC:** baixe o Tailscale em https://tailscale.com/download, instale e entre com a sua conta
   (Google, Microsoft ou GitHub).
2. **No celular:** instale o **Tailscale** pela Play Store e entre com **a mesma conta**. Deixe ele ligado
   (ele fica quietinho na barra do Android).
3. **No PC:** rode o `Iniciar-JARVIS.bat` de novo (para o JARVIS enxergar o Tailscale).
4. **No celular, ainda em casa:** abra o app do JARVIS uma vez. Ele pergunta ao PC o endereço do
   Tailscale e guarda.

Pronto. Fora de casa, ao abrir o app, ele tenta a Wi-Fi de casa; se não achar, entra sozinho pelo
Tailscale. Nada muda no uso: a mesma central, a mesma voz, a lista de compras etc.

## Como saber se funcionou

- Desligue a Wi-Fi do celular (fica só no 4G) e abra o app: a central deve abrir normalmente.
- Na central, em NÚCLEO · SERVIÇOS › APARELHOS CONECTADOS, o celular aparece igual.

## Segurança

- O Tailscale criptografa tudo entre o celular e o PC; ninguém de fora da sua conta entra.
- Mesmo dentro dessa rede, o JARVIS continua pedindo a chave de pareamento do app e o bloqueio
  (rosto, PIN ou digital) — igual em casa.
- Para cortar o acesso de um celular perdido: no site do Tailscale, remova o aparelho; e no JARVIS,
  troque a chave de pareamento (apague `data/access_token.txt` e reinicie: todos os aparelhos pareiam de novo).

## Detalhes técnicos

- O PC informa o endereço do Tailscale (faixa 100.64.0.0/10) em `/api/mobile/info` (`remote_host`) e
  em `/api/network-access`.
- O app guarda esse endereço e, quando a Wi-Fi de casa não responde, troca só o endereço e mantém a chave.
- O backend aceita a central aberta por endereços do Tailscale (100.64–100.127.x.x e `*.ts.net`).
