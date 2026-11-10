"""Testes unitários para o Modo Torcedor e Provedor Esportivo (Palmeiras / Glassmorphism)."""
import unittest
from modules import fan_mode, sports_provider, prefs


class TestFanMode(unittest.TestCase):
    def test_registered_teams(self):
        """Valida se o Palmeiras está registrado com as chaves esperadas."""
        self.assertIn("palmeiras", fan_mode.FAN_TEAMS)
        info = fan_mode.FAN_TEAMS["palmeiras"]
        self.assertEqual(info["id"], "palmeiras")
        self.assertIn("Palmeiras", info["name"])
        self.assertIn("badge_url", info)
        self.assertEqual(info["shout_phrase"], "Avante Palestra!")
        self.assertIn("colors", info)
        self.assertIn("primary", info["colors"])

    def test_match_schedule_and_countdown(self):
        """Valida se o cálculo de partidas retorna dados válidos com contagem regressiva."""
        match_data = sports_provider.get_current_or_next_match("palmeiras")
        self.assertIsInstance(match_data, dict)
        self.assertEqual(match_data["team"], "palmeiras")
        self.assertIn("opponent", match_data)
        self.assertIn("countdown", match_data)
        self.assertIn("score", match_data)
        self.assertIn("status", match_data)
        # V4.4: "unknown" = sem agenda ainda (sem internet na primeira abertura); "postponed" = adiado
        self.assertIn(match_data["status"], ["scheduled", "live", "finished", "unknown", "postponed"])

    def test_shout_control_deduplication(self):
        """Valida que o grito de torcida não dispara quando o jogo não está rolando."""
        # Se status != live, não deve disparar
        self.assertFalse(sports_provider.should_trigger_shout("palmeiras"))

    def test_fan_mode_prefs_toggle(self):
        """Valida que prefs.update aceita tanto dicionário quanto kwargs sem TypeError."""
        res1 = prefs.update({"fan_mode_enabled": True})
        self.assertTrue(res1["fan_mode_enabled"])

        res2 = prefs.update(fan_mode_enabled=False)
        self.assertFalse(res2["fan_mode_enabled"])


if __name__ == "__main__":
    unittest.main()
