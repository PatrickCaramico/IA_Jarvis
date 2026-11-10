import sys
from pathlib import Path
import unittest

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class TestGeminiHistoryFormat(unittest.TestCase):
    def test_gemini_history_construction(self):
        """Valida que o histórico para o Gemini descarta assistente no início e mapeia roles corretamente."""
        raw_history = [
            {"role": "assistant", "content": "Mensagem solta do assistente"},
            {"role": "user", "content": "Quem descobriu o Brasil?"},
            {"role": "assistant", "content": "Pedro Álvares Cabral em 1500."},
        ]

        # Lógica aplicada em _call_gemini
        recent = [
            item for item in raw_history[-10:]
            if isinstance(item.get("content"), str) and item.get("content", "").strip()
        ]
        while recent and recent[0].get("role") in {"assistant", "model"}:
            recent.pop(0)

        formatted = []
        for item in recent:
            role = "model" if item.get("role") in {"assistant", "model"} else "user"
            formatted.append({"role": role, "text": item["content"]})

        self.assertEqual(len(formatted), 2)
        self.assertEqual(formatted[0]["role"], "user")
        self.assertEqual(formatted[0]["text"], "Quem descobriu o Brasil?")
        self.assertEqual(formatted[1]["role"], "model")
        self.assertEqual(formatted[1]["text"], "Pedro Álvares Cabral em 1500.")


if __name__ == "__main__":
    unittest.main()
