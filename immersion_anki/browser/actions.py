from __future__ import annotations


ALLOWED_ACTIONS = frozenset(
    {
        "navigate",
        "search",
        "click",
        "type",
        "scroll",
        "read",
        "screenshot",
        "back",
        "new_tab",
        "close_tab",
        "wait",
    }
)


class BrowserActionError(RuntimeError):
    pass


class BrowserTools:
    def __init__(self, client):
        self.client = client

    def execute(self, action: str, arguments: dict | None = None):
        if action not in ALLOWED_ACTIONS:
            raise BrowserActionError(f"Acción de navegador no permitida: {action}")
        method = getattr(self.client, action)
        return method(**(arguments or {}))

