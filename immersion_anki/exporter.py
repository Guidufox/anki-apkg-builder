from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from pathlib import Path

import genanki


MODEL_ID = 1709324501


def deterministic_id(namespace: str, value: str) -> int:
    digest = hashlib.sha256(f"{namespace}:{value}".encode("utf-8")).digest()
    return 1_000_000_000 + int.from_bytes(digest[:4], "big") % 1_000_000_000


def safe_filename(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", name).strip()
    cleaned = re.sub(r"[^\w\-.]+", "-", normalized, flags=re.UNICODE).strip("-._")
    return (cleaned or "anki-deck")[:100] + ".apkg"


def build_model() -> genanki.Model:
    return genanki.Model(
        MODEL_ID,
        "Japanese Immersion (Recognition + Recall) v1",
        fields=[
            {"name": "Expression"},
            {"name": "Reading"},
            {"name": "Meaning"},
            {"name": "Example"},
            {"name": "Translation"},
            {"name": "Context"},
            {"name": "ClozePrompt"},
            {"name": "ClozeAnswer"},
        ],
        templates=[
            {
                "name": "Recognition",
                "qfmt": (
                    '<div class="example jp">{{Example}}</div>'
                    '<div class="expression jp">{{Expression}}'
                    '<span class="reading">【{{Reading}}】</span></div>'
                ),
                "afmt": (
                    '{{FrontSide}}<hr id="answer">'
                    '<div class="answer-expression jp">{{Expression}}</div>'
                    '<div class="answer-reading jp">{{Reading}}</div>'
                    '<div class="meaning">{{Meaning}}</div>'
                    '<div class="example jp">{{Example}}</div>'
                    '<div class="translation">{{Translation}}</div>'
                    '{{#Context}}<div class="context">{{Context}}</div>{{/Context}}'
                ),
            },
            {
                "name": "Recall",
                "qfmt": (
                    '<div class="meaning">{{Meaning}}</div>'
                    '<div class="example jp">{{ClozePrompt}}</div>'
                ),
                "afmt": (
                    '{{FrontSide}}<hr id="answer">'
                    '<div class="cloze-answer jp">{{ClozeAnswer}}</div>'
                    '<div class="expression jp">{{Expression}}'
                    '<span class="reading">【{{Reading}}】</span></div>'
                    '<div class="example jp">{{Example}}</div>'
                    '{{#Translation}}<div class="translation">{{Translation}}</div>{{/Translation}}'
                    '{{#Context}}<div class="context">{{Context}}</div>{{/Context}}'
                ),
            },
        ],
        css="""
.card { font-family: -apple-system, BlinkMacSystemFont, "Noto Sans JP", "Yu Gothic",
  "Hiragino Kaku Gothic ProN", Meiryo, sans-serif; font-size: 20px;
  text-align: center; color: #e8e8e8; background: #191b20; padding: 24px; }
.jp { font-family: "Noto Sans JP", "Yu Gothic", Meiryo, sans-serif; }
.example { font-size: 26px; line-height: 1.6; margin: 14px 0; }
.expression, .answer-expression { font-size: 30px; margin: 14px 0 4px; }
.reading, .answer-reading { color: #aeb7c8; font-size: 20px; }
.meaning { color: #90d7b8; font-size: 28px; margin: 18px 0; }
.translation { color: #c8ccd4; margin: 10px 0; }
.cloze-answer { color: #f0c674; font-size: 34px; font-weight: 700; }
.context { color: #7f8796; font-size: 14px; margin-top: 24px; }
hr { border: 0; border-top: 1px solid #3a3d45; margin: 22px 0; }
""",
    )


def export_apkg(deck: dict, cards: list[dict], output_dir: str | Path) -> Path:
    if not cards:
        raise ValueError("El mazo no contiene tarjetas")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    deck_id = deterministic_id("deck-v1", deck["name"].strip().casefold())
    anki_deck = genanki.Deck(deck_id, deck["name"])
    model = build_model()

    for card in cards:
        fields = [
            html.escape(str(card.get(field, "")), quote=True)
            for field in (
                "japanese",
                "reading",
                "meaning",
                "example",
                "translation",
                "context",
                "cloze",
                "cloze_answer",
            )
        ]
        note = genanki.Note(
            model=model,
            fields=fields,
            tags=[tag for tag in str(card.get("tags", "")).split() if tag],
            guid=genanki.guid_for(deck["stable_id"], card["stable_id"]),
        )
        anki_deck.add_note(note)

    destination = output_dir / safe_filename(deck["name"])
    genanki.Package(anki_deck).write_to_file(str(destination))
    return destination
