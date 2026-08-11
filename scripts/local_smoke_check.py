#!/usr/bin/env python3
"""Smoke check for the legacy `python3 server.py` entrypoint.

The old monolith HTTP handler has been removed. This test verifies that the
compatibility entrypoint still starts the FastAPI local app and serves the
browser-facing API/UI paths.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request_text(base_url: str, path: str, *, headers: dict | None = None) -> tuple[int, str]:
    request = urllib.request.Request(f"{base_url}{path}", headers={"Accept": "text/html", **(headers or {})})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, response.read().decode("utf-8")


def request_json(base_url: str, path: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None) -> tuple[int, dict | list]:
    request_headers = {"Accept": "application/json", **(headers or {})}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{base_url}{path}", data=data, method=method, headers=request_headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def login_headers(base_url: str) -> dict[str, str]:
    status, payload = request_json(base_url, "/api/auth/login", method="POST", body={"id": "dobedub", "password": "password"})
    assert status == 200 and isinstance(payload, dict) and payload.get("accessToken")
    return {"Authorization": f"Bearer {payload['accessToken']}"}


def wait_until_ready(base_url: str) -> None:
    deadline = time.time() + 15
    last_error = None
    while time.time() < deadline:
        try:
            status, payload = request_json(base_url, "/api/health")
            if status == 200 and isinstance(payload, dict) and payload.get("backend") == "fastapi":
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"server.py entrypoint did not become ready: {last_error}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-server-entrypoint-") as tmp:
        data_dir = Path(tmp) / "data"
        metadata_dir = Path(tmp) / "metadata"
        for path in (data_dir, metadata_dir):
            path.mkdir(parents=True, exist_ok=True)
        (data_dir / "history.json").write_text("[]", encoding="utf-8")
        (data_dir / "assets.json").write_text("{}", encoding="utf-8")
        (data_dir / "configs.json").write_text("[]", encoding="utf-8")

        port = free_port()
        env = {
            **os.environ,
            "HOST": "127.0.0.1",
            "PORT": str(port),
            "STUDIO_DATA_DIR": str(data_dir),
            "METADATA_DIR": str(metadata_dir),
            "WORKFLOWS_DIR": str(PROJECT_ROOT / "workflows"),
            "WORKFLOW_SEED_DIR": str(PROJECT_ROOT / "workflows"),
            "RUNPOD_DRY_RUN": "1",
            "PERSISTENCE_BACKEND": "db",
            "DATABASE_URL": f"sqlite:///{Path(tmp) / 'smoke.db'}",
            "RUN_SERVER_AUTO_MIGRATE": "1",
        }
        process = subprocess.Popen(
            [sys.executable, "server.py"],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            wait_until_ready(base_url)
            auth_headers = login_headers(base_url)
            status, index = request_text(base_url, "/")
            assert status == 200 and "DOBEDUB STUDIO" in index
            status, workflows = request_json(base_url, "/api/workflows", headers=auth_headers)
            assert status == 200 and any(item.get("id") == "1-images.json" for item in workflows)
            status, manual = request_text(base_url, "/manual", headers=auth_headers)
            assert status == 200 and "dobedub studio" in manual.lower()
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            output = process.stdout.read() if process.stdout else ""
            if process.returncode not in {0, -15, -2}:
                print(output)
                raise RuntimeError(f"server.py exited with {process.returncode}")

    print("OK server.py compatibility smoke check passed")


if __name__ == "__main__":
    main()
