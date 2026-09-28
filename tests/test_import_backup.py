from __future__ import annotations


TSV = "覆う\tおおう\tcubrir\t霧が町を覆っている。\tLa niebla cubre el pueblo.\tSilent Hill f\tverb vocabulary"
CSV = 'Japanese,Reading,Meaning,Example,Translation,Context,Tags\n猫,ねこ,gato,猫がいる。,"Hay un gato.",Demo,"noun vocabulary"'


def test_tsv_preview_and_import(client):
    preview = client.post("/api/import/preview", json={"text": TSV, "format": "tsv"})
    assert preview.status_code == 200
    assert preview.get_json()["rows"][0]["reading"] == "おおう"
    assert preview.get_json()["rows"][0]["_duplicate"] is True
    result = client.post("/api/import/commit", json={"text": TSV, "format": "tsv"})
    assert result.status_code == 200
    assert result.get_json()["cards"] == []
    assert len(result.get_json()["skipped"]) == 1


def test_duplicate_can_be_explicitly_allowed(client):
    result = client.post(
        "/api/import/commit",
        json={"text": TSV, "format": "tsv", "allow_duplicates": True},
    )
    assert result.status_code == 201
    assert result.get_json()["cards"][0]["meaning"] == "cubrir"


def test_duplicate_inside_same_import_is_skipped(client):
    text = "\n".join(
        [
            "新語\tしんご\tpalabra nueva\t新語を覚える。\tAprendo una palabra nueva.\tDemo\tnoun",
            "新語\tしんご\totro significado\t新語だ。\tEs una palabra nueva.\tDemo\tnoun",
        ]
    )
    preview = client.post("/api/import/preview", json={"text": text, "format": "tsv"}).get_json()
    assert [row["_duplicate"] for row in preview["rows"]] == [False, True]
    result = client.post("/api/import/commit", json={"text": text, "format": "tsv"}).get_json()
    assert len(result["cards"]) == 1
    assert len(result["skipped"]) == 1


def test_csv_header_preview_and_import(client):
    preview = client.post("/api/import/preview", json={"text": CSV, "format": "csv"})
    assert preview.status_code == 200
    rows = preview.get_json()["rows"]
    assert len(rows) == 1
    assert rows[0]["translation"] == "Hay un gato."
    assert client.post("/api/import/commit", json={"text": CSV, "format": "csv"}).status_code == 201


def test_json_backup_restore_replaces_project(client):
    backup = client.get("/api/backup")
    assert backup.status_code == 200
    payload = backup.get_json()
    original_ids = [card["stable_id"] for card in payload["cards"]]

    first_id = client.get("/api/cards").get_json()[0]["id"]
    client.delete(f"/api/cards/{first_id}")
    client.put("/api/deck", json={"name": "Changed"})

    restored = client.post("/api/backup", json=payload)
    assert restored.status_code == 200
    project = client.get("/api/project").get_json()
    assert project["deck"]["name"] == "Japanese Immersion — Demo"
    assert [card["stable_id"] for card in project["cards"]] == original_ids


def test_malformed_import_is_rejected(client):
    response = client.post("/api/import/preview", json={"text": "too,few,columns", "format": "csv"})
    assert response.status_code == 400
