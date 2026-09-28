from __future__ import annotations

import pytest

from immersion_anki.browser.actions import ALLOWED_ACTIONS, BrowserActionError, BrowserTools
from immersion_anki.browser.safety import sensitive_reason
from immersion_anki.browser.playwright_client import PlaywrightBrowser


class FakeBrowser:
    def read(self, **kwargs):
        return {"visible_text": "safe", **kwargs}


def test_browser_action_allowlist():
    tools = BrowserTools(FakeBrowser())
    assert tools.execute("read")["visible_text"] == "safe"
    assert "shell" not in ALLOWED_ACTIONS
    with pytest.raises(BrowserActionError):
        tools.execute("shell", {"command": "id"})


def test_sensitive_action_requires_confirmation():
    assert sensitive_reason("click", {"selector": "button.buy-now"})
    assert sensitive_reason("type", {"selector": "input[type=password]", "text": "secret"})
    assert sensitive_reason("navigate", {"url": "https://jisho.org"}) is None
    assert sensitive_reason("read", {}) is None
    assert sensitive_reason("navigate", {"url": "https://example.test/tool.exe"})
    assert sensitive_reason(
        "type", {"selector": "form textarea", "text": "hello", "press_enter": True}
    )


def test_browser_rejects_non_web_urls():
    with pytest.raises(ValueError, match="http/https"):
        PlaywrightBrowser._validate_web_url("file:///etc/passwd")
    PlaywrightBrowser._validate_web_url("https://example.test")


def test_browser_disabled_mode(client):
    card_id = client.get("/api/cards").get_json()[0]["id"]
    client.put("/api/settings", json={"ai_enabled": True, "network_enabled": True, "web_access": True, "browser_enabled": False})
    response = client.post(f"/api/cards/{card_id}/research", json={})
    assert response.status_code == 400
    assert "desactivado" in response.get_json()["error"]


def test_network_disabled_mode(client):
    card_id = client.get("/api/cards").get_json()[0]["id"]
    client.put("/api/settings", json={"ai_enabled": True, "network_enabled": False, "web_access": True, "browser_enabled": True})
    response = client.post(f"/api/cards/{card_id}/research", json={})
    assert response.status_code == 400
    assert "web" in response.get_json()["error"].lower()
    project = client.get("/api/project")
    assert project.status_code == 200
    assert client.post("/api/export").status_code == 200


def test_disable_all_network(client):
    client.put("/api/settings", json={"network_enabled": True, "web_access": True, "browser_enabled": True})
    settings = client.post("/api/settings/disable-network").get_json()
    assert settings["network_enabled"] is False
    assert settings["web_access"] is False
    assert settings["browser_enabled"] is False
