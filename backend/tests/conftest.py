"""Fixtures compartilhadas: isolam os arquivos de data/ em uma pasta temporária."""
import pytest

# V4.4: arquivos que o JARVIS GRAVA em data/. Em todo teste eles apontam para uma pasta temporária,
# para nenhum teste mexer nas configurações e nos registros reais do usuário. (Antes, um teste do
# Modo Torcedor desligava o modo no data/jarvis_settings.json de verdade.)
_WRITABLE = (
    ("prefs", "_SETTINGS_PATH", "jarvis_settings.json"),
    ("sports_provider", "CACHE_FILE", "fan_cache.json"),
    ("fan_mode", "NEWS_CACHE_FILE", "fan_news_cache.json"),
    ("lock_log", "LOG_PATH", "lock_log.json"),
    ("lock_pin", "PIN_PATH", "lock_pin.json"),
    ("water", "DATA_FILE", "water_log.json"),
    ("reminders", "_REMINDERS_PATH", "lembretes.json"),
    ("tasks", "_TASKS_PATH", "tarefas.json"),
    ("routine", "DATA_PATH", "rotina.json"),
    ("deep_search_quota", "_QUOTA_FILE", "deep_search_usage.json"),
    ("health", "HEALTH_FILE", "health_telemetry.json"),
    ("event_log", "_PATH", "eventos.json"),
    ("memory", "_PATH", "memoria.json"),
    ("whatsapp", "CONTACTS_PATH", "contatos.json"),
    ("finances", "DATA_PATH", "financas.json"),
    ("files", "UNDO_PATH", "organizacao_ultima.json"),
)


@pytest.fixture(autouse=True)
def _protect_real_data(tmp_path_factory, monkeypatch):
    import importlib

    base = tmp_path_factory.mktemp("data")
    from modules import profiles

    monkeypatch.setattr(profiles, "REGISTRY_PATH", base / "perfis.json")
    monkeypatch.setattr(profiles, "PROFILES_DIR", base / "perfis")
    for module_name, attr, filename in _WRITABLE:
        module = importlib.import_module(f"modules.{module_name}")
        if hasattr(module, attr):
            monkeypatch.setattr(module, attr, base / filename)
    yield


@pytest.fixture
def isolated_data(tmp_path, monkeypatch):
    """Redireciona os arquivos persistentes usados pelas funções de bloqueio para tmp_path."""
    from modules import access, face, lock_log, lock_pin, prefs, water

    monkeypatch.setattr(lock_pin, "PIN_PATH", tmp_path / "lock_pin.json")
    monkeypatch.setattr(lock_log, "LOG_PATH", tmp_path / "lock_log.json")
    monkeypatch.setattr(lock_log, "INTRUDERS_DIR", tmp_path / "intruders")
    monkeypatch.setattr(prefs, "_SETTINGS_PATH", tmp_path / "jarvis_settings.json")
    monkeypatch.setattr(face, "PHOTO_PATH", tmp_path / "profile.jpg")
    monkeypatch.setattr(face, "META_PATH", tmp_path / "profile.json")
    monkeypatch.setattr(water, "DATA_FILE", tmp_path / "water_log.json")
    access.reset_for_tests(access.LOCKED)
    yield tmp_path
    access.reset_for_tests(access.LOCKED)
