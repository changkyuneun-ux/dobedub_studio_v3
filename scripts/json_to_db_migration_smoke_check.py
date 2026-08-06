#!/usr/bin/env python3
"""Smoke check for scripts/migrate_json_to_db.py using temporary data."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, inspect


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migrate_json_to_db import migrate_json_to_db  # noqa: E402


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-json-migrate-") as tmp:
        root = Path(tmp)
        data_dir = root / "data"
        uploads_dir = data_dir / "uploads"
        outputs_dir = data_dir / "outputs"
        uploads_dir.mkdir(parents=True)
        outputs_dir.mkdir(parents=True)
        upload_path = uploads_dir / "asset_input_sample.png"
        output_path = outputs_dir / "asset_output_sample.mp4"
        upload_path.write_bytes(b"input")
        output_path.write_bytes(b"output")

        write_json(data_dir / "assets.json", {
            "asset_input": {
                "assetId": "asset_input",
                "type": "input_image",
                "fileName": "sample.png",
                "mimeType": "image/png",
                "sizeBytes": 5,
                "path": str(upload_path),
                "createdAt": "2026-08-02 10:00:00",
            },
            "asset_output": {
                "assetId": "asset_output",
                "type": "output_image",
                "fileName": "sample.mp4",
                "mimeType": "video/mp4",
                "sizeBytes": 6,
                "path": str(output_path),
                "createdAt": "2026-08-02 10:01:00",
            },
        })
        write_json(data_dir / "history.json", [{
            "taskId": "task_json_migrate",
            "timestamp": "2026-08-02 10:02:00",
            "workflowId": "1-images.json",
            "executionMode": "runpod",
            "user": {"id": "user_json_migrate", "name": "JSON Migrate User"},
            "workerName": "JSON Migrate User",
            "status": "Completed",
            "positivePrompts": [{"index": 1, "text": "positive"}],
            "negativePrompts": [{"index": 1, "text": "negative"}],
            "configJson": {"fps": 16, "steps": 4},
            "wanNodeConfig": {"segments": [{"index": 1}]},
            "inputAssets": ["asset_input"],
            "inputImages": [{"index": 1, "assetId": "asset_input", "fileName": "sample.png"}],
            "keyframes": [{"index": 1, "uploadId": "asset_input", "fileName": "sample.png"}],
            "outputAssets": [{
                "assetId": "asset_output",
                "fileName": "sample.mp4",
                "mimeType": "video/mp4",
                "outputRole": "final",
                "segmentIndex": 1,
            }],
        }])
        write_json(data_dir / "configs.json", [{
            "configId": "config_json_migrate",
            "timestamp": "2026-08-02 10:03:00",
            "source": "studio",
            "workflowId": "1-images.json",
            "name": "json migrate config",
            "snapshot": {"workflowId": "1-images.json"},
        }])

        database_url = f"sqlite:///{root / 'migration.db'}"
        dry_run = migrate_json_to_db(data_dir=data_dir, database_url=database_url, apply=False)
        assert dry_run["assets"] == 2
        assert dry_run["history"] == 1
        assert dry_run["configs"] == 1
        assert dry_run["applied"] is False

        applied = migrate_json_to_db(data_dir=data_dir, database_url=database_url, apply=True)
        assert applied["applied"] is True
        assert applied["dbHistory"] == 1
        assert applied["dbConfigs"] == 1

        engine = create_engine(database_url, future=True)
        inspector = inspect(engine)
        assert "workflow_tasks" in inspector.get_table_names()
        engine.dispose()

    print("OK json to db migration smoke check passed")


if __name__ == "__main__":
    main()
