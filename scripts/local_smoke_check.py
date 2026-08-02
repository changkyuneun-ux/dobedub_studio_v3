#!/usr/bin/env python3
"""Local smoke checks for DOBEDUB STUDIO monolith.

This script starts the current stdlib HTTP server in-process with runtime
data paths redirected to a temporary directory. It exercises the stable API
surface used as the regression baseline before the FastAPI/React/MySQL
refactor.
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import server


def request_json(base_url: str, path: str, method: str = "GET", payload: dict | None = None):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}


def request_text(base_url: str, path: str):
    request = urllib.request.Request(f"{base_url}{path}", headers={"Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, response.read().decode("utf-8")


def assert_true(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def redirect_runtime_paths(tmp_root: Path):
    data_dir = tmp_root / "data"
    uploads_dir = data_dir / "uploads"
    outputs_dir = data_dir / "outputs"
    reports_dir = data_dir / "reports"
    for path in (data_dir, uploads_dir, outputs_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=True)

    (data_dir / "history.json").write_text("[]", encoding="utf-8")
    (data_dir / "assets.json").write_text("{}", encoding="utf-8")
    (data_dir / "configs.json").write_text("[]", encoding="utf-8")

    server.DATA_DIR = data_dir
    server.HISTORY_PATH = data_dir / "history.json"
    server.ASSETS_PATH = data_dir / "assets.json"
    server.CONFIGS_PATH = data_dir / "configs.json"
    server.SEGMENT_DEFAULTS_PATH = data_dir / "segment-defaults.json"
    server.REPORTS_DIR = reports_dir
    server.UPLOADS_DIR = uploads_dir
    server.OUTPUTS_DIR = outputs_dir
    server.DRY_RUN = True


def main():
    with tempfile.TemporaryDirectory(prefix="dobedub-smoke-") as tmp:
        redirect_runtime_paths(Path(tmp))
        server.ensure_metadata_current()

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{httpd.server_port}"

        try:
            status, health = request_json(base_url, "/api/health")
            assert_true(status == 200 and health.get("ok") is True, "health endpoint failed")
            assert_true(health.get("dryRun") is True, "smoke check must force dry-run mode")

            status, workflows = request_json(base_url, "/api/workflows")
            assert_true(status == 200, "workflows endpoint failed")
            workflow_items = workflows if isinstance(workflows, list) else workflows.get("items", [])
            workflow_ids = {item.get("id") or item.get("workflow") for item in workflow_items}
            assert_true("1-images.json" in workflow_ids, "1-images workflow missing")
            assert_true(len(workflow_items) >= 6, "expected at least six workflows")

            status, schema = request_json(base_url, "/api/workflows/1-images.json/schema")
            assert_true(status == 200, "workflow schema endpoint failed")
            assert_true(schema.get("workflowId") == "1-images.json", "schema workflowId mismatch")
            assert_true(schema.get("keyframeCount") == 1, "1-images keyframe count mismatch")

            status, defaults = request_json(base_url, "/api/segment-defaults/1-images.json")
            assert_true(status == 200, "segment defaults endpoint failed")
            assert_true(len(defaults.get("segments", [])) == 1, "segment defaults missing")

            status, metadata = request_json(base_url, "/api/workflows/1-images.json/widget-metadata")
            assert_true(status == 200, "widget metadata endpoint failed")
            assert_true(metadata.get("workflowId") == "1-images.json", "widget metadata workflow mismatch")
            assert_true(metadata.get("nodeCount", 0) > 0, "widget metadata node count missing")

            status, metadata_status = request_json(base_url, "/api/metadata/status")
            assert_true(status == 200 and metadata_status.get("ok") is True, "metadata status failed")

            status, history = request_json(base_url, "/api/history?page=1&pageSize=10")
            assert_true(status == 200 and history.get("pageSize") == 10, "history pagination failed")

            status, login = request_json(
                base_url,
                "/api/auth/login",
                method="POST",
                payload={"id": "smoke@example.com", "password": "test", "name": "Smoke Tester"},
            )
            assert_true(status == 200 and login.get("user", {}).get("name") == "Smoke Tester", "login failed")

            status, manual = request_text(base_url, "/manual")
            assert_true(status == 200 and "dobedub studio" in manual.lower(), "manual page failed")

            print("OK local smoke check passed")
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"HTTP error: {exc.code} {exc.reason}")
        raise
