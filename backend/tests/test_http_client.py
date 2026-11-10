"""Cliente HTTP único e cotações unificadas (refatoração 4.2), sem acesso à rede."""
import pytest

from services import http_client, quotes


class _FakeResponse:
    def __init__(self, payload, status=200, content=b""):
        self._payload = payload
        self.status_code = status
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise http_client.requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, timeout))
        return self.responses.pop(0)


@pytest.fixture
def fake_session(monkeypatch):
    http_client.clear_cache()

    def install(*responses):
        fake = _FakeSession(responses)
        monkeypatch.setattr(http_client, "session", lambda: fake)
        return fake

    yield install
    http_client.clear_cache()


def test_cache_reuses_result_within_ttl(fake_session):
    fake = fake_session(_FakeResponse({"v": 1}), _FakeResponse({"v": 2}))
    assert http_client.get_json("https://x/api", params={"a": 1}, ttl=60) == {"v": 1}
    assert http_client.get_json("https://x/api", params={"a": 1}, ttl=60) == {"v": 1}
    assert len(fake.calls) == 1


def test_without_ttl_always_fetches(fake_session):
    fake = fake_session(_FakeResponse({"v": 1}), _FakeResponse({"v": 2}))
    assert http_client.get_json("https://x/api")["v"] == 1
    assert http_client.get_json("https://x/api")["v"] == 2
    assert len(fake.calls) == 2


def test_different_params_are_different_entries(fake_session):
    fake = fake_session(_FakeResponse({"v": "sp"}), _FakeResponse({"v": "rj"}))
    assert http_client.get_json("https://x/geo", params={"name": "sp"}, ttl=60)["v"] == "sp"
    assert http_client.get_json("https://x/geo", params={"name": "rj"}, ttl=60)["v"] == "rj"
    assert len(fake.calls) == 2


def test_errors_are_not_cached(fake_session):
    fake = fake_session(_FakeResponse({}, status=503), _FakeResponse({"ok": True}))
    with pytest.raises(http_client.requests.HTTPError):
        http_client.get_json("https://x/api", ttl=60)
    assert http_client.get_json("https://x/api", ttl=60) == {"ok": True}
    assert len(fake.calls) == 2


def test_default_timeout_is_always_sent(fake_session):
    fake = fake_session(_FakeResponse(None, content=b"<rss/>"))
    assert http_client.get_bytes("https://x/rss") == b"<rss/>"
    assert fake.calls[0][2] == http_client.DEFAULT_TIMEOUT


def test_session_retries_only_idempotent_gets():
    retry = http_client._build_session().get_adapter("https://example.com").max_retries
    assert retry.allowed_methods == frozenset({"GET"})
    assert set(retry.status_forcelist) == {502, 503, 504}


_RAW = {
    "USDBRL": {"code": "USD", "name": "Dólar", "bid": "5.40", "pctChange": "0.1", "high": "5.5", "low": "5.3"},
    "EURBRL": {"code": "EUR", "name": "Euro", "bid": "5.90", "pctChange": "-0.2", "high": "6.0", "low": "5.8"},
    "BTCBRL": {"code": "BTC", "name": "Bitcoin", "bid": "370000", "pctChange": "1.0", "high": "1", "low": "1"},
}


def test_quotes_share_one_request(fake_session):
    fake = fake_session(_FakeResponse(_RAW))
    assert quotes.get_rate("USDBRL") == 5.40
    assert quotes.get_rate("EURBRL") == 5.90  # mesma consulta, vinda do cache
    rates = quotes.summarize(quotes.fetch_rates())
    assert [r["pair"] for r in rates] == ["USDBRL", "EURBRL", "BTCBRL"]
    assert rates[2]["bid"] == 370000.0
    assert len(fake.calls) == 1
