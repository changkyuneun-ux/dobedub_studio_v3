#!/usr/bin/env python3
"""Smoke check for the new FastAPI backend skeleton."""

from __future__ import annotations

import sys
import os
import base64
import tempfile
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.dialects import mysql

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def redirect_app_paths(tmp_root: Path):
    data_dir = tmp_root / "data"
    metadata_dir = tmp_root / "metadata"
    uploads_dir = data_dir / "uploads"
    outputs_dir = data_dir / "outputs"
    reports_dir = data_dir / "reports"
    for path in (data_dir, metadata_dir, uploads_dir, outputs_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=True)

    (data_dir / "history.json").write_text("[]", encoding="utf-8")
    (data_dir / "assets.json").write_text("{}", encoding="utf-8")
    (data_dir / "configs.json").write_text("[]", encoding="utf-8")

    os.environ["STUDIO_DATA_DIR"] = str(data_dir)
    os.environ["METADATA_DIR"] = str(metadata_dir)
    os.environ["WORKFLOWS_DIR"] = str(PROJECT_ROOT / "workflows")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_root / 'fastapi-smoke.db'}"
    os.environ["PERSISTENCE_BACKEND"] = "db"
    os.environ["RUNPOD_DRY_RUN"] = "1"


def login_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"id": "dobedub", "password": "password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


