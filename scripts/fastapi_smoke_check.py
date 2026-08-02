#!/usr/bin/env python3
"""Smoke check for the new FastAPI backend skeleton."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import create_app


def main():
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["backend"] == "fastapi"
    assert payload["app"] == "dobedub-studio"
    assert payload["ok"] is True
    assert "legacy" in payload

    response = client.get("/api/v1/workflows")
    assert response.status_code == 200, response.text
    workflows = response.json()
    assert any(item.get("id") == "1-images.json" for item in workflows)

    response = client.get("/api/v1/workflows/1-images.json/schema")
    assert response.status_code == 200, response.text
    schema = response.json()
    assert schema["workflowId"] == "1-images.json"
    assert schema["keyframeCount"] == 1

    response = client.get("/api/v1/workflows/1-images.json/segment-defaults")
    assert response.status_code == 200, response.text
    defaults = response.json()
    assert len(defaults["segments"]) == 1

    response = client.get("/api/v1/workflows/1-images.json/widget-metadata")
    assert response.status_code == 200, response.text
    widget_metadata = response.json()
    assert widget_metadata["workflowId"] == "1-images.json"
    assert widget_metadata["nodeCount"] > 0

    response = client.get("/api/v1/metadata/status")
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True

    print("OK fastapi smoke check passed")


if __name__ == "__main__":
    main()
