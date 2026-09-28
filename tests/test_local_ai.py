from __future__ import annotations

import json
import urllib.error

import pytest

from immersion_anki.ai.local_provider import LocalAIError, LocalAIProvider


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_openai_compatible_local_provider(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        return FakeResponse({"choices": [{"message": {"content": '{"action":"finish","arguments":{}}'}}]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = LocalAIProvider("http://127.0.0.1:8080/v1", "bonsai")
    answer = provider.chat([{"role": "user", "content": "test"}])
    assert '"finish"' in answer
    assert captured["url"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert captured["payload"]["model"] == "bonsai"


def test_cloud_endpoint_is_never_accepted():
    with pytest.raises(LocalAIError, match="localhost"):
        LocalAIProvider("https://api.openai.com/v1", "anything")


def test_unavailable_local_ai_fails_cleanly(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    provider = LocalAIProvider("http://localhost:9999/v1", "bonsai", timeout=1)
    with pytest.raises(LocalAIError, match="Local AI"):
        provider.chat([{"role": "user", "content": "test"}])
    assert provider.health()["available"] is False

