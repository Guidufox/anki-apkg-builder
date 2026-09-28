from __future__ import annotations

import sqlite3
import zipfile

from immersion_anki.exporter import deterministic_id, safe_filename


def test_apkg_is_valid_and_contains_expected_notes(client, app, tmp_path):
    response = client.post("/api/export")
    assert response.status_code == 200
    destination = next((tmp_path / "exports").glob("*.apkg"))
    assert destination.name == safe_filename("Japanese Immersion — Demo")

    with zipfile.ZipFile(destination) as archive:
        names = archive.namelist()
        collection_name = next(name for name in names if name.startswith("collection.anki2"))
        archive.extract(collection_name, tmp_path / "unpacked")

    connection = sqlite3.connect(tmp_path / "unpacked" / collection_name)
    try:
        notes = connection.execute("SELECT flds, tags, guid FROM notes ORDER BY id").fetchall()
        cards = connection.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    finally:
        connection.close()
    assert len(notes) == 5
    assert cards == 10
    assert any("覆う" in fields and "霧が町を覆っている。" in fields for fields, _, _ in notes)
    assert all("<script" not in fields for fields, _, _ in notes)


def test_ids_and_filenames_are_deterministic():
    assert deterministic_id("deck-v1", "demo") == deterministic_id("deck-v1", "demo")
    assert deterministic_id("deck-v1", "demo") != deterministic_id("deck-v1", "other")
    assert safe_filename("Silent Hill f — Japanese Immersion") == "Silent-Hill-f-Japanese-Immersion.apkg"


def test_export_escapes_user_html(client, tmp_path):
    card = client.post("/api/cards", json={"japanese": "<script>alert(1)</script>", "meaning": "x"}).get_json()
    client.post("/api/export")
    destination = next((tmp_path / "exports").glob("*.apkg"))
    with zipfile.ZipFile(destination) as archive:
        collection_name = next(name for name in archive.namelist() if name.startswith("collection.anki2"))
        archive.extract(collection_name, tmp_path / "escaped")
    connection = sqlite3.connect(tmp_path / "escaped" / collection_name)
    fields = connection.execute("SELECT flds FROM notes WHERE guid = (SELECT guid FROM notes ORDER BY id DESC LIMIT 1)").fetchone()[0]
    connection.close()
    assert "&lt;script&gt;" in fields
    assert "<script>" not in fields

