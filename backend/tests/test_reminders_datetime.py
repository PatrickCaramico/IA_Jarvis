from datetime import datetime
import sys
from pathlib import Path
import unittest

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from modules.reminders import _parse_datetime, add_reminder, postpone_reminder, clear_reminders


class TestRemindersDateTime(unittest.TestCase):
    def setUp(self):
        clear_reminders()

    def tearDown(self):
        clear_reminders()

    def test_parse_daily_recurrence(self):
        """Testa agendamento com recorrência diária: 'todo dia às 8h'."""
        alvo, clean, recorrencia, _dias = _parse_datetime("todo dia as 8h")
        self.assertIsNotNone(alvo)
        self.assertEqual(alvo.hour, 8)
        self.assertEqual(alvo.minute, 0)
        self.assertEqual(recorrencia, "diaria")

    def test_parse_relative_minutes(self):
        """Testa parsing relativo: 'daqui a 15 minutos'."""
        agora = datetime.now()
        alvo, clean, recorrencia, _dias = _parse_datetime("daqui a 15 minutos tomar agua")
        self.assertIsNotNone(alvo)
        self.assertAlmostEqual((alvo - agora).total_seconds(), 900, delta=70)  # V5.1: arredonda para o minuto seguinte
        self.assertIsNone(recorrencia)

    def test_postpone_reminder(self):
        """Testa adiar lembrete: 'adie 10 minutos'."""
        add_reminder("reunião de alinhamento", datetime.now())
        adiado = postpone_reminder(10)
        self.assertIsNotNone(adiado)
        self.assertEqual(adiado["texto"], "reunião de alinhamento")
        self.assertFalse(adiado["disparado"])


if __name__ == "__main__":
    unittest.main()
