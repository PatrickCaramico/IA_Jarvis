"""V6.5.14: entender melhor o que foi falado."""
from modules import voice_fix as vf

KNOWN = ["youtube", "netflix", "spotify", "google", "gmail", "whatsapp", "notion", "max", "calculadora",
         "bloco de notas", "instagram", "chatgpt", "claude"]


def test_fixes_common_mishearings():
    assert vf.apply_fixes("abre o iutubi") == "abre o youtube"
    assert vf.apply_fixes("abri o you tube") == "abre o youtube"
    assert vf.apply_fixes("toca espotifai") == "toca spotify"
    assert vf.apply_fixes("abre o chat gpt") == "abre o chatgpt"


def test_bare_name_opens_like_alexa():
    assert vf.bare_target("youtube", KNOWN) == "youtube"
    assert vf.bare_target("o netflix", KNOWN) == "netflix"
    assert vf.bare_target("youtube ai", KNOWN) == "youtube"
    assert vf.bare_target("jarvis youtube", KNOWN) == "youtube"
    assert vf.bare_target("vai no youtube", KNOWN) == "youtube"
    assert vf.bare_target("entra no netflx", KNOWN) == "netflix"


def test_does_not_hijack_other_phrases():
    for phrase in ("noticias", "clima", "tarefas", "agenda", "e mails", "comandos", "que horas sao",
                   "vai na lista de compras", "bom dia", "me conta uma piada sobre o youtube"):
        assert vf.bare_target(phrase, KNOWN) is None, phrase
