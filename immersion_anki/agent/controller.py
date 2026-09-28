from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from ..ai import LocalAIProvider
from ..browser.actions import BrowserTools
from ..browser.playwright_client import PlaywrightBrowser
from ..browser.safety import sensitive_reason
from .tools import SYSTEM_PROMPT


def parse_model_action(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    try:
        action = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Local AI no devolvió una acción JSON válida") from exc
    if not isinstance(action, dict) or not isinstance(action.get("action"), str):
        raise ValueError("La acción de Local AI no tiene el formato esperado")
    if not isinstance(action.get("arguments", {}), dict):
        raise ValueError("Los argumentos de la acción deben ser un objeto")
    return action


class AgentController:
    def __init__(self, database, project_root: str | Path):
        self.database = database
        self.project_root = Path(project_root).resolve()
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._thread: threading.Thread | None = None
        self._stop = False
        self._paused = False
        self._confirmation: bool | None = None
        self._state = self._empty_state()

    @staticmethod
    def _empty_state() -> dict:
        return {
            "status": "idle",
            "research_id": None,
            "current_url": "",
            "current_task": "",
            "last_action": "",
            "next_proposed_action": "",
            "confirmation_required": False,
            "confirmation_reason": "",
            "error": "",
        }

    def state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def start_research(self, card_id: int, task: str = "") -> dict:
        settings = self.database.get_settings()
        if not settings["ai_enabled"]:
            raise ValueError("Local AI está desactivada en Settings")
        if not settings["network_enabled"] or not settings["web_access"]:
            raise ValueError("El acceso web está desactivado")
        if not settings["browser_enabled"]:
            raise ValueError("Browser automation está desactivado")
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise ValueError("Ya hay una investigación en curso")
            card = self.database.get_card(card_id)
            if not card:
                raise ValueError("Tarjeta no encontrada")
            default_task = f"Investigar uso y matices de {card['japanese']} ({card['reading']})"
            research = self.database.create_research(card_id, task.strip() or default_task)
            self._stop = False
            self._paused = False
            self._confirmation = None
            self._state = self._empty_state()
            self._state.update(
                status="starting",
                research_id=research["id"],
                current_task=research["task"],
            )
            self._thread = threading.Thread(
                target=self._run,
                args=(research["id"], card, settings),
                daemon=True,
                name="local-research-agent",
            )
            self._thread.start()
            return dict(self._state)

    def pause(self) -> dict:
        with self._condition:
            if self._state["status"] in {"running", "starting"}:
                self._paused = True
                self._state["status"] = "paused"
            return dict(self._state)

    def resume(self) -> dict:
        with self._condition:
            if self._paused:
                self._paused = False
                self._state["status"] = "running"
                self._condition.notify_all()
            return dict(self._state)

    def stop(self) -> dict:
        with self._condition:
            if not self._thread or not self._thread.is_alive():
                return dict(self._state)
            self._stop = True
            self._paused = False
            self._confirmation = False
            self._state["status"] = "stopping"
            self._condition.notify_all()
            return dict(self._state)

    def confirm(self, allowed: bool) -> dict:
        with self._condition:
            if not self._state["confirmation_required"]:
                raise ValueError("No hay una acción pendiente de confirmación")
            self._confirmation = bool(allowed)
            self._state["confirmation_required"] = False
            self._state["confirmation_reason"] = ""
            self._state["status"] = "running"
            self._condition.notify_all()
            return dict(self._state)

    def _wait_if_paused(self) -> None:
        with self._condition:
            while self._paused and not self._stop:
                self._condition.wait(timeout=1)

    def _await_confirmation(self, reason: str) -> bool:
        with self._condition:
            self._confirmation = None
            self._state.update(
                status="awaiting_confirmation",
                confirmation_required=True,
                confirmation_reason=reason,
            )
            while self._confirmation is None and not self._stop:
                self._condition.wait(timeout=1)
            return bool(self._confirmation) and not self._stop

    def _profile_path(self, configured: str) -> Path:
        path = Path(configured).expanduser()
        return path.resolve() if path.is_absolute() else (self.project_root / path).resolve()

    def _run(self, research_id: int, card: dict, settings: dict) -> None:
        browser = None
        task = self._state["current_task"]
        try:
            provider = LocalAIProvider.from_settings(settings)
            browser = PlaywrightBrowser(
                self._profile_path(settings["browser_profile"]),
                headless=bool(settings["browser_headless"]),
                project_root=self.project_root,
            )
            browser.start()
            tools = BrowserTools(browser)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": task,
                            "card": {
                                key: card[key]
                                for key in (
                                    "japanese",
                                    "reading",
                                    "meaning",
                                    "example",
                                    "translation",
                                    "context",
                                )
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
            with self._lock:
                self._state["status"] = "running"

            for _step in range(30):
                self._wait_if_paused()
                if self._stop:
                    self.database.update_research(research_id, status="stopped")
                    break
                action_data = parse_model_action(provider.chat(messages))
                action = action_data["action"]
                arguments = action_data.get("arguments", {})
                with self._lock:
                    self._state["next_proposed_action"] = action_data.get(
                        "next_proposed_action", action
                    )
                    self._state["current_url"] = browser.current_url

                if action == "finish":
                    self.database.update_research(
                        research_id,
                        status="proposal",
                        summary=arguments.get("summary", ""),
                        suggested_meaning=arguments.get("suggested_meaning", ""),
                        suggested_example=arguments.get("suggested_example", ""),
                        notes=arguments.get("notes", ""),
                    )
                    self.database.log_agent_action(task, browser.current_url, "finish", "Propuesta creada")
                    with self._lock:
                        self._state.update(status="completed", last_action="finish")
                    break

                reason = sensitive_reason(action, arguments)
                if reason and not self._await_confirmation(reason):
                    result = {"blocked": True, "reason": "El usuario rechazó la acción sensible"}
                else:
                    safe_arguments = {
                        key: value
                        for key, value in arguments.items()
                        if key not in {"sensitive", "reason"}
                    }
                    result = tools.execute(action, safe_arguments)
                url = str(result.get("url", browser.current_url)) if isinstance(result, dict) else browser.current_url
                log_result = json.dumps(result, ensure_ascii=False)[:4000]
                if action == "type":
                    log_result = "Texto introducido (contenido omitido por privacidad)"
                self.database.log_agent_action(task, url, action, log_result)
                if action == "read" and isinstance(result, dict):
                    self.database.add_research_source(
                        research_id,
                        str(result.get("title", "")),
                        url,
                        str(result.get("visible_text", ""))[:4000],
                    )
                with self._lock:
                    self._state.update(
                        current_url=url,
                        last_action=action,
                        next_proposed_action="Esperando decisión del modelo local",
                    )
                messages.extend(
                    [
                        {"role": "assistant", "content": json.dumps(action_data, ensure_ascii=False)},
                        {"role": "user", "content": "Observación:\n" + json.dumps(result, ensure_ascii=False)[:16000]},
                    ]
                )
            else:
                raise RuntimeError("El agente alcanzó el límite de 30 acciones")
        except Exception as exc:
            self.database.update_research(research_id, status="failed", notes=str(exc))
            self.database.log_agent_action(task, "", "error", str(exc))
            with self._lock:
                self._state.update(status="failed", error=str(exc))
        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
