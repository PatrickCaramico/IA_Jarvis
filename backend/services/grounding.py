"""V8.12: IA com os pés no chão (menos alucinação).

Três peças, usadas pelo motor de conversa e pelo orquestrador da IA:

- `needs_fresh_facts(frase)`: a pergunta depende de fato atual (notícia, placar, preço, cargo, lançamento,
  "hoje", "ainda", "último")? Então vai para a IA COM pesquisa no Google. Antes só um punhado de frases fixas
  ("quem ganhou", "notícias sobre") pesquisava; "quais as notícias da DC" ia para a IA sem pesquisa e ela
  inventava manchetes com cara de verdade.
- `RULES`: as regras de veracidade que entram no SYSTEM_PROMPT de todas as IAs.
- notas por pedido: com pesquisa, "responda só com o que as fontes dizem"; sem pesquisa numa pergunta que pede
  fato atual, "avise que pode estar desatualizado e ofereça pesquisar" (em vez de chutar).
"""
from __future__ import annotations

import re
import unicodedata


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


# Coisas que mudam com o tempo: sem pesquisa, a IA responde com o que sabia no treino (às vezes de anos atrás)
_FRESH = re.compile(
    r"\b(?:"
    r"noticias?|novidades?|manchetes?|lancamentos?|lancou|lancaram|vai lancar|estreia|estreou|"
    r"hoje|ontem|agora|atualmente|atual|atuais|ultim[oa]s?|recentes?|recentemente|ainda|"
    r"essa semana|esta semana|semana passada|esse mes|este mes|esse ano|este ano|ano passado|"
    r"placar|resultado|rodada|tabela|classificacao|escalacao|jogo de|proximo jogo|campeonato|"
    r"cotacao|preco|precos|quanto custa|quanto esta|valor do|valor da|inflacao|selic|bolsa|dolar|euro|bitcoin|"
    r"presidente|governador|prefeito|ministro|ceo|tecnico do|tecnico da|tecnico de|tecnico atual|"
    r"esta vivo|morreu|faleceu|eleicao|eleicoes|pesquisa eleitoral|"
    r"previsao de|anunciou|anunciaram|confirmou|confirmaram|saiu|vai sair|quando sai|data de lancamento|"
    r"20[2-3]\d"
    r")\b"
)

# Pedido sobre o próprio usuário, o JARVIS ou as coisas do PC: a resposta está aqui, não na internet
_LOCAL = re.compile(
    r"\b(?:meus?|minhas?|comigo|eu tenho|eu fiz|lembretes?|tarefas?|timers?|alarmes?|"
    r"lista de compras|agua|computador|pc|notebook|processador|memoria|disco|janelas?|monitor|"
    r"senha|area de transferencia|copiei|piada|historia|poema|conselho|me ajuda a|me explica como|"
    r"tenho|agenda|compromissos?|reunioes?)\b"
    # Pedido de ação ("toca a última do Coldplay", "abre as notícias"): com pesquisa a IA não usa as Skills
    r"|^(?:jarvis[\s,]+)?(?:por favor[\s,]+)?(?:toca|tocar|coloca|bota|abre|abrir|liga|desliga|manda|envia|"
    r"cria|marca|agenda|anota|lembra|pausa|para|aumenta|diminui|fecha|salva|organiza|mostra a tela)\b"
)

# Pergunta de conhecimento geral que não muda (definição, conta, explicação): dispensa pesquisa
_TIMELESS = re.compile(r"^(?:o que (?:e|significa)|como (?:funciona|se faz|fazer)|por que|explica|explique|"
                       r"qual a diferenca|quanto e \d|traduz)")


def needs_fresh_facts(message: str) -> bool:
    """A pergunta precisa de informação atual (e, portanto, de pesquisa) para não virar chute?"""
    norm = re.sub(r"^(?:jarvis|ei jarvis|ok jarvis)[\s,]+", "", _norm(message).strip())  # o nome não é o assunto
    if len(norm) < 8 or not _FRESH.search(norm):
        return False
    if _LOCAL.search(norm):
        return False
    # "o que é inflação" é conceito; "qual a inflação de hoje" é dado: só dispensa quando nada indica tempo
    if _TIMELESS.search(norm) and not re.search(r"\b(?:hoje|agora|atual|ultim|recente|20[2-3]\d)", norm):
        return False
    return True


RULES = (
    "Regras de veracidade (valem acima do tom e da brevidade): "
    "nunca invente fatos, números, datas, nomes, cargos, placares, preços, citações, manchetes, fontes ou links. "
    "Se não tiver certeza, diga que não tem certeza em poucas palavras, em vez de completar com um palpite; "
    "se for palpite ou estimativa, diga que é. "
    "Seu conhecimento tem data de corte: sobre o que pode ter mudado (notícias, resultados, preços, quem ocupa "
    "um cargo, lançamentos), só afirme com base na pesquisa ou nos dados fornecidos nesta mensagem; sem eles, "
    "avise que pode estar desatualizado e ofereça pesquisar. "
    "Com resultados de pesquisa, use só o que as fontes dizem e cite a fonte; se elas não respondem a pergunta "
    "ou se contradizem, diga isso. Nunca cite uma fonte que não apareceu. "
    "Se a pergunta tiver uma premissa falsa ou que você não pode confirmar, aponte com educação em vez de seguir nela. "
    "Prefira uma resposta curta e certa a uma longa e duvidosa."
)

WEB_NOTE = ("Este pedido vai com pesquisa no Google: responda só com o que as fontes encontradas dizem, diga de "
            "quando é a informação se ela puder mudar e, se a pesquisa não trouxer a resposta, diga isso.")

NO_SEARCH_NOTE = ("Atenção: este pedido depende de informação atual, mas a pesquisa na internet não está disponível "
                  "agora. Não afirme fatos recentes como certos: diga em uma frase que pode estar desatualizado, dê só "
                  "o que tem certeza (se houver) e ofereça pesquisar.")


def turn_note(message: str, web: bool) -> str:
    """A nota do pedido para o prompt (vazia quando não precisa)."""
    if web:
        return WEB_NOTE
    return NO_SEARCH_NOTE if needs_fresh_facts(message) else ""
