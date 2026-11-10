"""Testes unitários para o Módulo de Hidratação e Lembrete de Água (Fase W)."""
import unittest
from modules import water


class TestWaterTracker(unittest.TestCase):
    def setUp(self):
        water.reset_today()
        water.set_goal(2000)

    def test_initial_status(self):
        st = water.get_status()
        self.assertEqual(st["total_ml"], 0)
        self.assertEqual(st["goal_ml"], 2000)
        self.assertEqual(st["percentage"], 0)
        self.assertFalse(st["goal_reached"])

    def test_add_intake_and_percentage(self):
        st = water.add_intake(500, "garrafa de água")
        self.assertEqual(st["total_ml"], 500)
        self.assertEqual(st["percentage"], 25)
        self.assertFalse(st["goal_reached"])

        st = water.add_intake(1500, "garrafa grande")
        self.assertEqual(st["total_ml"], 2000)
        self.assertEqual(st["percentage"], 100)
        self.assertTrue(st["goal_reached"])

    def test_parse_water_commands(self):
        # Ingestão explícita
        cmd1 = water.parse_water_command("bebi 300ml de água")
        self.assertEqual(cmd1, ("add", 300))

        cmd2 = water.parse_water_command("tomei um copo de água")
        self.assertEqual(cmd2, ("add", 250))

        cmd3 = water.parse_water_command("bebi uma garrafinha de água")
        self.assertEqual(cmd3, ("add", 500))

        cmd4 = water.parse_water_command("tomei 1 litro de água")
        self.assertEqual(cmd4, ("add", 1000))

        # Consulta
        cmd5 = water.parse_water_command("quanto de água já bebi hoje?")
        self.assertEqual(cmd5, ("query", 0))

        # Ajuste de meta
        cmd6 = water.parse_water_command("mudar meta de água para 2500ml")
        self.assertEqual(cmd6, ("set_goal", 2500))


if __name__ == "__main__":
    unittest.main()
