from __future__ import annotations

import pytest

from immersion_anki import create_app


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "EXPORT_DIR": str(tmp_path / "exports"),
        }
    )
    return app


@pytest.fixture()
def client(app):
    return app.test_client()

