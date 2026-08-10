from __future__ import annotations

import json
from pathlib import Path


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def merge_defaults(base: object, override: object) -> object:
    """Merge runtime overrides without discarding newly bundled default fields."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = merge_defaults(merged[key], value) if key in merged else value
        return merged
    if isinstance(base, list) and isinstance(override, list):
        merged = list(base)
        for index, value in enumerate(override):
            if index < len(merged):
                merged[index] = merge_defaults(merged[index], value)
            else:
                merged.append(value)
        return merged
    return override


def load_segment_defaults(data_dir: Path, bundled_defaults_path: Path) -> dict:
    runtime_path = data_dir / "segment-defaults.json"
    defaults: dict = {}
    if bundled_defaults_path.exists():
        defaults = read_json(bundled_defaults_path)
    if runtime_path.exists() and runtime_path != bundled_defaults_path:
        defaults = merge_defaults(defaults, read_json(runtime_path))
    return defaults


def get_workflow_segment_defaults(workflow_id: str, data_dir: Path, bundled_defaults_path: Path) -> dict:
    defaults = load_segment_defaults(data_dir, bundled_defaults_path)
    safe_name = Path(workflow_id).name
    if safe_name not in defaults:
        raise KeyError(safe_name)
    return defaults[safe_name]