def main():
    with tempfile.TemporaryDirectory(prefix="dobedub-fastapi-smoke-") as tmp:
        redirect_app_paths(Path(tmp))
        command.upgrade(Config(str(PROJECT_ROOT / "alembic.ini")), "head")
        from backend.app.main import create_app

        client = TestClient(create_app())
        response = client.get("/api/v1/health")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["backend"] == "fastapi"
        assert payload["app"] == "dobedub-studio"
        assert payload["ok"] is True
        assert "system" in payload
        assert "legacy" in payload
        assert "runpod" in payload["system"]
        assert "promptLlm" in payload["system"]

        admin_headers = login_headers(client)

        response = client.get("/api/v1/workflows", headers=admin_headers)
        assert response.status_code == 200, response.text
        workflows = response.json()
        assert any(item.get("id") == "1-images.json" for item in workflows)

        response = client.get("/api/v1/workflows/1-images.json/schema", headers=admin_headers)
        assert response.status_code == 200, response.text
        schema = response.json()
        assert schema["workflowId"] == "1-images.json"
        assert schema["keyframeCount"] == 1

        response = client.get("/api/v1/workflows/1-images.json/segment-defaults", headers=admin_headers)
        assert response.status_code == 200, response.text
        defaults = response.json()
        assert len(defaults["segments"]) == 1

        response = client.get("/api/v1/workflows/1-images.json/widget-metadata", headers=admin_headers)
        assert response.status_code == 200, response.text
        widget_metadata = response.json()
        assert widget_metadata["workflowId"] == "1-images.json"
        assert widget_metadata["nodeCount"] > 0

        response = client.get("/api/v1/metadata/status", headers=admin_headers)
        assert response.status_code == 200, response.text
        assert response.json()["ok"] is True

        response = client.get("/api/health")
        assert response.status_code == 200, response.text
        assert response.json()["backend"] == "fastapi"
        assert "system" in response.json()

        response = client.post("/api/auth/login", json={"id": "dobedub", "password": "password"})
        assert response.status_code == 200, response.text
        assert response.json()["user"]["name"] == "장균은"
        assert response.json()["accessToken"]

        data_url = "data:image/png;base64," + base64.b64encode(b"fake-image").decode("ascii")
        response = client.post("/api/uploads", headers=admin_headers, json={"fileName": "example.png", "dataUrl": data_url})
        assert response.status_code == 201, response.text
        upload = response.json()
        assert upload["assetId"]

        response = client.get(f"/api/files/{upload['assetId']}", headers=admin_headers)
        assert response.status_code == 200, response.text
        assert response.content == b"fake-image"

        # Assets are intentionally protected: browser image/video tags cannot attach
        # JWT headers, so the frontend must load task assets through apiClient.assetBlob.
        response = client.get(f"/api/files/{upload['assetId']}")
        assert response.status_code == 401, response.text

        response = client.get(f"/api/files/{upload['assetId']}", headers={**admin_headers, "Range": "bytes=0-3"})
        assert response.status_code == 206, response.text
        assert response.content == b"fake"

        segment = schema["segments"][0]
        job_payload = {
            "workflowId": "1-images.json",
            "keyframes": [{"index": 1, "uploadId": upload["assetId"], "fileName": upload["fileName"]}],
            "segments": [{
                "index": 1,
                "nodeId": segment.get("nodeId", ""),
                "subgraphName": segment.get("subgraphName", ""),
                "displayName": segment.get("displayName", ""),
                "positivePrompt": "fastapi smoke prompt",
                "negativePromptAddition": "fastapi smoke negative",
                "config": segment.get("config", {}),
            }],
            "user": {"id": "dobedub", "name": "장균은"},
        }
        response = client.post("/api/jobs", headers=admin_headers, json=job_payload)
        assert response.status_code == 201, response.text
        task_id = response.json()["taskId"]
        last_status = {}
        for _ in range(80):
            response = client.get(f"/api/jobs/{task_id}", headers=admin_headers)
            assert response.status_code == 200, response.text
            last_status = response.json()
            if last_status["status"] == "success":
                break
            time.sleep(0.1)
        assert last_status["status"] == "success", last_status

        response = client.get("/api/history?page=1&pageSize=10", headers=admin_headers)
        assert response.status_code == 200, response.text
        history = response.json()
        assert history["total"] >= 1
        history_item = next(item for item in history["items"] if item.get("taskId") == task_id)
        assert history_item["inputAssets"] == [upload["assetId"]]
        assert history_item["inputImages"][0]["assetId"] == upload["assetId"]

        response = client.get("/api/prompts", headers=admin_headers)
        assert response.status_code == 200, response.text
        assert "positive" in response.json()

        response = client.get("/api/prompts/reusable?reuseEligible=true", headers=admin_headers)
        assert response.status_code == 200, response.text

        from backend.app.db.models import TaskPrompt
        from backend.app.services.task_tracking_service import reusable_task_prompts

        reusable_task_prompts(reuse_eligible=True)
        mysql_reuse_query = select(TaskPrompt).order_by(
            TaskPrompt.quality_rating.is_(None).asc(),
            TaskPrompt.quality_rating.desc(),
            TaskPrompt.updated_at.desc(),
            TaskPrompt.id.desc(),
        )
        assert "NULLS LAST" not in str(mysql_reuse_query.compile(dialect=mysql.dialect())).upper()

        response = client.post("/api/configs", headers=admin_headers, json={"workflowId": "1-images.json", "snapshot": job_payload})
        assert response.status_code == 201, response.text
        response = client.get("/api/configs", headers=admin_headers)
        assert response.status_code == 200, response.text
        assert response.json()["items"]

        response = client.post("/api/reports", headers=admin_headers, json={"historyItem": history["items"][0]})
        assert response.status_code == 201, response.text
        report = response.json()
        response = client.get(report["downloadUrl"], headers=admin_headers)
        assert response.status_code == 200, response.text
        assert b"DOBEDUB STUDIO" in response.content

        response = client.post("/api/jobs", headers=admin_headers, json=job_payload)
        assert response.status_code == 201, response.text
        cancel_task_id = response.json()["taskId"]
        response = client.post(f"/api/jobs/{cancel_task_id}/cancel", headers=admin_headers)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "cancelled"

        response = client.post(f"/api/history/{task_id}/delete", headers=admin_headers)
        assert response.status_code == 200, response.text
        assert response.json()["deleted"] is True

        response = client.get("/manual", headers=admin_headers)
        assert response.status_code == 200, response.text
        assert "dobedub studio" in response.text
        assert "v3-01-login.png" in response.text
        assert "v3-14-admin-prompt-catalog.png" in response.text
        assert 'href="#1-서비스-개요"' in response.text
        assert "manualSearch" not in response.text
        assert "<script>" not in response.text
        assert "Prompt Reuse" in response.text
        assert "Admin Console" in response.text

    print("OK fastapi smoke check passed")


if __name__ == "__main__":
    main()
