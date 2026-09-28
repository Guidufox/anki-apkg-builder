from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlparse

from .provider import AIProvider


class LocalAIError(RuntimeError):
    pass


def validate_local_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise LocalAIError("La URL del modelo local no es válida")
    hostname = parsed.hostname.lower()
    is_loopback = hostname == "localhost"
    if not is_loopback:
        try:
            is_loopback = ip_address(hostname).is_loopback
        except ValueError:
            is_loopback = False
    if not is_loopback:
        raise LocalAIError(
            "Por privacidad, el proveedor Local AI solo acepta endpoints localhost/loopback"
        )
    return base_url.rstrip("/")


@dataclass
class LocalAIProvider(AIProvider):
    base_url: str
    model: str
    api_format: str = "openai"
    context_length: int = 8192
    timeout: int = 120

    def __post_init__(self) -> None:
        self.base_url = validate_local_url(self.base_url)
        if self.api_format not in {"openai", "ollama"}:
            raise LocalAIError("API format debe ser 'openai' u 'ollama'")
        if not self.model.strip():
            raise LocalAIError("Model name no puede estar vacío")

    @classmethod
    def from_settings(cls, settings: dict) -> "LocalAIProvider":
        return cls(
            base_url=settings["ai_base_url"],
            model=settings["ai_model"],
            api_format=settings["ai_api_format"],
            context_length=int(settings["ai_context_length"]),
            timeout=int(settings["ai_timeout"]),
        )

    def _request(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise LocalAIError(f"No se pudo contactar con Local AI: {exc}") from exc

    def chat(self, messages: list[dict], temperature: float = 0.1) -> str:
        if self.api_format == "openai":
            data = self._request(
                "/chat/completions",
                {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                },
            )
            try:
                return str(data["choices"][0]["message"]["content"])
            except (KeyError, IndexError, TypeError) as exc:
                raise LocalAIError("Respuesta OpenAI-compatible inválida") from exc

        data = self._request(
            "/api/chat",
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"num_ctx": self.context_length, "temperature": temperature},
            },
        )
        try:
            return str(data["message"]["content"])
        except (KeyError, TypeError) as exc:
            raise LocalAIError("Respuesta Ollama inválida") from exc

    def health(self) -> dict:
        path = "/models" if self.api_format == "openai" else "/api/tags"
        request = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=min(self.timeout, 5)) as response:
                return {"available": True, "status": response.status, "provider": "LOCAL"}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"available": False, "error": str(exc), "provider": "LOCAL"}
