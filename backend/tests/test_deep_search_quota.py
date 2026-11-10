import json
import sys
from pathlib import Path
import unittest

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import settings
from modules import deep_search_quota


class TestDeepSearchQuota(unittest.TestCase):
    def setUp(self):
        self._orig_file = deep_search_quota._QUOTA_FILE
        self._test_file = settings.DATA_DIR / "_test_deep_search_usage.json"
        deep_search_quota._QUOTA_FILE = self._test_file
        if self._test_file.exists():
            self._test_file.unlink()

    def tearDown(self):
        if self._test_file.exists():
            self._test_file.unlink()
        deep_search_quota._QUOTA_FILE = self._orig_file

    def test_consume_and_refund(self):
        """Testa o consumo da cota e o reembolso em caso de falha na API (R2)."""
        status_inicial = deep_search_quota.get_status()
        self.assertEqual(status_inicial["count"], 0)

        # Consumo de uma cota
        deep_search_quota.consume()
        status_pos = deep_search_quota.get_status()
        self.assertEqual(status_pos["count"], 1)

        # Falha na API -> Reembolso (R2)
        refunded = deep_search_quota.refund()
        self.assertTrue(refunded)
        status_reembolsado = deep_search_quota.get_status()
        self.assertEqual(status_reembolsado["count"], 0)

    def test_quota_day_rollover(self):
        """Testa a virada do dia: dados de ontem devem resetar o contador para 0."""
        yesterday_data = {"date": "2020-01-01", "count": 10}
        self._test_file.write_text(json.dumps(yesterday_data), encoding="utf-8")

        status = deep_search_quota.get_status()
        self.assertEqual(status["count"], 0)
        self.assertNotEqual(status["date"], "2020-01-01")


if __name__ == "__main__":
    unittest.main()
