from __future__ import annotations


def test_demo_deck_is_created(client):
    response = client.get("/api/project")
    assert response.status_code == 200
    project = response.get_json()
    assert project["deck"]["name"] == "Japanese Immersion — Demo"
    assert len(project["cards"]) == 5
    assert project["cards"][0]["japanese"] == "覆う"


def test_update_deck_and_card_crud(client):
    deck = client.put("/api/deck", json={"name": "Silent Hill f — Japanese Immersion"})
    assert deck.status_code == 200
    assert deck.get_json()["name"].startswith("Silent Hill")

    created = client.post(
        "/api/cards",
        json={
            "japanese": "霧",
            "reading": "きり",
            "meaning": "niebla",
            "example": "霧が深い。",
            "translation": "La niebla es densa.",
            "context": "game",
            "tags": "noun weather",
            "cloze": "＿＿が深い。",
            "cloze_answer": "霧",
        },
    )
    assert created.status_code == 201
    card_id = created.get_json()["id"]

    updated = client.put(f"/api/cards/{card_id}", json={"meaning": "bruma"})
    assert updated.get_json()["meaning"] == "bruma"

    duplicated = client.post(f"/api/cards/{card_id}/duplicate")
    assert duplicated.status_code == 201
    assert duplicated.get_json()["stable_id"] != created.get_json()["stable_id"]

    assert client.delete(f"/api/cards/{card_id}").status_code == 204
    assert client.put(f"/api/cards/{card_id}", json={"meaning": "x"}).status_code == 404


def test_reorder_requires_all_cards(client):
    cards = client.get("/api/cards").get_json()
    ids = [card["id"] for card in reversed(cards)]
    assert client.put("/api/cards/reorder", json={"ids": ids}).status_code == 200
    reordered = client.get("/api/cards").get_json()
    assert [card["id"] for card in reordered] == ids
    assert client.put("/api/cards/reorder", json={"ids": ids[:-1]}).status_code == 400

