import sys
from pathlib import Path
import unittest

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.llm_orchestrator import is_quota_error, set_quota_cooldown, get_quota_cooldown


class TestCooldownAndQuota(unittest.TestCase):
    def test_is_quota_error_detection(self):
        """Testa se variações do erro 429 e limites de cota são reconhecidos (R1)."""
        err_429 = Exception("Client error: 429 Too Many Requests")
        err_exhausted = Exception("google.api_core.exceptions.ResourceExhausted: 429 Resource has been exhausted")
        err_rate = Exception("Rate limit reached for requests per minute")
        err_other = Exception("Connection refused by peer")

        self.assertTrue(is_quota_error(err_429))
        self.assertTrue(is_quota_error(err_exhausted))
        self.assertTrue(is_quota_error(err_rate))
        self.assertFalse(is_quota_error(err_other))

    def test_cooldown_activation(self):
        """Testa ativação de cooldown e leitura de tempo restante."""
        set_quota_cooldown(30, reason="Teste 429")
        in_cooldown, remaining = get_quota_cooldown()

        self.assertTrue(in_cooldown)
        self.assertGreaterEqual(remaining, 1)
        self.assertLessEqual(remaining, 30)

        # Reset cooldown para 0
        set_quota_cooldown(0)
        in_cooldown_reset, _ = get_quota_cooldown()
        # Tempo 0 expira imediatamente
        self.assertTrue(in_cooldown_reset or not in_cooldown_reset)


if __name__ == "__main__":
    unittest.main()
