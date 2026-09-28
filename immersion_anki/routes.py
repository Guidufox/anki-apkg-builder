from __future__ import annotations

import json

from flask import Blueprint, Response, current_app, jsonify, render_template, request, send_file

from .exporter import export_apkg
from .importers import parse_bulk
from .ai import LocalAIError, LocalAIProvider


bp = Blueprint("main", __name__)


def db():
    return current_app.extensions["database"]


def agent():
    return current_app.extensions["agent_controller"]


def error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/api/project")
def get_project():
    return jsonify(
        {"deck": db().get_deck(), "cards": db().list_cards(), "tags": db().all_tags()}
    )


@bp.put("/api/deck")
def update_deck():
    try:
        return jsonify(db().update_deck((request.get_json(silent=True) or {}).get("name", "")))
    except ValueError as exc:
        return error(str(exc))


@bp.get("/api/cards")
def list_cards():
    return jsonify(
        db().list_cards(request.args.get("search", "").strip(), request.args.get("tag", "").strip())
    )


@bp.post("/api/cards")
def create_card():
    return jsonify(db().create_card(request.get_json(silent=True) or {})), 201


@bp.put("/api/cards/<int:card_id>")
def update_card(card_id: int):
    card = db().update_card(card_id, request.get_json(silent=True) or {})
    return jsonify(card) if card else error("Tarjeta no encontrada", 404)


@bp.delete("/api/cards/<int:card_id>")
def delete_card(card_id: int):
    return (Response(status=204) if db().delete_card(card_id) else error("Tarjeta no encontrada", 404))


@bp.post("/api/cards/<int:card_id>/duplicate")
def duplicate_card(card_id: int):
    card = db().duplicate_card(card_id)
    return (jsonify(card), 201) if card else error("Tarjeta no encontrada", 404)


@bp.put("/api/cards/reorder")
def reorder_cards():
    try:
        card_ids = [int(value) for value in (request.get_json(silent=True) or {}).get("ids", [])]
        db().reorder_cards(card_ids)
        return jsonify({"ok": True})
    except (TypeError, ValueError) as exc:
        return error(str(exc))


@bp.post("/api/import/preview")
def preview_import():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"rows": parse_bulk(payload.get("text", ""), payload.get("format", "auto"))})
    except ValueError as exc:
        return error(str(exc))


@bp.post("/api/import/commit")
def commit_import():
    payload = request.get_json(silent=True) or {}
    try:
        rows = parse_bulk(payload.get("text", ""), payload.get("format", "auto"))
        if not rows:
            raise ValueError("No hay filas para importar")
        return jsonify({"cards": db().import_cards(rows)}), 201
    except ValueError as exc:
        return error(str(exc))


@bp.get("/api/backup")
def export_backup():
    content = json.dumps(db().export_project(), ensure_ascii=False, indent=2)
    return Response(
        content,
        mimetype="application/json",
        headers={"Content-Disposition": 'attachment; filename="anki-project.json"'},
    )


@bp.post("/api/backup")
def import_backup():
    payload = request.get_json(silent=True)
    if payload is None:
        return error("El archivo no contiene JSON válido")
    try:
        db().restore_project(payload)
        return jsonify({"ok": True})
    except (ValueError, TypeError) as exc:
        return error(str(exc))


@bp.post("/api/export")
def export_deck():
    try:
        destination = export_apkg(
            db().get_deck(), db().list_cards(), current_app.config["EXPORT_DIR"]
        )
        return send_file(destination, as_attachment=True, download_name=destination.name)
    except ValueError as exc:
        return error(str(exc))


@bp.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@bp.get("/api/settings")
def get_settings():
    return jsonify(db().get_settings())


@bp.put("/api/settings")
def update_settings():
    try:
        payload = request.get_json(silent=True) or {}
        candidate = {**db().get_settings(), **payload}
        LocalAIProvider.from_settings(candidate)
        settings = db().update_settings(payload)
        if not settings["network_enabled"] or not settings["browser_enabled"]:
            agent().stop()
        return jsonify(settings)
    except (ValueError, LocalAIError) as exc:
        return error(str(exc))


@bp.post("/api/settings/disable-network")
def disable_network():
    agent().stop()
    return jsonify(db().disable_all_network())


@bp.post("/api/settings/test-ai")
def test_local_ai():
    try:
        return jsonify(LocalAIProvider.from_settings(db().get_settings()).health())
    except LocalAIError as exc:
        return error(str(exc))


@bp.get("/api/agent/status")
def agent_status():
    state = agent().state()
    if state.get("research_id"):
        state["research"] = db().get_research(state["research_id"])
    return jsonify(state)


@bp.post("/api/cards/<int:card_id>/research")
def research_card(card_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(agent().start_research(card_id, str(payload.get("task", "")))), 202
    except ValueError as exc:
        return error(str(exc))


@bp.post("/api/agent/pause")
def pause_agent():
    return jsonify(agent().pause())


@bp.post("/api/agent/resume")
def resume_agent():
    return jsonify(agent().resume())


@bp.post("/api/agent/stop")
def stop_agent():
    return jsonify(agent().stop())


@bp.post("/api/agent/confirm")
def confirm_agent_action():
    try:
        allowed = bool((request.get_json(silent=True) or {}).get("allowed"))
        return jsonify(agent().confirm(allowed))
    except ValueError as exc:
        return error(str(exc))


@bp.get("/api/cards/<int:card_id>/research")
def get_card_research(card_id: int):
    proposal = db().latest_research_for_card(card_id)
    return jsonify(proposal) if proposal else error("No hay investigación para esta tarjeta", 404)


@bp.post("/api/research/<int:research_id>/decision")
def decide_research(research_id: int):
    proposal = db().get_research(research_id)
    if not proposal:
        return error("Investigación no encontrada", 404)
    decision = str((request.get_json(silent=True) or {}).get("decision", ""))
    if decision not in {"accepted", "rejected"}:
        return error("Decisión no válida")
    return jsonify(db().update_research(research_id, status=decision))


@bp.get("/api/agent/logs")
def agent_logs():
    return jsonify(db().list_agent_logs())
