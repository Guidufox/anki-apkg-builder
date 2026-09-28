"""Local Japanese immersion deck builder."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from .db import Database


def create_app(test_config: dict | None = None) -> Flask:
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=str(
            Path(os.environ.get("ANKI_BUILDER_DATA_DIR", project_root / "data"))
            / "anki_builder.sqlite3"
        ),
        EXPORT_DIR=str(
            Path(os.environ.get("ANKI_BUILDER_EXPORT_DIR", project_root / "exports"))
        ),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["EXPORT_DIR"]).mkdir(parents=True, exist_ok=True)

    database = Database(app.config["DATABASE"])
    database.initialize()
    app.extensions["database"] = database

    from .agent import AgentController

    app.extensions["agent_controller"] = AgentController(database, project_root)

    from .routes import bp

    app.register_blueprint(bp)
    return app
