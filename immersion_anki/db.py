from __future__ import annotations

import json
import sqlite3
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


DEMO_CARDS = [
    {
        "japanese": "覆う",
        "reading": "おおう",
        "meaning": "cubrir",
        "example": "霧が町を覆っている。",
        "translation": "La niebla cubre el pueblo.",
        "context": "Silent Hill f",
        "tags": "silent-hill-f verb vocabulary",
        "cloze": "霧が町を＿＿＿＿いる。",
        "cloze_answer": "覆って",
    },
    {
        "japanese": "近づく",
        "reading": "ちかづく",
        "meaning": "acercarse",
        "example": "あれに近づいちゃだめ。",
        "translation": "No te acerques a eso.",
        "context": "Demo",
        "tags": "verb vocabulary",
        "cloze": "あれに＿＿＿＿ちゃだめ。",
        "cloze_answer": "近づい",
    },
    {
        "japanese": "隠す",
        "reading": "かくす",
        "meaning": "esconder",
        "example": "鍵を箱の中に隠した。",
        "translation": "Escondí la llave dentro de la caja.",
        "context": "Demo",
        "tags": "verb vocabulary",
        "cloze": "鍵を箱の中に＿＿＿＿。",
        "cloze_answer": "隠した",
    },
    {
        "japanese": "徐々に",
        "reading": "じょじょに",
        "meaning": "gradualmente",
        "example": "徐々に回復している。",
        "translation": "Se está recuperando gradualmente.",
        "context": "Demo",
        "tags": "adverb vocabulary",
        "cloze": "＿＿＿＿回復している。",
        "cloze_answer": "徐々に",
    },
    {
        "japanese": "希望",
        "reading": "きぼう",
        "meaning": "esperanza",
        "example": "まだ希望がある。",
        "translation": "Todavía hay esperanza.",
        "context": "Demo",
        "tags": "noun vocabulary",
        "cloze": "まだ＿＿＿＿がある。",
        "cloze_answer": "希望",
    },
]

CARD_FIELDS = (
    "japanese",
    "reading",
    "meaning",
    "example",
    "translation",
    "context",
    "tags",
    "cloze",
    "cloze_answer",
)

