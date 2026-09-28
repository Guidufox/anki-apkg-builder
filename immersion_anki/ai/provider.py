from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Small interface implemented only by local inference providers."""

    @abstractmethod
    def chat(self, messages: list[dict], temperature: float = 0.1) -> str:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> dict:
        raise NotImplementedError

