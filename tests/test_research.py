from __future__ import annotations


def test_research_proposal_workflow_does_not_overwrite_card(client, app):
    database = app.extensions["database"]
    card = database.list_cards()[0]
    original_meaning = card["meaning"]
    research = database.create_research(card["id"], "Check Japanese dictionaries")
    database.add_research_source(
        research["id"], "Dictionary", "https://example.test/entry", "覆う: cover"
    )
    database.update_research(
        research["id"],
        status="proposal",
        summary="Several senses were found.",
        suggested_meaning="cubrir; envolver",
        suggested_example="雲が空を覆う。",
        notes="Transitive verb.",
    )

    response = client.get(f"/api/cards/{card['id']}/research")
    proposal = response.get_json()
    assert proposal["status"] == "proposal"
    assert proposal["sources"][0]["page_title"] == "Dictionary"
    assert database.get_card(card["id"])["meaning"] == original_meaning

    accepted = client.post(
        f"/api/research/{research['id']}/decision", json={"decision": "accepted"}
    )
    assert accepted.get_json()["status"] == "accepted"
    assert database.get_card(card["id"])["meaning"] == original_meaning