DEFAULT_SETTINGS = {
    "ai_provider": "LOCAL",
    "ai_enabled": False,
    "ai_base_url": "http://127.0.0.1:8080/v1",
    "ai_model": "bonsai",
    "ai_api_format": "openai",
    "ai_context_length": 8192,
    "ai_timeout": 120,
    "network_enabled": False,
    "web_access": False,
    "browser_enabled": False,
    "browser_headless": False,
    "browser_profile": "data/browser-profile",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def card_identity(values: dict) -> tuple[str, str]:
    def normalize(value: object) -> str:
        text = unicodedata.normalize("NFKC", str(value or ""))
        return " ".join(text.split()).casefold()

    return normalize(values.get("japanese")), normalize(values.get("reading"))


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS decks (
                    id INTEGER PRIMARY KEY,
                    stable_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stable_id TEXT NOT NULL UNIQUE,
                    deck_id INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    japanese TEXT NOT NULL DEFAULT '',
                    reading TEXT NOT NULL DEFAULT '',
                    meaning TEXT NOT NULL DEFAULT '',
                    example TEXT NOT NULL DEFAULT '',
                    translation TEXT NOT NULL DEFAULT '',
                    context TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '',
                    cloze TEXT NOT NULL DEFAULT '',
                    cloze_answer TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS cards_deck_position
                    ON cards(deck_id, position);
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS research (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    task TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    suggested_meaning TEXT NOT NULL DEFAULT '',
                    suggested_example TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS research_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    research_id INTEGER NOT NULL REFERENCES research(id) ON DELETE CASCADE,
                    page_title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    accessed_at TEXT NOT NULL,
                    fragment TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    task TEXT NOT NULL,
                    url TEXT NOT NULL DEFAULT '',
                    action TEXT NOT NULL,
                    result TEXT NOT NULL DEFAULT ''
                );
                """
            )
            for key, value in DEFAULT_SETTINGS.items():
                connection.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, json.dumps(value, ensure_ascii=False)),
                )
            count = connection.execute("SELECT COUNT(*) FROM decks").fetchone()[0]
            if count == 0:
                now = utc_now()
                connection.execute(
                    "INSERT INTO decks (id, stable_id, name, created_at, updated_at) "
                    "VALUES (1, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), "Japanese Immersion — Demo", now, now),
                )
                for position, card in enumerate(DEMO_CARDS):
                    self._insert_card(connection, 1, card, position)

    def get_deck(self) -> dict:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM decks ORDER BY id LIMIT 1").fetchone()
            return dict(row)

    def update_deck(self, name: str) -> dict:
        name = name.strip()
        if not name:
            raise ValueError("Deck name no puede estar vacío")
        with self.connect() as connection:
            connection.execute(
                "UPDATE decks SET name = ?, updated_at = ? WHERE id = 1",
                (name, utc_now()),
            )
        return self.get_deck()

    def list_cards(self, search: str = "", tag: str = "") -> list[dict]:
        clauses = ["deck_id = 1"]
        params: list[str] = []
        if search:
            clauses.append(
                "(japanese LIKE ? OR reading LIKE ? OR meaning LIKE ? OR "
                "example LIKE ? OR translation LIKE ? OR context LIKE ? OR tags LIKE ?)"
            )
            token = f"%{search}%"
            params.extend([token] * 7)
        if tag:
            clauses.append("(' ' || tags || ' ') LIKE ?")
            params.append(f"% {tag} %")
        query = "SELECT * FROM cards WHERE " + " AND ".join(clauses) + " ORDER BY position, id"
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]

    def get_card(self, card_id: int) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM cards WHERE id = ? AND deck_id = 1", (card_id,)
            ).fetchone()
            return dict(row) if row else None

    def create_card(self, values: dict) -> dict:
        with self.connect() as connection:
            position = connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM cards WHERE deck_id = 1"
            ).fetchone()[0]
            card_id = self._insert_card(connection, 1, values, position)
        return self.get_card(card_id)

    def _insert_card(
        self,
        connection: sqlite3.Connection,
        deck_id: int,
        values: dict,
        position: int,
        stable_id: str | None = None,
    ) -> int:
        now = utc_now()
        clean = {field: str(values.get(field, "") or "").strip() for field in CARD_FIELDS}
        cursor = connection.execute(
            """
            INSERT INTO cards (
                stable_id, deck_id, position, japanese, reading, meaning,
                example, translation, context, tags, cloze, cloze_answer,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stable_id or str(uuid.uuid4()),
                deck_id,
                position,
                *(clean[field] for field in CARD_FIELDS),
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

    def update_card(self, card_id: int, values: dict) -> dict | None:
        existing = self.get_card(card_id)
        if not existing:
            return None
        clean = {
            field: str(values.get(field, existing[field]) or "").strip()
            for field in CARD_FIELDS
        }
        with self.connect() as connection:
            assignments = ", ".join(f"{field} = ?" for field in CARD_FIELDS)
            connection.execute(
                f"UPDATE cards SET {assignments}, updated_at = ? WHERE id = ? AND deck_id = 1",
                (*(clean[field] for field in CARD_FIELDS), utc_now(), card_id),
            )
        return self.get_card(card_id)

    def delete_card(self, card_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM cards WHERE id = ? AND deck_id = 1", (card_id,)
            )
            if cursor.rowcount:
                self._normalize_positions(connection)
            return bool(cursor.rowcount)

    def duplicate_card(self, card_id: int) -> dict | None:
        source = self.get_card(card_id)
        if not source:
            return None
        with self.connect() as connection:
            connection.execute(
                "UPDATE cards SET position = position + 1 "
                "WHERE deck_id = 1 AND position > ?",
                (source["position"],),
            )
            new_id = self._insert_card(
                connection, 1, source, source["position"] + 1
            )
        return self.get_card(new_id)

    def reorder_cards(self, card_ids: list[int]) -> None:
        current = {card["id"] for card in self.list_cards()}
        if set(card_ids) != current or len(card_ids) != len(current):
            raise ValueError("La lista de orden debe contener todas las tarjetas una sola vez")
        with self.connect() as connection:
            for position, card_id in enumerate(card_ids):
                connection.execute(
                    "UPDATE cards SET position = ?, updated_at = ? WHERE id = ?",
                    (position, utc_now(), card_id),
                )

    def all_tags(self) -> list[str]:
        tags = set()
        for card in self.list_cards():
            tags.update(tag for tag in card["tags"].split() if tag)
        return sorted(tags, key=str.casefold)

    def import_cards(self, rows: list[dict], skip_duplicates: bool = True) -> dict:
        created = []
        skipped = []
        known = {card_identity(card) for card in self.list_cards()}
        for row in rows:
            identity = card_identity(row)
            if skip_duplicates and identity in known:
                skipped.append(row)
                continue
            created.append(self.create_card(row))
            known.add(identity)
        return {"cards": created, "skipped": skipped}

    def export_project(self) -> dict:
        deck = self.get_deck()
        cards = self.list_cards()
        return {
            "format": "anki-apkg-builder-project",
            "version": 1,
            "exported_at": utc_now(),
            "deck": {
                "stable_id": deck["stable_id"],
                "name": deck["name"],
            },
            "cards": [
                {"stable_id": card["stable_id"], **{f: card[f] for f in CARD_FIELDS}}
                for card in cards
            ],
        }

    def get_settings(self) -> dict:
        with self.connect() as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
        values = DEFAULT_SETTINGS.copy()
        values.update({row["key"]: json.loads(row["value"]) for row in rows})
        return values

    def update_settings(self, values: dict) -> dict:
        allowed = set(DEFAULT_SETTINGS) - {"ai_provider"}
        with self.connect() as connection:
            for key, value in values.items():
                if key not in allowed:
                    continue
                if key in {
                    "ai_enabled",
                    "network_enabled",
                    "web_access",
                    "browser_enabled",
                    "browser_headless",
                }:
                    value = bool(value)
                elif key in {"ai_context_length", "ai_timeout"}:
                    value = int(value)
                    if value <= 0:
                        raise ValueError(f"{key} debe ser mayor que cero")
                else:
                    value = str(value).strip()
                connection.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, json.dumps(value, ensure_ascii=False)),
                )
        return self.get_settings()

    def disable_all_network(self) -> dict:
        return self.update_settings(
            {
                "network_enabled": False,
                "web_access": False,
                "browser_enabled": False,
            }
        )

    def create_research(self, card_id: int, task: str) -> dict:
        if not self.get_card(card_id):
            raise ValueError("Tarjeta no encontrada")
        now = utc_now()
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO research (card_id, status, task, created_at, updated_at) "
                "VALUES (?, 'running', ?, ?, ?)",
                (card_id, task, now, now),
            )
            research_id = int(cursor.lastrowid)
        return self.get_research(research_id)

    def update_research(self, research_id: int, **values) -> dict | None:
        allowed = {
            "status",
            "summary",
            "suggested_meaning",
            "suggested_example",
            "notes",
        }
        clean = {key: str(value) for key, value in values.items() if key in allowed}
        if not clean:
            return self.get_research(research_id)
        clean["updated_at"] = utc_now()
        with self.connect() as connection:
            assignments = ", ".join(f"{key} = ?" for key in clean)
            connection.execute(
                f"UPDATE research SET {assignments} WHERE id = ?",
                (*clean.values(), research_id),
            )
        return self.get_research(research_id)

    def get_research(self, research_id: int) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM research WHERE id = ?", (research_id,)
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            result["sources"] = [
                dict(source)
                for source in connection.execute(
                    "SELECT page_title, url, accessed_at, fragment "
                    "FROM research_sources WHERE research_id = ? ORDER BY id",
                    (research_id,),
                ).fetchall()
            ]
            return result

    def latest_research_for_card(self, card_id: int) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id FROM research WHERE card_id = ? ORDER BY id DESC LIMIT 1",
                (card_id,),
            ).fetchone()
        return self.get_research(row["id"]) if row else None

    def add_research_source(
        self, research_id: int, page_title: str, url: str, fragment: str
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO research_sources "
                "(research_id, page_title, url, accessed_at, fragment) VALUES (?, ?, ?, ?, ?)",
                (research_id, page_title[:500], url[:2000], utc_now(), fragment[:4000]),
            )

    def log_agent_action(
        self, task: str, url: str, action: str, result: str
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO agent_logs (timestamp, task, url, action, result) "
                "VALUES (?, ?, ?, ?, ?)",
                (utc_now(), task[:1000], url[:2000], action[:100], result[:4000]),
            )

    def list_agent_logs(self, limit: int = 200) -> list[dict]:
        with self.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM agent_logs ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            ]

    def restore_project(self, payload: dict) -> None:
        if payload.get("format") != "anki-apkg-builder-project" or payload.get("version") != 1:
            raise ValueError("Formato de backup no compatible")
        deck = payload.get("deck")
        cards = payload.get("cards")
        if not isinstance(deck, dict) or not str(deck.get("name", "")).strip():
            raise ValueError("El backup no contiene un mazo válido")
        if not isinstance(cards, list):
            raise ValueError("El backup no contiene una lista de tarjetas")
        with self.connect() as connection:
            connection.execute("DELETE FROM cards WHERE deck_id = 1")
            connection.execute(
                "UPDATE decks SET stable_id = ?, name = ?, updated_at = ? WHERE id = 1",
                (
                    str(deck.get("stable_id") or uuid.uuid4()),
                    str(deck["name"]).strip(),
                    utc_now(),
                ),
            )
            for position, card in enumerate(cards):
                if not isinstance(card, dict):
                    raise ValueError("Tarjeta inválida en el backup")
                self._insert_card(
                    connection,
                    1,
                    card,
                    position,
                    str(card.get("stable_id") or uuid.uuid4()),
                )

    @staticmethod
    def _normalize_positions(connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            "SELECT id FROM cards WHERE deck_id = 1 ORDER BY position, id"
        ).fetchall()
        for position, row in enumerate(rows):
            connection.execute(
                "UPDATE cards SET position = ? WHERE id = ?", (position, row["id"])
            )
