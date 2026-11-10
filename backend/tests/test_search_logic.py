import sys
from pathlib import Path
import unittest

# Adiciona backend ao sys.path para importação dos módulos
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from modules.tools import is_factual_query, extract_deep_search_request


class TestSearchLogic(unittest.TestCase):
    def test_factual_query_matches(self):
        """Perguntas factuais / recentes devem ser detectadas para busca via navegador."""
        self.assertTrue(is_factual_query("quem ganhou o jogo ontem"))
        self.assertTrue(is_factual_query("qual o resultado do jogo"))
        self.assertTrue(is_factual_query("noticias sobre tecnologia"))
        self.assertTrue(is_factual_query("qual o valor da empresa"))

    def test_factual_query_exclusions(self):
        """Perguntas pessoais e lembretes NÃO devem ir ao navegador (R4)."""
        self.assertFalse(is_factual_query("quando é meu lembrete"))
        self.assertFalse(is_factual_query("quando e meu lembrete"))
        self.assertFalse(is_factual_query("quais são meus lembretes"))
        self.assertFalse(is_factual_query("minha tarefa"))
        self.assertFalse(is_factual_query("quem sou eu"))
        self.assertFalse(is_factual_query("quem e voce"))

    def test_extract_deep_search_request(self):
        """Comandos explícitos de pesquisa profunda devem ser extraídos corretamente."""
        is_deep, q = extract_deep_search_request("pesquisa profunda sobre buracos negros")
        self.assertTrue(is_deep)
        self.assertEqual(q, "buracos negros")

        is_deep, q = extract_deep_search_request("pesquise a fundo o mercado de IA")
        self.assertTrue(is_deep)
        self.assertEqual(q, "o mercado de IA")

        is_deep, q = extract_deep_search_request("pesquise tutorial de python")
        self.assertFalse(is_deep)
        self.assertEqual(q, "")


if __name__ == "__main__":
    unittest.main()
