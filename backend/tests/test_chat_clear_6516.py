"""V6.5.16: apagar a conversa (só hoje ou todo o período) sem apagar o que o JARVIS sabe."""
from datetime import datetime, timedelta

from modules import memory


def test_clear_today_keeps_older_and_facts():
    data = memory._load()  # noqa: SLF001
    old = (datetime.now() - timedelta(days=2)).isoformat(timespec="seconds")
    data["conversation"] = [{"user": "antiga", "assistant": "ok", "at": old}]
    data["facts"] = [{"text": "gosto de café", "created_at": old}]
    memory._save(data)  # noqa: SLF001
    memory.add_conversation("de hoje", "ok")
    assert memory.clear_conversation("today") == 1
    left = memory.get_memory()
    assert [c["user"] for c in left["conversation"]] == ["antiga"]
    assert left["facts"][0]["text"] == "gosto de café"


def test_clear_all():
    memory.add_conversation("a", "b")
    memory.clear_conversation("all")
    assert memory.get_memory()["conversation"] == []
