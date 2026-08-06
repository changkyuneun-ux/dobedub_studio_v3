from __future__ import annotations

import json
from pathlib import Path


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def load_segment_defaults(data_dir: Path, bundled_defaults_path: Path) -> dict:
    runtime_path = data_dir / "segment-defaults.json"
    defaults = {}
    if bundled_defaults_path.exists():
        defaults.update(read_json(bundled_defaults_path))
    if runtime_path.exists() and runtime_path != bundled_defaults_path:
        defaults.update(read_json(runtime_path))
    return defaults


def get_workflow_segment_defaults(workflow_id: str, data_dir: Path, bundled_defaults_path: Path) -> dict:
    defaults = load_segment_defaults(data_dir, bundled_defaults_path)
    safe_name = Path(workflow_id).name
    if safe_name not in defaults:
        raise KeyError(safe_name)
    return defaults[safe_name]
