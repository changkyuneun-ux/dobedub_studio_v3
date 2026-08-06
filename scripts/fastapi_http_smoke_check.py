#!/usr/bin/env python3
"""Start the FastAPI app on a local port and exercise browser-facing paths."""

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


def request_text(base_url: str, path: str) -> tuple[int, str]:
    request = urllib.request.Request(f"{base_url}{path}", headers={"Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, response.read().decode("utf-8")


def request_json(base_url: str, path: str) -> tuple[int, dict]:
    request = urllib.request.Request(f"{base_url}{path}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def wait_until_ready(base_url: str) -> None:
    deadline = time.time() + 15
    last_error = None
    while time.time() < deadline:
        try:
            status, payload = request_json(base_url, "/api/health")
            if status == 200 and payload.get("ok") is True:
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"FastAPI server did not become ready: {last_error}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-fastapi-http-") as tmp:
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
            "RUNPOD_DRY_RUN": "1",
        }
        process = subprocess.Popen(
            [sys.executable, "scripts/run_local.py"],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            wait_until_ready(base_url)
            status, index = request_text(base_url, "/")
            assert status == 200 and "DOBEDUB STUDIO" in index
            assert "__MANUAL_MARKDOWN__" not in index
            status, css = request_text(base_url, "/src/styles.css")
            assert status == 200 and "body" in css
            status, manual = request_text(base_url, "/manual")
            assert status == 200 and "dobedub studio" in manual.lower()
            status, studio = request_text(base_url, "/studio")
            assert status == 200 and ("DOBEDUB STUDIO React frontend" in studio or '<div id="root">' in studio)
            status, workflows = request_json(base_url, "/api/workflows")
            assert status == 200 and any(item.get("id") == "1-images.json" for item in workflows)
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
                raise RuntimeError(f"FastAPI server exited with {process.returncode}")

    print("OK fastapi http smoke check passed")


if __name__ == "__main__":
    main()
