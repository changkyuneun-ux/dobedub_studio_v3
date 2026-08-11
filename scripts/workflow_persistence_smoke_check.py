#!/usr/bin/env python3
"""Verify image-bundled workflow updates cannot overwrite EFS runtime workflows."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.workflow_storage_service import bootstrap_workflow_store


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-workflow-store-") as tmp:
        root = Path(tmp)
        seed = root / "image-workflows"
        runtime = root / "efs-workflows"
        data = root / "data"
        bundled = seed / "bundled.json"
        bundled_config = seed / "bundled.paramconfig.json"
        write(bundled, '{"version": 1}\n')
        write(bundled_config, '{"version": 1}\n')

        first = bootstrap_workflow_store(seed, runtime, data)
        assert sorted(first["created"]) == ["bundled.json", "bundled.paramconfig.json"]
        assert (runtime / "bundled.json").read_text(encoding="utf-8") == '{"version": 1}\n'

        write(bundled, '{"version": 2}\n')
        write(bundled_config, '{"version": 2}\n')
        second = bootstrap_workflow_store(seed, runtime, data)
        assert sorted(second["updated"]) == ["bundled.json", "bundled.paramconfig.json"]
        assert (runtime / "bundled.json").read_text(encoding="utf-8") == '{"version": 2}\n'

        write(runtime / "operator-added.json", '{"operator": true}\n')
        write(runtime / "operator-added.paramconfig.json", '{"operator": true}\n')
        write(bundled, '{"version": 3}\n')
        write(seed / "new-image-default.json", '{"default": true}\n')
        third = bootstrap_workflow_store(seed, runtime, data)
        assert (runtime / "bundled.json").read_text(encoding="utf-8") == '{"version": 3}\n'
        assert (runtime / "operator-added.json").read_text(encoding="utf-8") == '{"operator": true}\n'
        assert "new-image-default.json" in third["created"]

        write(runtime / "bundled.json", '{"operatorOverride": true}\n')
        write(bundled, '{"version": 4}\n')
        fourth = bootstrap_workflow_store(seed, runtime, data)
        assert "bundled.json" in fourth["preserved"]
        assert (runtime / "bundled.json").read_text(encoding="utf-8") == '{"operatorOverride": true}\n'

    print("OK workflow persistence smoke check passed")


if __name__ == "__main__":
    main()
