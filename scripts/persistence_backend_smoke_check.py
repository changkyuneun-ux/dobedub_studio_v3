#!/usr/bin/env python3
"""Smoke check for PERSISTENCE_BACKEND=json|db selection.

The DB branch uses a temporary SQLite database so this test is deterministic
and does not require local MySQL.
"""

from __future__ import annotations

import base64
import os
import sys
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def migrate(database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")


def data_url(raw: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def login_headers(client) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"id": "dobedub", "password": "password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-persistence-") as tmp:
        root = Path(tmp)
        data_dir = root / "data"
        database_url = f"sqlite:///{root / 'studio.db'}"
        os.environ["PERSISTENCE_BACKEND"] = "db"
        os.environ["STUDIO_DATA_DIR"] = str(data_dir)
        os.environ["RUNPOD_DRY_RUN"] = "1"
        migrate(database_url)

        from fastapi.testclient import TestClient
        from backend.app.main import app
        from backend.app.services import studio_api_service

        client = TestClient(app)
        admin_headers = login_headers(client)
        upload_response = client.post("/api/uploads", headers=admin_headers, json={
            "fileName": "db-backend.png",
            "mimeType": "image/png",
            "dataUrl": data_url(b"db-backend-image"),
        })
        assert upload_response.status_code == 201, upload_response.text
        upload = upload_response.json()
        file_response = client.get(upload["downloadUrl"], headers=admin_headers)
        assert file_response.status_code == 200
        assert file_response.content == b"db-backend-image"

        config_response = client.post("/api/configs", headers=admin_headers, json={
            "source": "studio",
            "name": "db backend config",
            "snapshot": {
                "workflowId": "1-images.json",
                "keyframes": [{"index": 1, "uploadId": upload["assetId"], "fileName": upload["fileName"]}],
                "segments": [{"index": 1, "positivePrompt": "positive", "negativePromptAddition": "negative"}],
            },
        })
        assert config_response.status_code == 201, config_response.text
        configs_response = client.get("/api/configs", headers=admin_headers)
        assert configs_response.status_code == 200
        assert configs_response.json()["items"][0]["name"] == "db backend config"

        studio_api_service.append_history({
            "taskId": "task_persistence_backend",
            "timestamp": "2026-08-02 13:00:00",
            "workflowId": "1-images.json",
            "executionMode": "dry-run",
            "user": {"id": "user_persistence_backend", "name": "Persistence User"},
            "workerName": "Persistence User",
            "status": "Completed",
            "positivePrompts": [{"index": 1, "text": "positive"}],
            "negativePrompts": [{"index": 1, "text": "negative"}],
            "inputAssets": [upload["assetId"]],
            "inputImages": [{"index": 1, "assetId": upload["assetId"], "fileName": upload["fileName"]}],
            "keyframes": [{"index": 1, "uploadId": upload["assetId"], "fileName": upload["fileName"]}],
            "segments": [{"index": 1, "positivePrompt": "positive", "negativePromptAddition": "negative"}],
            "configJson": {"fps": 16, "steps": 4},
            "wanNodeConfig": {"segments": [{"index": 1}]},
        })
        history_response = client.get("/api/history?page=1&pageSize=10", headers=admin_headers)
        assert history_response.status_code == 200
        assert history_response.json()["items"][0]["taskId"] == "task_persistence_backend"

    print("OK persistence backend smoke check passed")


if __name__ == "__main__":
    main()
